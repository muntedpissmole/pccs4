"""Resolve approximate location from the host's public IP (demo mode)."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger("pccs")

_USER_AGENT = "PCCS4-Demo/1.0 (https://github.com/muntedpissmole/pccs4)"


def _format_place(city: str | None, region: str | None) -> str | None:
    city = (city or "").strip()
    region = (region or "").strip()
    if city and region and city.lower() != region.lower():
        return f"{city}, {region}"
    return city or region or None


def _from_ipapi_co(data: dict[str, Any]) -> dict[str, Any] | None:
    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is None or lon is None:
        return None
    place = _format_place(data.get("city"), data.get("region"))
    timezone = (data.get("timezone") or "").strip() or None
    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "place": place,
        "timezone": timezone,
        "source": "ipapi.co",
    }


def _from_ip_api(data: dict[str, Any]) -> dict[str, Any] | None:
    if data.get("status") != "success":
        return None
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is None or lon is None:
        return None
    place = _format_place(data.get("city"), data.get("regionName"))
    timezone = (data.get("timezone") or "").strip() or None
    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "place": place,
        "timezone": timezone,
        "source": "ip-api.com",
    }


def fetch_ip_geolocation(timeout: float = 8.0) -> dict[str, Any] | None:
    """Best-effort public-IP geolocation. Returns None if every provider fails."""
    providers = (
        (
            "https://ipapi.co/json/",
            _from_ipapi_co,
        ),
        (
            "http://ip-api.com/json/?fields=status,message,lat,lon,city,regionName,timezone",
            _from_ip_api,
        ),
    )
    headers = {"User-Agent": _USER_AGENT}

    for url, parser in providers:
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            parsed = parser(response.json())
            if parsed:
                logger.info(
                    "📍 IP geolocation via %s → %s (%.4f, %.4f)",
                    parsed["source"],
                    parsed.get("place") or "unknown",
                    parsed["latitude"],
                    parsed["longitude"],
                )
                return parsed
        except (OSError, requests.RequestException, ValueError, TypeError) as exc:
            logger.debug("IP geolocation failed for %s: %s", url, exc)

    logger.warning("📍 IP geolocation unavailable — using demo config fallbacks")
    return None