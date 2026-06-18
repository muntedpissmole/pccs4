"""In-memory Arduino simulation — lights ramp and state reads work without serial."""

from __future__ import annotations

import logging
import re
import threading
import time

from demo.water_scheduler import current_water_level_pct
from modules.arduino import ArduinoManager, brightness_to_pwm, pwm_to_brightness

logger = logging.getLogger("pccs")

_RAMP_RE = re.compile(r"^RAMP\s+(\d+)\s+(\d+)\s+(\d+)$")
_GET_RE = re.compile(r"^GET\s+(\d+)$")
_ANALOG_RE = re.compile(r"^ANALOG\s+(\d+)$")


class DemoArduinoManager(ArduinoManager):
    """ArduinoManager that never opens serial; commands update simulated PWM state."""

    def __init__(self, config):
        super().__init__(config)
        self._pin_pwm: dict[int, int] = {}
        self._lock = threading.Lock()

    def init_serial(self) -> bool:
        logger.info("📟 Demo Arduino — simulated (no serial hardware)")
        return True

    def is_connected(self) -> bool:
        return True

    def cleanup(self):
        return

    def _pin_for_light(self, name: str) -> int | None:
        if name in self.LIGHT_MAP:
            return self.LIGHT_MAP[name]
        pins = self.RGB_BUG_LIGHTS.get(name)
        if not pins:
            return None
        mode = self.state.get(f"{name}_mode", "white")
        if mode == "red":
            return pins["red"]
        return pins["white"]

    def send_command(self, cmd: str, expect: str | None = None) -> str | None:
        cmd = (cmd or "").strip()
        if not cmd:
            return None

        with self._lock:
            if cmd == "GETVCC":
                return "VCC 5.000"

            analog = _ANALOG_RE.match(cmd)
            if analog:
                pin = int(analog.group(1))
                if pin == self.config.getint("arduino analog", "water_pin", fallback=1):
                    raw = int(current_water_level_pct() * 10.23)
                    return f"ANALOG {pin} {raw}"
                return f"ANALOG {pin} 0"

            ramp = _RAMP_RE.match(cmd)
            if ramp:
                pin, pwm, _ms = map(int, ramp.groups())
                self._pin_pwm[pin] = max(0, min(255, pwm))
                self._sync_light_state_from_pins()
                return None

            get = _GET_RE.match(cmd)
            if get and expect == "VALUE":
                pin = int(get.group(1))
                pwm = self._pin_pwm.get(pin, 0)
                return f"VALUE {pin} {pwm}"

        return None

    def _sync_light_state_from_pins(self):
        for name, pin in self.LIGHT_MAP.items():
            self.state[name] = pwm_to_brightness(self._pin_pwm.get(pin, 0))

        for name, pins in self.RGB_BUG_LIGHTS.items():
            red_pwm = self._pin_pwm.get(pins["red"], 0)
            white_pwm = self._pin_pwm.get(pins["white"], 0)
            if red_pwm > white_pwm:
                self.state[name] = pwm_to_brightness(red_pwm)
                self.state[f"{name}_mode"] = "red"
            else:
                self.state[name] = pwm_to_brightness(white_pwm)
                self.state[f"{name}_mode"] = "white"

    def read_all_states(self):
        with self._lock:
            self._sync_light_state_from_pins()

    def set_rgb_bug_light(self, name: str, brightness: int, mode: str = "white", ramp_ms: int | None = None) -> bool:
        config = self.RGB_BUG_LIGHTS.get(name)
        if not config:
            return False

        pwm = brightness_to_pwm(brightness)
        if mode == "red":
            self._pin_pwm[config["red"]] = pwm
            self._pin_pwm[config["green"]] = int(pwm * 0.05)
            self._pin_pwm[config["white"]] = 0
        else:
            self._pin_pwm[config["red"]] = 0
            self._pin_pwm[config["green"]] = 0
            self._pin_pwm[config["white"]] = pwm

        self.state[name] = brightness
        self.state[f"{name}_mode"] = mode
        self.OPTIMISTIC_LOCK[name] = time.time() + self.OPTIMISTIC_LOCK_DURATION
        return True