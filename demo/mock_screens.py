"""Simulated remote touchscreens — brightness tracked in memory (no SSH)."""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger("pccs")


class DemoScreenActuator:
    """ScreenActuator-compatible simulator for reed-linked screen brightness."""

    def __init__(self, screens: dict, compiled):
        self._screens = screens
        self._compiled = compiled
        self._observed: Dict[str, int] = {name: 0 for name in screens}
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