"""Weather conditions — Open-Meteo forecast using live GPS coordinates when available."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import requests

_gps_module = None

_DEFAULT_LAT = -37.191
_DEFAULT_LNG = 145.711

_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None}
_CACHE_TTL = 300.0

_SUMMARIES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    95: "Thunderstorm",
}

_UNAVAILABLE: dict[str, Any] = {
    "summary": None,
    "temperature_c": None,
    "feels_like_c": None,
    "wind_kmh": None,
    "wind_direction_deg": None,
    "rain_chance_percent": None,
    "humidity_percent": None,
    "cloud_cover_percent": None,
    "low_tonight_c": None,
    "temp_min": None,
    "temp_max": None,
    "hourly_forecast": [],
    "daily_forecast": [],
    "weather_code": None,
    "is_day": None,
    "source": "unavailable",
}


def set_gps_module(gps_module) -> None:
    global _gps_module
    _gps_module = gps_module


def _coords() -> tuple[float, float]:
    if _gps_module is not None:
        state = _gps_module.get_state()
        lat = state.get("latitude")
        lng = state.get("longitude")
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    return _DEFAULT_LAT, _DEFAULT_LNG


def _summary_for_code(code: int | None) -> str:
    if code is None:
        return "—"
    return _SUMMARIES.get(int(code), "Mixed conditions")


def _fetch_open_meteo(lat: float, lng: float) -> dict[str, Any] | None:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lng}"
        "&models=gfs_seamless"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode"
        "&hourly=temperature_2m"
        "&past_hours=6"
        "&forecast_hours=24"
        "&current=relative_humidity_2m,temperature_2m,weather_code,is_day,"
        "wind_speed_10m,wind_direction_10m,apparent_temperature,cloud_cover"
        "&timezone=auto"
    )
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        return response.json()
    except (OSError, requests.RequestException):
        return None


def get_weather_status() -> dict[str, Any]:
    now = time.time()
    if _CACHE["payload"] and now - _CACHE["ts"] < _CACHE_TTL:
        return dict(_CACHE["payload"])

    lat, lng = _coords()
    data = _fetch_open_meteo(lat, lng)
    if not data:
        cached = _CACHE["payload"]
        if cached:
            return dict(cached)
        return dict(_UNAVAILABLE)

    current = data.get("current") or {}
    daily = data.get("daily") or {}
    code = current.get("weather_code")
    payload: dict[str, Any] = {
        "summary": _summary_for_code(code),
        "temperature_c": current.get("temperature_2m"),
        "feels_like_c": current.get("apparent_temperature"),
        "wind_kmh": current.get("wind_speed_10m"),
        "wind_direction_deg": current.get("wind_direction_10m"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "cloud_cover_percent": current.get("cloud_cover"),
        "weather_code": code,
        "is_day": bool(current.get("is_day") == 1),
        "latitude": lat,
        "longitude": lng,
        "source": "open-meteo",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    hourly = data.get("hourly") or {}
    hour_times = hourly.get("time") or []
    hour_temps = hourly.get("temperature_2m") or []
    hour_count = min(len(hour_times), len(hour_temps))
    if hour_count:
        payload["hourly_forecast"] = [
            {
                "time": hour_times[i],
                "temperature_c": hour_temps[i],
            }
            for i in range(hour_count)
            if hour_temps[i] is not None
        ]

    day_times = daily.get("time") or []
    mins = daily.get("temperature_2m_min") or []
    maxs = daily.get("temperature_2m_max") or []
    day_codes = daily.get("weathercode") or []
    rain = daily.get("precipitation_probability_max") or []
    day_count = min(len(day_times), len(mins), len(maxs), len(day_codes))
    if day_count:
        payload["daily_forecast"] = [
            {
                "date": day_times[i],
                "weather_code": day_codes[i],
                "temp_min": mins[i],
                "temp_max": maxs[i],
            }
            for i in range(day_count)
        ]
    if mins:
        payload["temp_min"] = mins[0]
        payload["low_tonight_c"] = mins[0]
    if maxs:
        payload["temp_max"] = maxs[0]
    if rain:
        payload["rain_chance_percent"] = rain[0]

    _CACHE.update({"ts": now, "payload": payload})
    return dict(payload)