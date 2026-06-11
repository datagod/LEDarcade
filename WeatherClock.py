"""
Fetch and format local weather reports for LEDarcade terminal scrolling.
"""

import os
import traceback
import urllib.parse
from configparser import ConfigParser

import requests

KeyConfigFileName = "KeyConfig.ini"
DEFAULT_LOCATION = "Franktown"
WEATHER_TYPE_SPEED = 0.064  # 25% faster than default terminal TypeSpeed of 0.08
WEATHER_SCROLL_REPEAT = 2
WEATHER_POST_SCROLL_WAIT = 30  # seconds to idle after scrolling before exiting
WEATHER_HEADER_RGB = (200, 200, 0)


def CheckConfigFiles():
    if os.path.exists(KeyConfigFileName):
        return

    try:
        with open(KeyConfigFileName, "a+") as config_file:
            config_file.write("[KEYS]\n")
            config_file.write("WEATHER_LOCATION = Franktown\n")
            config_file.write("\n")
        print(f"[WeatherClock] Created default {KeyConfigFileName}")
    except Exception as error:
        print(f"[WeatherClock] Could not create {KeyConfigFileName}: {error}")


def LoadWeatherLocation(location_override=""):
    if location_override:
        return location_override.strip()

    CheckConfigFiles()
    if not os.path.exists(KeyConfigFileName):
        return DEFAULT_LOCATION

    try:
        key_file = ConfigParser()
        key_file.read(KeyConfigFileName)
        return key_file.get("KEYS", "WEATHER_LOCATION", fallback=DEFAULT_LOCATION).strip() or DEFAULT_LOCATION
    except Exception as error:
        print(f"[WeatherClock] Config read error: {error}")
        return DEFAULT_LOCATION


def NormalizeUnits(units="F"):
    """Return 'C' or 'F' for supported temperature units."""
    if str(units).strip().upper().startswith("C"):
        return "C"
    return "F"


def FetchWeatherReport(location, units="F"):
    """Fetch weather from wttr.in and return a scrollable text report."""
    units = NormalizeUnits(units)
    encoded_location = urllib.parse.quote(location)
    url = f"https://wttr.in/{encoded_location}?format=j1"

    try:
        response = requests.get(
            url,
            timeout=12,
            headers={"User-Agent": "LEDarcade-WeatherClock/1.0"},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as error:
        print(f"[WeatherClock] Fetch failed for '{location}': {error}")
        return {"header": "", "body": f"Weather unavailable for {location}. {error}"}

    try:
        area = data["nearest_area"][0]["areaName"][0]["value"]
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

        condition = current["weatherDesc"][0]["value"]
        humidity = current.get("humidity", "?")
        wind_dir = current.get("winddir16Point", "")

        body_parts = [
            f"Now {temp}{temp_label}, {condition}.",
            f"Feels like {feels}{temp_label}.",
            f"Humidity {humidity}%.",
            f"Wind {wind_speed} {wind_label} {wind_dir}.".strip(),
            f"Today high {today_high}{temp_label}, low {today_low}{temp_label}.",
        ]

        if tomorrow:
            if units == "C":
                tomorrow_high = tomorrow.get("maxtempC", "?")
                tomorrow_low = tomorrow.get("mintempC", "?")
            else:
                tomorrow_high = tomorrow.get("maxtempF", "?")
                tomorrow_low = tomorrow.get("mintempF", "?")
            tomorrow_desc = tomorrow["hourly"][4]["weatherDesc"][0]["value"]
            body_parts.append(
                f"Tomorrow {tomorrow_desc}, high {tomorrow_high}{temp_label}, low {tomorrow_low}{temp_label}."
            )

        header = f"Weather for {area}."
        body = " ".join(body_parts)
        return {"header": header, "body": body}
    except Exception as error:
        print(f"[WeatherClock] Parse error: {error}")
        traceback.print_exc()
        return {"header": "", "body": f"Weather data parse error for {location}."}