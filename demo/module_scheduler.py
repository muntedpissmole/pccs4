"""Rotate which system-tile module appears offline — 3 of 4 stay online."""

from __future__ import annotations

import logging
import random
import threading
import time

logger = logging.getLogger("pccs")

MODULE_IDS = ("mppt", "shunt", "arduino", "gps")


class DemoModuleScheduler:
    """Background thread that marks one module offline and rotates it every few hours."""

    def __init__(self, config):
        self._config = config
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._enabled = config.getboolean("demo", "module_offline_rotate", fallback=True)
        self._min_hours = config.getfloat("demo", "module_offline_min_hours", fallback=2.0)
        self._max_hours = config.getfloat("demo", "module_offline_max_hours", fallback=6.0)
        self._offline_id = random.choice(MODULE_IDS)

    def get_connectivity(self) -> dict[str, bool]:
        with self._lock:
            offline = self._offline_id
        return {module_id: module_id != offline for module_id in MODULE_IDS}

    def start(self):
        if not self._enabled:
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DemoModuleScheduler")
        self._thread.start()
        logger.info(
            "📡 Demo module scheduler — 3/4 online; offline rotates every "
            f"{self._min_hours:.1f}–{self._max_hours:.1f} h (currently {self._offline_id})"
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
                self._rotate_offline_module()
            except Exception as e:
                logger.debug(f"Demo module scheduler: {e}")

    def _sleep(self, seconds: float) -> bool:
        end = time.time() + seconds
        while self._running and time.time() < end:
            time.sleep(min(30.0, end - time.time()))
        return not self._running

    def _rotate_offline_module(self):
        with self._lock:
            choices = [module_id for module_id in MODULE_IDS if module_id != self._offline_id]
            previous = self._offline_id
            self._offline_id = random.choice(choices)
            current = self._offline_id
        logger.info(f"📡 Demo module scheduler → {previous} online, {current} offline")