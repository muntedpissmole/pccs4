"""Simulated remote touchscreens — brightness tracked in memory (no SSH)."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("pccs")


class DemoScreenActuator:
    """ScreenActuator-compatible simulator for reed-linked screen brightness."""

    def __init__(self, screens: dict, compiled):
        self._screens = screens
        self._compiled = compiled
        self._observed: Dict[str, int] = {}
        for name, conf in screens.items():
            levels = conf.get("phase_brightness") or {}
            self._observed[name] = int(levels.get("day", 100))
        self._on_command_failed = None
        logger.info(f"🖥️ Demo screens — {len(screens)} simulated display(s)")

    def set_on_command_failed(self, callback):
        self._on_command_failed = callback

    def set_screen(self, name: str, brightness_pct: int):
        pct = max(0, min(100, int(brightness_pct)))
        self._observed[name] = pct
        logger.debug(f"🖥️ Demo screen {name} → {pct}%")

    def read_screens(self) -> Dict[str, int]:
        return dict(self._observed)

    def test_connectivity(self, name: str, timeout: float = 3.0) -> dict:
        conf = self._screens.get(name)
        if not conf:
            return {"online": False, "error": "No config"}

        pct = self._observed.get(name, 0)
        latency = max(1, int(timeout * 1000 * 0.15))
        time.sleep(min(timeout, 0.05))
        return {
            "online": True,
            "latency": latency,
            "ssh_passwordless": True,
            "last_checked": datetime.now().isoformat(),
            "brightness": pct * 100,
            "brightness_pct": pct,
            "on": pct > 0,
        }

    def manual_toggle(
        self,
        name: str,
        force_on: Optional[bool] = None,
        brightness_pct: Optional[int] = None,
    ):
        if brightness_pct is not None:
            self.set_screen(name, brightness_pct)
            return
        if force_on is None:
            force_on = self._observed.get(name, 0) <= 0
        if not force_on:
            self.set_screen(name, 0)
            return
        conf = self._screens.get(name) or {}
        levels = conf.get("phase_brightness") or {}
        fallback = max(levels.values(), default=100) if levels else 100
        self.set_screen(name, fallback)

    def shutdown_all(self):
        logger.info("🖥️ Demo screens shutdown_all — simulated (no remote power-off)")