"""Randomly open and close reed switches every few hours for demo realism."""

from __future__ import annotations

import logging
import random
import threading
import time

logger = logging.getLogger("pccs")


class DemoReedScheduler:
    """Background thread that toggles simulated reeds on a random interval."""

    def __init__(self, gpio_manager, config):
        self._gpio = gpio_manager
        self._config = config
        self._running = False
        self._thread: threading.Thread | None = None

        self._min_hours = config.getfloat("demo", "reed_toggle_min_hours", fallback=2.0)
        self._max_hours = config.getfloat("demo", "reed_toggle_max_hours", fallback=6.0)
        self._enabled = config.getboolean("demo", "reed_random_toggle", fallback=True)

    def start(self):
        if not self._enabled or not self._gpio.reeds:
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DemoReedScheduler")
        self._thread.start()
        logger.info(
            f"🚪 Demo reed scheduler — random toggle every "
            f"{self._min_hours:.1f}–{self._max_hours:.1f} h"
        )

    def stop(self):
        self._running = False

    def _next_delay_s(self) -> float:
        hours = random.uniform(self._min_hours, self._max_hours)
        return hours * 3600.0

    def _loop(self):
        while self._running:
            delay = self._next_delay_s()
            if self._sleep(delay):
                break
            try:
                self._toggle_random_reed()
            except Exception as e:
                logger.debug(f"Demo reed scheduler: {e}")

    def _sleep(self, seconds: float) -> bool:
        end = time.time() + seconds
        while self._running and time.time() < end:
            time.sleep(min(30.0, end - time.time()))
        return not self._running

    def _toggle_random_reed(self):
        names = list(self._gpio.reeds.keys())
        if not names:
            return

        name = random.choice(names)
        current = self._gpio.reed_states.get(name, True)
        new_state = not current
        self._gpio.set_reed_closed(name, new_state)
        action = "CLOSED" if new_state else "OPEN"
        logger.info(f"🚪 Demo reed scheduler → {name} {action}")