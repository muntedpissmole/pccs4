"""Simulated GPIO — reeds and relays without gpiozero/LGPIO."""

from __future__ import annotations

import logging

logger = logging.getLogger("pccs")


class _MockRelay:
    def __init__(self, initial: bool):
        self._on = bool(initial)

    @property
    def value(self) -> bool:
        return self._on

    def on(self):
        self._on = True

    def off(self):
        self._on = False

    def close(self):
        return


class _MockReed:
    def __init__(self, closed: bool = True):
        self._closed = bool(closed)

    @property
    def is_pressed(self) -> bool:
        return self._closed

    @is_pressed.setter
    def is_pressed(self, closed: bool):
        self._closed = bool(closed)

    def close(self):
        return


class DemoGPIODeviceManager:
    """GPIO manager that parses pccs.conf but keeps all state in memory."""

    def __init__(self, config):
        self.config = config
        self.devices: dict = {}
        self.reeds: dict[str, _MockReed] = {}
        self.relays: dict[str, _MockRelay] = {}
        self.reed_states: dict[str, bool] = {}
        self.reed_to_light_map: dict[str, list] = {}
        self.relay_initial_states: dict[str, bool] = {}

    def _setup_pin_factory(self):
        return

    def init_devices(self) -> None:
        logger.debug("🔧 Demo GPIO — initializing simulated relays and reeds")

        if self.config.has_section("gpio"):
            gpio_section = self.config.get_section("gpio")
            for name, line in gpio_section.items():
                if name.endswith(("_pin", "_pull_up", "_bounce_time")):
                    continue

                parts = [p.strip() for p in str(line).split("|")]
                if len(parts) < 2:
                    continue

                try:
                    int(parts[1])
                except ValueError:
                    continue

                initial = len(parts) > 3 and parts[3].lower() == "true"
                relay = _MockRelay(initial)
                self.devices[name] = relay
                self.relays[name] = relay
                self.relay_initial_states[name] = initial
                logger.debug(f"📟 Demo relay: {name} (initial={'ON' if initial else 'OFF'})")

        if self.config.has_section("reeds"):
            reed_section = self.config.get_section("reeds")
            for name, line in reed_section.items():
                parts = [p.strip() for p in str(line).split("|")]
                if len(parts) < 2:
                    continue

                controls = [name]
                if len(parts) > 6:
                    last_field = parts[6].strip()
                    if last_field.startswith("controls:"):
                        light_list = last_field[9:].strip()
                        if light_list:
                            controls = [x.strip() for x in light_list.split(",") if x.strip()]
                    elif last_field:
                        controls = [last_field]

                closed = self.config.getboolean("demo", f"reed_{name}_closed", fallback=True)
                reed = _MockReed(closed)
                self.devices[name] = reed
                self.reeds[name] = reed
                self.reed_states[name] = closed
                self.reed_to_light_map[name] = controls
                logger.debug(f"🚪 Demo reed: {name} → {'closed' if closed else 'open'}")

        logger.info(
            f"🏭 Demo GPIO initialized → {len(self.relays)} relay(s), "
            f"{len(self.reeds)} reed(s) (simulated)"
        )

    def get_device(self, name: str):
        return self.devices.get(name)

    def get_relay(self, name: str):
        return self.relays.get(name)

    def set_reed_closed(self, name: str, closed: bool):
        reed = self.reeds.get(name)
        if reed is None:
            return
        reed.is_pressed = closed
        self.reed_states[name] = closed

    def cleanup(self):
        self.devices.clear()
        self.relays.clear()
        self.reeds.clear()
        self.reed_states.clear()
        self.relay_initial_states.clear()
        self.reed_to_light_map.clear()