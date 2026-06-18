"""GPS simulation — local system time and configured demo coordinates."""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime

import zoneinfo
from astral import LocationInfo
from astral.sun import sun

logger = logging.getLogger("pccs")


class DemoGPSModule:
    """GPS module that uses the host clock and demo coordinates (no serial hardware)."""

    def __init__(self, config, socketio):
        self.config = config
        self.socketio = socketio
        self.serial = None
        self.geolocator = None
        self._stop_event = threading.Event()
        self._reader_thread: threading.Thread | None = None

        self.fallback_timezone = config.get(
            "demo", "timezone",
            fallback=config.get("gps", "fallback_timezone", fallback="Australia/Melbourne"),
        )

        lat = config.getfloat("demo", "latitude", fallback=None)
        lon = config.getfloat("demo", "longitude", fallback=None)
        if lat is None or lon is None:
            lat = config.getfloat("gps", "fallback_latitude", fallback=-37.191)
            lon = config.getfloat("gps", "fallback_longitude", fallback=145.711)

        suburb = config.get("demo", "suburb", fallback=config.get("gps", "fallback_name", fallback="Demo"))

        self.state = {
            "latitude": lat,
            "longitude": lon,
            "local_time": None,
            "date": None,
            "utc_time": None,
            "satellites": 8,
            "fix_quality": 1,
            "hdop": 1.2,
            "speed_kmh": 0.0,
            "altitude_m": 120.0,
            "suburb": suburb,
            "timezone": self.fallback_timezone,
            "last_known_suburb": suburb,
            "sunrise": None,
            "sunset": None,
            "raw_sentences": [],
            "using_fallback": False,
            "force_no_fix": False,
            "force_no_hardware": False,
            "hardware_missing": False,
            "demo_mode": True,
        }

        self._update_sun_times()
        logger.info(f"📍 Demo GPS — {suburb} ({lat:.4f}, {lon:.4f}), local time from host clock")

    def _update_sun_times(self):
        try:
            tz = zoneinfo.ZoneInfo(self.fallback_timezone)
            loc = LocationInfo(
                latitude=self.state["latitude"],
                longitude=self.state["longitude"],
                timezone=self.fallback_timezone,
            )
            today = date.today()
            s = sun(loc.observer, date=today, tzinfo=tz)
            self.state["sunrise"] = s["sunrise"].strftime("%I:%M %p").lstrip("0")
            self.state["sunset"] = s["sunset"].strftime("%I:%M %p").lstrip("0")
        except Exception as e:
            logger.warning(f"Demo GPS sun calc failed: {e}")

    def init_gps(self):
        return

    def init_geolocator(self):
        return

    def start_reader(self):
        if self._reader_thread and self._reader_thread.is_alive():
            return
        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._time_loop,
            daemon=True,
            name="DemoGPS",
        )
        self._reader_thread.start()

    def _time_loop(self):
        while not self._stop_event.wait(1.0):
            try:
                tz = zoneinfo.ZoneInfo(self.fallback_timezone)
                now = datetime.now(tz)
                self.state["local_time"] = now.strftime("%H:%M:%S")
                self.state["date"] = now.strftime("%Y-%m-%d")
                self.state["utc_time"] = datetime.now(zoneinfo.ZoneInfo("UTC")).isoformat()
                if self.socketio:
                    self.socketio.emit("gps_update", self.get_state())
            except Exception as e:
                logger.debug(f"Demo GPS tick: {e}")

    def get_state(self) -> dict:
        return dict(self.state)

    def get_fallback_coords(self) -> tuple[float, float]:
        return float(self.state["latitude"]), float(self.state["longitude"])

    def get_fallback_timezone(self) -> str:
        return self.fallback_timezone

    def get_fallback_name(self) -> str:
        return self.state.get("suburb") or "Demo"

    def get_fallback_data(self) -> dict:
        lat, lon = self.get_fallback_coords()
        return {
            "latitude": lat,
            "longitude": lon,
            "name": self.get_fallback_name(),
            "timezone": self.get_fallback_timezone(),
        }

    def set_no_fix_simulation(self, enabled: bool):
        self.state["force_no_fix"] = bool(enabled)
        if enabled:
            self.state["fix_quality"] = 0
        else:
            self.state["fix_quality"] = 1

    def set_no_hardware_simulation(self, enabled: bool):
        self.state["force_no_hardware"] = bool(enabled)

    def cleanup(self):
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2)