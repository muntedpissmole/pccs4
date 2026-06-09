"""LPG tank level — live from SensorManager when a sensor is configured."""

from __future__ import annotations

from typing import Any

_sensor_manager = None

_DEMO: dict[str, Any] = {
    "level_percent": None,
    "enabled": False,
    "source": "unconfigured",
}


def set_sensor_manager(sensor_manager) -> None:
    global _sensor_manager
    _sensor_manager = sensor_manager


def get_lpg_status() -> dict[str, Any]:
    if _sensor_manager is None:
        return dict(_DEMO)

    reading = getattr(_sensor_manager, "last_reading", None) or {}
    level = reading.get("lpg_percent")
    if level is None:
        return dict(_DEMO)

    return {
        "level_percent": int(level),
        "enabled": True,
        "source": "live",
    }