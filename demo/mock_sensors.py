"""Simulated water tank and temperature sensors."""

from __future__ import annotations

import logging
import math
import threading
import time

from demo.water_scheduler import current_water_level_pct

logger = logging.getLogger("pccs")


class DemoSensorManager:
    """SensorManager-compatible simulator — no 1-Wire or Arduino analog reads."""

    def __init__(self, config, send_command_func, socketio):
        self.config = config
        self.send_command = send_command_func
        self.socketio = socketio
        self.running = False
        self.thread = None
        self.last_reading: dict = {}
        self._start = time.time()

        self.WATER_CAPACITY_LITRES = config.getfloat("tanks", "water_litres", fallback=120.0)
        logger.info("🔋 Demo SensorManager — simulated water + temperatures")

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="DemoSensors")
        self.thread.start()
        self.update_sensors()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self.update_sensors()
            except Exception as e:
                logger.debug(f"Demo sensors: {e}")
            time.sleep(30.0)

    def _outside_temp_c(self, elapsed_s: float) -> float:
        """Drift within today's forecast min/max so the live reading matches the daily range."""
        try:
            from weather import get_weather_status

            wx = get_weather_status()
            t_min = wx.get("temp_min")
            t_max = wx.get("temp_max")
            if t_min is not None and t_max is not None:
                lo = float(t_min)
                hi = float(t_max)
                if hi > lo:
                    phase = 0.5 + 0.5 * math.sin(elapsed_s / 1200.0)
                    return lo + (hi - lo) * phase
                return lo
        except Exception as e:
            logger.debug(f"Demo outside temp from forecast: {e}")

        return 18.0 + math.sin(elapsed_s / 1200.0) * 4.0

    def update_sensors(self):
        t = time.time() - self._start
        water_pct = current_water_level_pct()
        water_pct = max(0.0, min(100.0, water_pct + math.sin(t / 900.0) * 1.5))

        outside = self._outside_temp_c(t)
        fridge = 4.0 + math.sin(t / 800.0) * 0.4
        freezer = -18.0 + math.sin(t / 700.0) * 0.5

        litres = round(self.WATER_CAPACITY_LITRES * water_pct / 100.0, 1)
        payload = {
            "water_percent": round(water_pct, 1),
            "water_litres": litres,
            "water_capacity_litres": self.WATER_CAPACITY_LITRES,
            "outside_temp_c": round(outside, 1),
            "fridge_temp_c": round(fridge, 1),
            "freezer_temp_c": round(freezer, 1),
            "demo_mode": True,
        }
        self.last_reading = payload
        if self.socketio:
            self.socketio.emit("sensor_update", payload)