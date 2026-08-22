"""
Fetch and format local weather reports for LEDarcade terminal scrolling.

Uses Open-Meteo (live, no API key) as the primary source so each run pulls
current conditions. Falls back to wttr.in if Open-Meteo is unreachable.
"""

from __future__ import annotations

import os
import time
import traceback
import urllib.parse
from configparser import ConfigParser
from datetime import datetime

import requests

KeyConfigFileName = "KeyConfig.ini"
DEFAULT_LOCATION = "Franktown, Ontario, Canada"
WEATHER_TYPE_SPEED = 0.064  # 25% faster than default terminal TypeSpeed of 0.08
WEATHER_SCROLL_REPEAT = 2
WEATHER_POST_SCROLL_WAIT = 30  # seconds to idle after scrolling before exiting
WEATHER_HEADER_RGB = (200, 200, 0)

# HTTP
_HTTP_TIMEOUT = 15
_USER_AGENT = "LEDarcade-WeatherClock/2.0 (+https://github.com/datagod/LEDarcade)"

# WMO weather interpretation codes (Open-Meteo)
_WMO_DESC = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Freezing drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Freezing rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def CheckConfigFiles():
    """Ensure KeyConfig.ini exists and has weather keys (append if missing)."""
    if not os.path.exists(KeyConfigFileName):
        try:
            with open(KeyConfigFileName, "w") as config_file:
                config_file.write("[KEYS]\n")
                config_file.write(f"WEATHER_LOCATION = {DEFAULT_LOCATION}\n")
                config_file.write("# Optional: pin exact coordinates (skip geocode)\n")
                config_file.write("# WEATHER_LAT = 45.04\n")
                config_file.write("# WEATHER_LON = -76.06\n")
                config_file.write("\n")
            print(f"[WeatherClock] Created default {KeyConfigFileName}")
        except Exception as error:
            print(f"[WeatherClock] Could not create {KeyConfigFileName}: {error}")
        return

    # File exists — ensure WEATHER_LOCATION key is present
    try:
        key_file = ConfigParser()
        key_file.read(KeyConfigFileName)
        if not key_file.has_section("KEYS"):
            key_file.add_section("KEYS")
        if not key_file.has_option("KEYS", "WEATHER_LOCATION"):
            key_file.set("KEYS", "WEATHER_LOCATION", DEFAULT_LOCATION)
            with open(KeyConfigFileName, "w") as config_file:
                key_file.write(config_file)
            print(f"[WeatherClock] Added WEATHER_LOCATION to {KeyConfigFileName}")
    except Exception as error:
        print(f"[WeatherClock] Config ensure error: {error}")


def _read_key_config():
    CheckConfigFiles()
    key_file = ConfigParser()
    if os.path.exists(KeyConfigFileName):
        key_file.read(KeyConfigFileName)
    return key_file


def LoadWeatherLocation(location_override=""):
    if location_override:
        return location_override.strip()

    try:
        key_file = _read_key_config()
        return (
            key_file.get("KEYS", "WEATHER_LOCATION", fallback=DEFAULT_LOCATION).strip()
            or DEFAULT_LOCATION
        )
    except Exception as error:
        print(f"[WeatherClock] Config read error: {error}")
        return DEFAULT_LOCATION


def LoadWeatherCoords():
    """Optional fixed lat/lon from KeyConfig.ini — most accurate when set."""
    try:
        key_file = _read_key_config()
        lat_s = key_file.get("KEYS", "WEATHER_LAT", fallback="").strip()
        lon_s = key_file.get("KEYS", "WEATHER_LON", fallback="").strip()
        if not lat_s or not lon_s:
            return None
        return float(lat_s), float(lon_s)
    except Exception as error:
        print(f"[WeatherClock] Coord read error: {error}")
        return None


def NormalizeUnits(units="C"):
    """Return 'C' or 'F' for supported temperature units. Default metric (°C)."""
    if str(units).strip().upper().startswith("F"):
        return "F"
    return "C"


def _wmo_description(code):
    try:
        return _WMO_DESC.get(int(code), f"Code {code}")
    except (TypeError, ValueError):
        return "Unknown"


def _wind_dir_label(degrees):
    try:
        d = float(degrees) % 360.0
    except (TypeError, ValueError):
        return ""
    dirs = (
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    )
    return dirs[int((d + 11.25) / 22.5) % 16]


def _session():
    s = requests.Session()
    s.headers.update({"User-Agent": _USER_AGENT, "Accept": "application/json"})
    # Never use stale intermediate caches for live weather
    s.headers.update({"Cache-Control": "no-cache", "Pragma": "no-cache"})
    return s


def GeocodeLocation(location):
    """
    Resolve a place name to (lat, lon, display_name).

    For multi-part queries ("Town, Province, Country") Nominatim is tried
    first — Open-Meteo's search ranks large US names ahead of small towns.
    Bare names use Open-Meteo with region scoring, then Nominatim.
    """
    location = (location or "").strip()
    if not location:
        return None

    sess = _session()
    multi_part = "," in location

    def _from_nominatim():
        resp = sess.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": location,
                "format": "json",
                "limit": 5,
                "addressdetails": 1,
            },
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json() or []
        if not results:
            return None
        best = results[0]
        addr = best.get("address") or {}
        parts = [
            best.get("name")
            or addr.get("hamlet")
            or addr.get("village")
            or addr.get("town")
            or addr.get("city"),
            addr.get("state") or addr.get("province"),
            addr.get("country"),
        ]
        display = ", ".join(p for p in parts if p) or best.get("display_name", location)
        return {
            "lat": float(best["lat"]),
            "lon": float(best["lon"]),
            "name": display,
            "source": "nominatim",
        }

    def _from_open_meteo():
        # Try full string first, then bare city token
        names = [location]
        bare = location.split(",")[0].strip()
        if bare and bare != location:
            names.append(bare)
        all_results = []
        for name in names:
            resp = sess.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "name": name,
                    "count": 10,
                    "language": "en",
                    "format": "json",
                },
                timeout=_HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            all_results.extend((resp.json() or {}).get("results") or [])
        return _pick_geocode_result(location, all_results, source="open-meteo")

    # Multi-part place names → Nominatim first (accurate for small towns)
    if multi_part:
        try:
            pick = _from_nominatim()
            if pick:
                return pick
        except Exception as error:
            print(f"[WeatherClock] Nominatim geocode failed: {error}")
        try:
            pick = _from_open_meteo()
            if pick:
                return pick
        except Exception as error:
            print(f"[WeatherClock] Open-Meteo geocode failed: {error}")
        return None

    # Bare names → Open-Meteo first, Nominatim fallback
    try:
        pick = _from_open_meteo()
        if pick and pick.get("_score", 0) > 0:
            return pick
        # Unscored ambiguous bare name — try Nominatim before accepting
        if pick:
            bare_pick = pick
        else:
            bare_pick = None
    except Exception as error:
        print(f"[WeatherClock] Open-Meteo geocode failed: {error}")
        bare_pick = None

    try:
        nom = _from_nominatim()
        if nom:
            return nom
    except Exception as error:
        print(f"[WeatherClock] Nominatim geocode failed: {error}")

    return bare_pick


def _pick_geocode_result(query, results, source="open-meteo"):
    if not results:
        return None
    q = query.lower()
    # Prefer matches whose admin1/country appear in the query string
    scored = []
    seen = set()
    for r in results:
        key = (round(float(r.get("latitude", 0)), 3), round(float(r.get("longitude", 0)), 3))
        if key in seen:
            continue
        seen.add(key)
        score = 0
        admin1 = (r.get("admin1") or "").lower()
        country = (r.get("country") or "").lower()
        name = (r.get("name") or "").lower()
        if admin1 and admin1 in q:
            score += 5
        if "ontario" in q and "ontario" in admin1:
            score += 10
        if "canada" in q and "canada" in country:
            score += 8
        if "colorado" in q and "colorado" in admin1:
            score += 10
        if name and name.split()[0] in q:
            score += 2
        # Prefer higher population when available
        pop = r.get("population") or 0
        score += min(3, int(pop) // 5000) if pop else 0
        scored.append((score, r))
    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best = scored[0]
    # If query is bare "Franktown" and nothing scored, still use first but log
    if best_score == 0 and "," not in query:
        print(
            f"[WeatherClock] Ambiguous location '{query}' — "
            f"using {best.get('name')}, {best.get('admin1')}, {best.get('country')}. "
            f"Set WEATHER_LOCATION more specifically or WEATHER_LAT/LON in KeyConfig.ini"
        )
    display = ", ".join(
        p for p in [best.get("name"), best.get("admin1"), best.get("country")] if p
    )
    return {
        "lat": float(best["latitude"]),
        "lon": float(best["longitude"]),
        "name": display or query,
        "source": source,
        "_score": best_score,
    }


def FetchOpenMeteo(lat, lon, place_name, units="C"):
    """Live current + today/tomorrow from Open-Meteo (no cache)."""
    units = NormalizeUnits(units)
    temp_unit = "celsius" if units == "C" else "fahrenheit"
    temp_label = "C" if units == "C" else "F"
    wind_unit = "kmh" if units == "C" else "mph"
    wind_label = "km/h" if units == "C" else "mph"

    # cache-bust so CDNs never return a stale snapshot
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "weather_code,wind_speed_10m,wind_direction_10m"
        ),
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "timezone": "auto",
        "forecast_days": 2,
        "temperature_unit": temp_unit,
        "wind_speed_unit": wind_unit,
        "_": int(time.time()),  # cache buster
    }
    sess = _session()
    resp = sess.get(
        "https://api.open-meteo.com/v1/forecast",
        params=params,
        timeout=_HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    current = data.get("current") or {}
    daily = data.get("daily") or {}

    temp = current.get("temperature_2m", "?")
    feels = current.get("apparent_temperature", temp)
    humidity = current.get("relative_humidity_2m", "?")
    wind_speed = current.get("wind_speed_10m", "?")
    wind_dir = _wind_dir_label(current.get("wind_direction_10m"))
    condition = _wmo_description(current.get("weather_code"))
    as_of = current.get("time") or ""
    # Prefer local clock if observation time parses
    as_of_label = ""
    if as_of:
        try:
            # "2026-08-17T08:15"
            as_of_label = datetime.fromisoformat(as_of).strftime("%-I:%M %p")
        except Exception:
            as_of_label = as_of

    today_high = (daily.get("temperature_2m_max") or ["?"])[0]
    today_low = (daily.get("temperature_2m_min") or ["?"])[0]

    body_parts = [
        f"Now {temp}{temp_label}, {condition}.",
        f"Feels like {feels}{temp_label}.",
        f"Humidity {humidity} pct.",
        f"Wind {wind_speed} {wind_label} {wind_dir}.".strip(),
        f"Today high {today_high}{temp_label}, low {today_low}{temp_label}.",
    ]
    if as_of_label:
        body_parts.insert(0, f"As of {as_of_label}.")

    if len(daily.get("time") or []) > 1:
        tomorrow_high = daily["temperature_2m_max"][1]
        tomorrow_low = daily["temperature_2m_min"][1]
        tomorrow_desc = _wmo_description(daily["weather_code"][1])
        body_parts.append(
            f"Tomorrow {tomorrow_desc}, high {tomorrow_high}{temp_label}, "
            f"low {tomorrow_low}{temp_label}."
        )

    header = f"Weather for {place_name}."
    body = " ".join(str(p) for p in body_parts if p)
    print(
        f"[WeatherClock] Open-Meteo live: {place_name} "
        f"lat={lat:.4f} lon={lon:.4f} temp={temp}{temp_label} "
        f"as_of={as_of} ({condition})"
    )
    return {"header": header, "body": body, "source": "open-meteo", "as_of": as_of}


def FetchWttrIn(location, units="C"):
    """Fallback provider (wttr.in JSON)."""
    units = NormalizeUnits(units)
    encoded_location = urllib.parse.quote(location)
    # lang + m (metric) or u (USCS); tq for quiet; format=j1 JSON
    unit_flag = "m" if units == "C" else "u"
    url = f"https://wttr.in/{encoded_location}?format=j1&{unit_flag}&lang=en"
    sess = _session()
    response = sess.get(url, timeout=_HTTP_TIMEOUT, params={"_": int(time.time())})
    response.raise_for_status()
    data = response.json()

    area = data["nearest_area"][0]["areaName"][0]["value"]
    region = ""
    try:
        region = data["nearest_area"][0]["region"][0]["value"]
    except Exception:
        pass
    country = ""
    try:
        country = data["nearest_area"][0]["country"][0]["value"]
    except Exception:
        pass
    place = ", ".join(p for p in (area, region, country) if p)

    current = data["current_condition"][0]
    today = data["weather"][0]
    tomorrow = data["weather"][1] if len(data.get("weather", [])) > 1 else None

    if units == "C":
        temp = current.get("temp_C", "?")
        feels = current.get("FeelsLikeC", temp)
        temp_label = "C"
        wind_speed = current.get("windspeedKmph", "?")
        wind_label = "km/h"
        today_high = today.get("maxtempC", "?")
        today_low = today.get("mintempC", "?")
    else:
        temp = current.get("temp_F", "?")
        feels = current.get("FeelsLikeF", temp)
        temp_label = "F"
        wind_speed = current.get("windspeedMiles", "?")
        wind_label = "mph"
        today_high = today.get("maxtempF", "?")
        today_low = today.get("mintempF", "?")

    condition = current["weatherDesc"][0]["value"].strip()
    humidity = current.get("humidity", "?")
    wind_dir = current.get("winddir16Point", "")
    obs = current.get("localObsDateTime") or current.get("observation_time") or ""

    body_parts = []
    if obs:
        body_parts.append(f"As of {obs}.")
    body_parts.extend(
        [
            f"Now {temp}{temp_label}, {condition}.",
            f"Feels like {feels}{temp_label}.",
            f"Humidity {humidity} pct.",
            f"Wind {wind_speed} {wind_label} {wind_dir}.".strip(),
            f"Today high {today_high}{temp_label}, low {today_low}{temp_label}.",
        ]
    )

    if tomorrow:
        if units == "C":
            tomorrow_high = tomorrow.get("maxtempC", "?")
            tomorrow_low = tomorrow.get("mintempC", "?")
        else:
            tomorrow_high = tomorrow.get("maxtempF", "?")
            tomorrow_low = tomorrow.get("mintempF", "?")
        tomorrow_desc = tomorrow["hourly"][4]["weatherDesc"][0]["value"].strip()
        body_parts.append(
            f"Tomorrow {tomorrow_desc}, high {tomorrow_high}{temp_label}, "
            f"low {tomorrow_low}{temp_label}."
        )

    print(
        f"[WeatherClock] wttr.in fallback: {place} temp={temp}{temp_label} obs={obs}"
    )
    return {
        "header": f"Weather for {place}.",
        "body": " ".join(body_parts),
        "source": "wttr.in",
        "as_of": obs,
    }


def FetchWeatherReport(location, units="C"):
    """
    Fetch up-to-date weather and return a scrollable text report (default °C).

    Always hits the network (no local cache). Prefers Open-Meteo current
    conditions; falls back to wttr.in on failure.
    """
    units = NormalizeUnits(units)
    location = (location or LoadWeatherLocation()).strip() or DEFAULT_LOCATION

    # 1) Fixed coordinates if configured
    coords = LoadWeatherCoords()
    place_name = location
    lat = lon = None
    if coords:
        lat, lon = coords
        place_name = location
        print(f"[WeatherClock] Using configured coordinates lat={lat} lon={lon}")
    else:
        geo = GeocodeLocation(location)
        if geo:
            lat, lon = geo["lat"], geo["lon"]
            place_name = geo.get("name") or location
            print(
                f"[WeatherClock] Geocoded '{location}' → {place_name} "
                f"({lat:.4f},{lon:.4f}) via {geo.get('source')}"
            )

    # 2) Open-Meteo (primary — always live)
    if lat is not None and lon is not None:
        try:
            return FetchOpenMeteo(lat, lon, place_name, units=units)
        except Exception as error:
            print(f"[WeatherClock] Open-Meteo fetch failed: {error}")
            traceback.print_exc()

    # 3) wttr.in fallback
    try:
        return FetchWttrIn(location, units=units)
    except Exception as error:
        print(f"[WeatherClock] Fetch failed for '{location}': {error}")
        traceback.print_exc()
        return {
            "header": "",
            "body": f"Weather unavailable for {location}. {error}",
            "source": "none",
            "as_of": "",
        }


if __name__ == "__main__":
    loc = LoadWeatherLocation()
    print("Location:", loc)
    report = FetchWeatherReport(loc, "C")
    print(report.get("header"))
    print(report.get("body"))
    print("source:", report.get("source"), "as_of:", report.get("as_of"))
