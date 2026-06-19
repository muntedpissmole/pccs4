"""Simulated Victron shunt + MPPT for demo mode — self-contained tile telemetry."""

from __future__ import annotations

import copy
import logging
import math
import threading
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("pccs")

_DEMO_SHUNT = {
    "address": "aa:bb:cc:11:22:33",
    "alarm": "No Alarm",
    "aux_mode": "Temperature",
    "configured": True,
    "connected": True,
    "consumed_ah": 8.5,
    "current": -2.1,
    "midpoint_voltage": None,
    "model_name": "SmartShunt 500A/50mV",
    "name": "Demo SmartShunt",
    "remaining_mins": 1180,
    "rssi": -58,
    "soc": 78.0,
    "stale": False,
    "starter_voltage": None,
    "temperature": 22.0,
    "voltage": 13.24,
}

_DEMO_MPPT = {
    "address": "aa:bb:cc:44:55:66",
    "battery_charging_current": 6.8,
    "battery_voltage": 13.22,
    "charge_state": "Bulk",
    "charger_error": "No Error",
    "configured": True,
    "connected": True,
    "external_device_load": None,
    "model_name": "SmartSolar Charger MPPT 100/50",
    "name": "Demo SmartSolar",
    "rssi": -61,
    "solar_power": 145.0,
    "stale": False,
    "yield_today_wh": 820.0,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DemoVictronManager:
    """VictronManager-compatible simulator with slowly varying power metrics."""

    def __init__(self, socketio, config, phase_manager=None):
        self.socketio = socketio
        self.config = config
        self.phase_manager = phase_manager
        self._running = False
        self._thread: threading.Thread | None = None
        self._start = time.time()
        self._yield_today_wh = float(_DEMO_MPPT["yield_today_wh"])

        self.state: dict[str, Any] = {
            "stale": False,
            "demo_mode": True,
        }
        self._apply_variation(initial=True)

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
        self._yield_today_wh = 0.0
        mppt = self.state.get("mppt")
        if isinstance(mppt, dict):
            mppt["yield_today_wh"] = 0.0
        self.state["yield_today_kwh"] = 0.0

    def get_state(self) -> dict:
        return copy.deepcopy(self.state)

    def _apply_variation(self, initial: bool = False) -> None:
        t = 0.0 if initial else time.time() - self._start
        hour = max(0.05, math.sin(t / 180.0) * 0.5 + 0.5)

        base_soc = self.config.getfloat("demo", "battery_soc", fallback=_DEMO_SHUNT["soc"])
        soc = max(45.0, min(99.0, base_soc + math.sin(t / 600.0) * 4.0))
        solar_w = int(20 + hour * 180)
        solar_a = round(solar_w / 21.5, 1) if solar_w else 0.0
        current = round(-1.2 - hour * 3.5, 1)
        voltage = round(12.6 + soc / 100.0 * 1.1, 2)
        temp = round(20.0 + math.sin(t / 900.0) * 2.0, 1)
        now = _now_iso()

        if not initial:
            self._yield_today_wh += solar_w / 3600.0 * 5.0

        shunt = copy.deepcopy(_DEMO_SHUNT)
        mppt = copy.deepcopy(_DEMO_MPPT)
        shunt.update({
            "soc": round(soc, 1),
            "voltage": voltage,
            "current": current,
            "consumed_ah": round(8.5 + max(0.0, (base_soc - soc)) * 0.2, 1),
            "remaining_mins": int(900 + soc * 6),
            "temperature": temp,
            "rssi": -58 + int(math.sin(t / 45.0) * 2),
            "last_update": now,
        })
        mppt.update({
            "battery_voltage": round(voltage - 0.02, 2),
            "battery_charging_current": solar_a if solar_w else 0.0,
            "charge_state": "Bulk" if solar_w > 30 else "Off",
            "solar_power": float(solar_w),
            "yield_today_wh": round(self._yield_today_wh, 1),
            "rssi": -61 + int(math.cos(t / 50.0) * 2),
            "last_update": now,
        })

        self.state.update({
            "stale": False,
            "soc": shunt["soc"],
            "voltage": shunt["voltage"],
            "current_a": current,
            "consumed_ah": shunt["consumed_ah"],
            "time_to_go_mins": shunt["remaining_mins"],
            "solar_power_w": solar_w,
            "solar_current_a": solar_a,
            "yield_today_kwh": round(self._yield_today_wh / 1000.0, 2),
            "charge_state": mppt["charge_state"],
            "temperature": temp,
            "last_update": now,
            "shunt": shunt,
            "mppt": mppt,
            "demo_mode": True,
        })

    def _loop(self):
        while self._running:
            try:
                self._apply_variation()
                self._emit()
            except Exception as e:
                logger.debug(f"Demo Victron loop: {e}")
            time.sleep(5.0)

    def _emit(self):
        if self.socketio:
            self.socketio.emit("victron_update", self.get_state())