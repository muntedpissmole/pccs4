"""Simulated Victron shunt + MPPT — live-looking battery and solar numbers."""

from __future__ import annotations

import logging
import math
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger("pccs")


class DemoVictronManager:
    """VictronManager-compatible simulator with slowly varying power metrics."""

    def __init__(self, socketio, config, phase_manager=None):
        self.socketio = socketio
        self.config = config
        self.phase_manager = phase_manager
        self._running = False
        self._thread: threading.Thread | None = None
        self._start = time.time()
        self._yield_today = 0.0

        base_soc = config.getfloat("demo", "battery_soc", fallback=78.0)
        self.state = {
            "stale": False,
            "soc": base_soc,
            "voltage": 13.2,
            "current_a": -2.4,
            "consumed_ah": 12.5,
            "time_to_go_mins": 1440,
            "solar_power_w": 180,
            "solar_current_a": 8.5,
            "yield_today_kwh": 1.2,
            "charge_state": "bulk",
            "temperature": 22.0,
            "last_update": datetime.now(timezone.utc).isoformat(),
            "shunt": {"configured": True, "connected": True},
            "mppt": {"configured": True, "connected": True},
            "demo_mode": True,
        }

        logger.info("🔋 Demo Victron — simulated shunt + MPPT")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DemoVictron")
        self._thread.start()
        self._emit()

    def stop(self):
        self._running = False

    def reset_daily_generation(self):
        self._yield_today = 0.0
        self.state["yield_today_kwh"] = 0.0

    def get_state(self) -> dict:
        return dict(self.state)

    def _loop(self):
        while self._running:
            try:
                t = time.time() - self._start
                hour = max(0.05, math.sin(t / 180.0) * 0.5 + 0.5)
                solar_a = round(2.0 + hour * 12.0, 1)
                solar_w = int(solar_a * 21.5)
                soc = max(45.0, min(99.0, self.config.getfloat("demo", "battery_soc", fallback=78.0) + math.sin(t / 600.0) * 6.0))
                current = round(-1.5 - hour * 4.0, 1)

                self._yield_today += solar_w / 3600000.0 * 5.0
                self.state.update({
                    "soc": round(soc, 1),
                    "voltage": round(12.6 + soc / 100.0 * 1.2, 2),
                    "current_a": current,
                    "solar_current_a": solar_a,
                    "solar_power_w": solar_w,
                    "yield_today_kwh": round(self._yield_today, 2),
                    "time_to_go_mins": int(1440 + current * -60),
                    "last_update": datetime.now(timezone.utc).isoformat(),
                    "stale": False,
                })
                self._emit()
            except Exception as e:
                logger.debug(f"Demo Victron loop: {e}")
            time.sleep(5.0)

    def _emit(self):
        if self.socketio:
            self.socketio.emit("victron_update", self.get_state())