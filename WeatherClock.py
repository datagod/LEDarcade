"""
Fetch and format local weather reports for LEDarcade terminal scrolling.
"""

import os
import traceback
import urllib.parse
from configparser import ConfigParser

import requests

KeyConfigFileName = "KeyConfig.ini"
DEFAULT_LOCATION = "Ottawa"


def CheckConfigFiles():
    if os.path.exists(KeyConfigFileName):
        return

    try:
        with open(KeyConfigFileName, "a+") as config_file:
            config_file.write("[KEYS]\n")
            config_file.write("WEATHER_LOCATION = Ottawa\n")
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


def FetchWeatherReport(location):
    """Fetch weather from wttr.in and return a scrollable text report."""
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
        return f"Weather unavailable for {location}. {error}"

    try:
        area = data["nearest_area"][0]["areaName"][0]["value"]
        current = data["current_condition"][0]
        today = data["weather"][0]
        tomorrow = data["weather"][1] if len(data.get("weather", [])) > 1 else None

        temp_f = current.get("temp_F", "?")
        feels_f = current.get("FeelsLikeF", temp_f)
        condition = current["weatherDesc"][0]["value"]
        humidity = current.get("humidity", "?")
        wind_mph = current.get("windspeedMiles", "?")
        wind_dir = current.get("winddir16Point", "")
        today_high = today.get("maxtempF", "?")
        today_low = today.get("mintempF", "?")

        parts = [
            f"Weather for {area}.",
            f"Now {temp_f}F, {condition}.",
            f"Feels like {feels_f}F.",
            f"Humidity {humidity}%.",
            f"Wind {wind_mph} mph {wind_dir}.".strip(),
            f"Today high {today_high}F, low {today_low}F.",
        ]

        if tomorrow:
            tomorrow_high = tomorrow.get("maxtempF", "?")
            tomorrow_low = tomorrow.get("mintempF", "?")
            tomorrow_desc = tomorrow["hourly"][4]["weatherDesc"][0]["value"]
            parts.append(
                f"Tomorrow {tomorrow_desc}, high {tomorrow_high}F, low {tomorrow_low}F."
            )

        return " ".join(parts)
    except Exception as error:
        print(f"[WeatherClock] Parse error: {error}")
        traceback.print_exc()
        return f"Weather data parse error for {location}."