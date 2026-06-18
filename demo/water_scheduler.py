"""Drift simulated fresh-water tank level every few hours."""

from __future__ import annotations

import logging
import random
import threading
import time

logger = logging.getLogger("pccs")

_level: float = 72.0
_scheduler: "DemoWaterScheduler | None" = None


def current_water_level_pct() -> float:
    if _scheduler is not None:
        return _scheduler.level
    return _level


class DemoWaterScheduler:
    """Background thread that moves the demo tank level on a random interval."""

    def __init__(self, config):
        global _level, _scheduler

        self._config = config
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._enabled = config.getboolean("demo", "water_level_drift", fallback=True)
        self._min_hours = config.getfloat("demo", "water_level_min_hours", fallback=2.0)
        self._max_hours = config.getfloat("demo", "water_level_max_hours", fallback=6.0)
        self._min_pct = config.getfloat("demo", "water_level_min_pct", fallback=35.0)
        self._max_pct = config.getfloat("demo", "water_level_max_pct", fallback=95.0)

        base = config.getfloat("demo", "water_level_pct", fallback=72.0)
        with self._lock:
            self._level = max(self._min_pct, min(self._max_pct, base))
        _level = self._level
        _scheduler = self

    @property
    def level(self) -> float:
        with self._lock:
            return self._level

    def start(self):
        if not self._enabled:
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DemoWaterScheduler")
        self._thread.start()
        logger.info(
            "💧 Demo water scheduler — level drifts every "
            f"{self._min_hours:.1f}–{self._max_hours:.1f} h (currently {self.level:.0f}%)"
        )

    def stop(self):
        self._running = False

    def _next_delay_s(self) -> float:
        return random.uniform(self._min_hours, self._max_hours) * 3600.0

    def _loop(self):
        while self._running:
            delay = self._next_delay_s()
            if self._sleep(delay):
                break
            try:
                self._drift_level()
            except Exception as e:
                logger.debug(f"Demo water scheduler: {e}")

    def _sleep(self, seconds: float) -> bool:
        end = time.time() + seconds
        while self._running and time.time() < end:
            time.sleep(min(30.0, end - time.time()))
        return not self._running

    def _drift_level(self):
        global _level

        with self._lock:
            previous = self._level
            delta = random.uniform(-18.0, 18.0)
            self._level = max(self._min_pct, min(self._max_pct, previous + delta))
            current = self._level
        _level = current
        logger.info(f"💧 Demo water scheduler → {previous:.0f}% to {current:.0f}%")