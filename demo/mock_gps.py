"""GPS simulation — local system time and IP-geolocated demo coordinates."""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime

import zoneinfo
from astral import LocationInfo
from astral.sun import sun

from demo.ip_geolocation import fetch_ip_geolocation

logger = logging.getLogger("pccs")

# Fixed demo location — never fall back to [gps] (may be stale on upgraded installs).
_DEFAULT_LAT = -37.8136
_DEFAULT_LON = 144.9631
_DEFAULT_SUBURB = "Melbourne CBD"
_DEFAULT_TIMEZONE = "Australia/Melbourne"


class DemoGPSModule:
    """GPS module that uses the host clock and IP-geolocated coordinates (no serial hardware)."""

    def __init__(self, config, socketio):
        self.config = config
        self.socketio = socketio
        self.serial = None
        self.geolocator = None
        self._stop_event = threading.Event()
        self._reader_thread: threading.Thread | None = None
        self._geo_thread: threading.Thread | None = None
        self._state_lock = threading.Lock()

        self.fallback_timezone = config.get(
            "demo", "timezone", fallback=_DEFAULT_TIMEZONE,
        )

        self._pinned_lat = config.getfloat("demo", "latitude", fallback=_DEFAULT_LAT)
        self._pinned_lon = config.getfloat("demo", "longitude", fallback=_DEFAULT_LON)
        self._pinned_suburb = config.get("demo", "suburb", fallback=_DEFAULT_SUBURB)
        self._ip_geolocation_enabled = config.getboolean("demo", "ip_geolocation", fallback=False)

        lat = self._pinned_lat
        lon = self._pinned_lon
        suburb = self._pinned_suburb

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
            "altitude_m": 12.0,
            "suburb": suburb,
            "timezone": self.fallback_timezone,
            "last_known_suburb": suburb,
            "sunrise": None,
            "sunset": None,
            "raw_sentences": [],
            "using_fallback": True,
            "force_no_fix": False,
            "force_no_hardware": False,
            "hardware_missing": False,
            "demo_mode": True,
            "location_source": "config",
        }

        self._update_sun_times()
        logger.info(
            f"📍 Demo GPS — {suburb} ({lat:.4f}, {lon:.4f}) config fallback; "
            f"IP geolocation {'enabled' if self._ip_geolocation_enabled else 'disabled'}"
        )

    def _active_timezone(self) -> str:
        with self._state_lock:
            return self.state.get("timezone") or self.fallback_timezone

    def _update_sun_times(self):
        try:
            tz_name = self._active_timezone()
            tz = zoneinfo.ZoneInfo(tz_name)
            with self._state_lock:
                lat = float(self.state["latitude"])
                lon = float(self.state["longitude"])
            loc = LocationInfo(latitude=lat, longitude=lon, timezone=tz_name)
            today = date.today()
            s = sun(loc.observer, date=today, tzinfo=tz)
            with self._state_lock:
                self.state["sunrise"] = s["sunrise"].strftime("%I:%M %p").lstrip("0")
                self.state["sunset"] = s["sunset"].strftime("%I:%M %p").lstrip("0")
        except Exception as e:
            logger.warning(f"Demo GPS sun calc failed: {e}")

    def _apply_geolocation(self, geo: dict) -> bool:
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        if lat is None or lon is None:
            return False

        place = (geo.get("place") or "").strip()
        timezone = (geo.get("timezone") or "").strip()
        changed = False

        with self._state_lock:
            if float(self.state["latitude"]) != float(lat) or float(self.state["longitude"]) != float(lon):
                changed = True
            self.state["latitude"] = float(lat)
            self.state["longitude"] = float(lon)
            if place:
                self.state["suburb"] = place
                self.state["last_known_suburb"] = place
            if timezone:
                self.state["timezone"] = timezone
                self.fallback_timezone = timezone
            self.state["using_fallback"] = False
            self.state["location_source"] = geo.get("source") or "ip"

        if changed or place or timezone:
            self._update_sun_times()
            try:
                from weather import invalidate_cache

                invalidate_cache()
            except Exception:
                pass
            if self.socketio:
                self.socketio.emit("gps_update", self.get_state())
            logger.info(
                "📍 Demo GPS updated from IP → %s (%.4f, %.4f)",
                place or "geolocated",
                lat,
                lon,
            )
            return True
        return False

    def _resolve_ip_geolocation(self):
        geo = fetch_ip_geolocation()
        if geo:
            self._apply_geolocation(geo)

    def init_gps(self):
        return

    def init_geolocator(self):
        if not self._ip_geolocation_enabled:
            return
        if self._geo_thread and self._geo_thread.is_alive():
            return
        self._geo_thread = threading.Thread(
            target=self._resolve_ip_geolocation,
            daemon=True,
            name="DemoIPGeolocation",
        )
        self._geo_thread.start()

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
                tz = zoneinfo.ZoneInfo(self._active_timezone())
                now = datetime.now(tz)
                with self._state_lock:
                    self.state["local_time"] = now.strftime("%H:%M:%S")
                    self.state["date"] = now.strftime("%Y-%m-%d")
                    self.state["utc_time"] = datetime.now(zoneinfo.ZoneInfo("UTC")).isoformat()
                if self.socketio:
                    self.socketio.emit("gps_update", self.get_state())
            except Exception as e:
                logger.debug(f"Demo GPS tick: {e}")

    def get_state(self) -> dict:
        with self._state_lock:
            state = dict(self.state)
        if not self._ip_geolocation_enabled:
            state["latitude"] = self._pinned_lat
            state["longitude"] = self._pinned_lon
            state["suburb"] = self._pinned_suburb
            state["last_known_suburb"] = self._pinned_suburb
            state["timezone"] = self.fallback_timezone
            state["using_fallback"] = True
            state["location_source"] = "config"
        return state

    def get_fallback_coords(self) -> tuple[float, float]:
        return float(self._pinned_lat), float(self._pinned_lon)

    def get_fallback_timezone(self) -> str:
        return self._active_timezone()

    def get_fallback_name(self) -> str:
        return self._pinned_suburb

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