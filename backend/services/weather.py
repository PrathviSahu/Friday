"""
FRIDAY Weather Service
Fetches live weather data using Open-Meteo (no API key required).
Supports IP-based auto location AND specific city search.
"""
import urllib.request
import urllib.parse
import json


import os

def _get_ip_location() -> tuple[float, float, str]:
    """Fetch current location via ip-api.com, falling back to WEATHER_CITY or Thane."""
    default_city = os.getenv("WEATHER_CITY", "Thane").strip()
    try:
        req = urllib.request.Request(
            "http://ip-api.com/json/",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                return (
                    float(data.get("lat")),
                    float(data.get("lon")),
                    str(data.get("city", default_city))
                )
    except Exception as e:
        print(f"[Weather] IP location lookup failed: {e}")
    return 19.2183, 72.9781, default_city


def _geocode_city(city_name: str) -> tuple[float, float, str] | None:
    """Geocode a city name to (lat, lon, official_name) via Open-Meteo Geocoding API."""
    try:
        query = urllib.parse.quote(city_name.strip())
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=1&language=en&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results")
            if results and len(results) > 0:
                first = results[0]
                return (
                    float(first["latitude"]),
                    float(first["longitude"]),
                    str(first.get("name", city_name))
                )
    except Exception as e:
        print(f"[Weather] Geocoding failed for '{city_name}': {e}")
    return None


def get_weather(city_query: str | None = None) -> dict:
    """Fetch live weather data from Open-Meteo API."""
    lat, lon, city = None, None, None

    if city_query and city_query.strip():
        geo = _geocode_city(city_query)
        if geo:
            lat, lon, city = geo

    if lat is None:
        lat, lon, city = _get_ip_location()

    WEATHER_CODES = {
        0: ("Clear Sky", "☀️"),
        1: ("Mainly Clear", "🌤️"),
        2: ("Partly Cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Foggy", "🌫️"),
        48: ("Rime Fog", "🌫️"),
        51: ("Light Drizzle", "🌧️"),
        53: ("Moderate Drizzle", "🌧️"),
        55: ("Dense Drizzle", "🌧️"),
        61: ("Slight Rain", "🌧️"),
        63: ("Moderate Rain", "🌧️"),
        65: ("Heavy Rain", "🌧️"),
        80: ("Rain Showers", "🌦️"),
        95: ("Thunderstorm", "🌩️"),
    }

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            curr = data.get("current", {})
            daily = data.get("daily", {})

            code = curr.get("weather_code", 0)
            condition, icon = WEATHER_CODES.get(code, ("Clear", "☀️"))

            return {
                "city": city,
                "temperature": round(curr.get("temperature_2m", 25)),
                "feels_like": round(curr.get("apparent_temperature", 25)),
                "humidity": curr.get("relative_humidity_2m", 60),
                "wind_speed": round(curr.get("wind_speed_10m", 10)),
                "condition": condition,
                "icon": icon,
                "temp_max": round(daily.get("temperature_2m_max", [28])[0]),
                "temp_min": round(daily.get("temperature_2m_min", [20])[0]),
                "is_day": bool(curr.get("is_day", 1)),
            }
    except Exception as e:
        print(f"[Weather] Error fetching weather: {e}")
        return {
            "city": city or "Nashik",
            "temperature": 23,
            "feels_like": 24,
            "humidity": 90,
            "wind_speed": 15,
            "condition": "Partly Cloudy",
            "icon": "⛅",
            "temp_max": 26,
            "temp_min": 21,
            "is_day": True,
        }
