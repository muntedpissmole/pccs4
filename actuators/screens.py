from __future__ import annotations

import logging
import re
import shlex
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Union

logger = logging.getLogger("pccs")

_SCREEN_KNOWN_HOSTS = Path.home() / ".pccs" / "screen_known_hosts"

OnCommandFailed = Optional[Callable[[str], None]]


@dataclass(frozen=True)
class SysfsControl:
    path: str


@dataclass(frozen=True)
class DbusScreenSaverControl:
    service: str
    object_path: str


@dataclass(frozen=True)
class DbusKdeBrightnessControl:
    service: str
    object_path: str
    interface: str = "org.kde.ScreenBrightness.Display"


ScreenControl = Union[SysfsControl, DbusScreenSaverControl, DbusKdeBrightnessControl]


def _ssh_options(timeout: int = 5) -> str:
    _SCREEN_KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
    return (
        f"-o BatchMode=yes -o ConnectTimeout={timeout} "
        f"-o StrictHostKeyChecking=accept-new "
        f"-o UserKnownHostsFile={_SCREEN_KNOWN_HOSTS} "
        f"-o PreferredAuthentications=publickey -o IdentitiesOnly=no"
    )


def _ssh_cmd(username: str, host: str, remote: str, timeout: int) -> str:
    return (
        f"ssh {_ssh_options(timeout)} "
        f"{shlex.quote(username)}@{shlex.quote(host)} {shlex.quote(remote)}"
    )


def _parse_control(path: str) -> Optional[ScreenControl]:
    if not path:
        return None
    if path.startswith("dbus:"):
        spec = path[5:]
        if ":" in spec:
            service, object_path = spec.split(":", 1)
        else:
            service = spec
            object_path = "/" + service.replace(".", "/")
        if not service or not object_path.startswith("/"):
            return None
        if service == "org.kde.ScreenBrightness":
            return DbusKdeBrightnessControl(service=service, object_path=object_path)
        return DbusScreenSaverControl(service=service, object_path=object_path)
    return SysfsControl(path=path)


def _is_blank_path(path: str) -> bool:
    return "blank" in path or "/graphics/fb" in path


def _blank_awake_value(awake: bool) -> str:
    return "0" if awake else "1"


def _blank_is_awake(value: int) -> bool:
    """fb0/blank: 0 = awake; 1 or 4 = blanked (see config/pccs.conf [screens] notes)."""
    return value == 0


def _dbus_env_prefix() -> str:
    return "export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus;"


def _dbus_set_active_cmd(control: DbusScreenSaverControl, awake: bool) -> str:
    active = "false" if awake else "true"
    return (
        f"{_dbus_env_prefix()} "
        f"busctl --user call {shlex.quote(control.service)} "
        f"{shlex.quote(control.object_path)} "
        f"org.freedesktop.ScreenSaver SetActive b {active}"
    )


def _dbus_get_active_cmd(control: DbusScreenSaverControl) -> str:
    return (
        f"{_dbus_env_prefix()} "
        f"busctl --user call {shlex.quote(control.service)} "
        f"{shlex.quote(control.object_path)} "
        f"org.freedesktop.ScreenSaver GetActive"
    )


def _dbus_kde_set_brightness_cmd(control: DbusKdeBrightnessControl, awake: bool) -> str:
    svc = shlex.quote(control.service)
    obj = shlex.quote(control.object_path)
    iface = shlex.quote(control.interface)
    if awake:
        return (
            f"{_dbus_env_prefix()} "
            f"max=$(busctl --user get-property {svc} {obj} {iface} MaxBrightness "
            f"| awk '{{print $2}}'); "
            f"busctl --user call {svc} {obj} {iface} SetBrightness iu "
            f"${{max:-10000}} 0"
        )
    return (
        f"{_dbus_env_prefix()} "
        f"busctl --user call {svc} {obj} {iface} SetBrightness iu 0 0"
    )


def _dbus_kde_get_brightness_cmd(control: DbusKdeBrightnessControl) -> str:
    return (
        f"{_dbus_env_prefix()} "
        f"busctl --user get-property {shlex.quote(control.service)} "
        f"{shlex.quote(control.object_path)} "
        f"{shlex.quote(control.interface)} Brightness"
    )


def _parse_busctl_bool(output: str) -> Optional[bool]:
    match = re.search(r"\bb\s+(true|false)\b", output or "", re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower() == "true"


def _parse_busctl_int(output: str) -> Optional[int]:
    match = re.search(r"\bi\s+(-?\d+)\b", output or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _remote_set_cmd(username: str, host: str, control: ScreenControl, awake: bool, timeout: int) -> str:
    if isinstance(control, DbusKdeBrightnessControl):
        remote = _dbus_kde_set_brightness_cmd(control, awake)
    elif isinstance(control, DbusScreenSaverControl):
        remote = _dbus_set_active_cmd(control, awake)
    else:
        path_q = shlex.quote(control.path)
        is_blank = _is_blank_path(control.path)
        value = _blank_awake_value(awake) if is_blank else ("255" if awake else "0")
        value_q = shlex.quote(value)
        remote = (
            f"if echo {value_q} > {path_q} 2>/dev/null; then exit 0; fi; "
            f"echo {value_q} | sudo -n tee {path_q} >/dev/null"
        )
    return _ssh_cmd(username, host, remote, timeout)


def _remote_read_cmd(username: str, host: str, control: ScreenControl, timeout: int) -> str:
    if isinstance(control, DbusKdeBrightnessControl):
        remote = _dbus_kde_get_brightness_cmd(control)
    elif isinstance(control, DbusScreenSaverControl):
        remote = _dbus_get_active_cmd(control)
    else:
        path_q = shlex.quote(control.path)
        remote = f"cat {path_q} 2>/dev/null"
    return _ssh_cmd(username, host, remote, timeout)


def _state_from_read(control: ScreenControl, raw_output: str) -> tuple[Optional[bool], Optional[int]]:
    if isinstance(control, DbusKdeBrightnessControl):
        brightness = _parse_busctl_int(raw_output)
        if brightness is None:
            return None, None
        return (brightness > 0, brightness)

    if isinstance(control, DbusScreenSaverControl):
        active = _parse_busctl_bool(raw_output)
        if active is None:
            return None, None
        return (not active, 1 if active else 0)

    try:
        val = int((raw_output or "").strip())
    except ValueError:
        return None, None
    is_blank = _is_blank_path(control.path)
    on = _blank_is_awake(val) if is_blank else (val > 0)
    return on, val


class ScreenActuator:
    def __init__(self, screens: dict, compiled, on_command_failed: OnCommandFailed = None):
        self._screens = screens
        self._observed: Dict[str, bool] = {n: False for n in screens}
        self._on_command_failed = on_command_failed
        if screens:
            threading.Thread(target=self._probe_all, daemon=True, name="screen-probe").start()

    def set_on_command_failed(self, callback: OnCommandFailed):
        self._on_command_failed = callback

    def set_screen(self, name: str, awake: bool):
        threading.Thread(target=self._apply, args=(name, awake), daemon=True).start()

    def _apply(self, name: str, awake: bool):
        conf = self._screens.get(name)
        if not conf:
            return
        control = _parse_control(conf.get("brightness_path", ""))
        if not control:
            return
        cmd = _remote_set_cmd(
            conf["username"],
            conf["host"],
            control,
            awake,
            timeout=8,
        )
        try:
            result = subprocess.run(cmd, shell=True, timeout=10, capture_output=True, text=True)
            if result.returncode == 0:
                self._observed[name] = awake
                logger.info(f"🖥️ {'Woke' if awake else 'Slept'} screen: {conf.get('friendly', name)}")
            else:
                err = (result.stderr or result.stdout or "").strip()
                logger.warning(
                    "Screen %s SSH failed (exit %s): %s",
                    name,
                    result.returncode,
                    err[:200] or "no output",
                )
                if self._on_command_failed:
                    self._on_command_failed(name)
        except Exception as e:
            logger.warning(f"Screen {name} SSH: {e}")
            if self._on_command_failed:
                self._on_command_failed(name)

    def _probe_all(self):
        for name in self._screens:
            try:
                self.test_connectivity(name)
            except Exception as e:
                logger.debug("Screen %s startup probe: %s", name, e)

    def read_screens(self) -> Dict[str, bool]:
        return dict(self._observed)

    def test_connectivity(self, name: str, timeout: float = 3.0) -> dict:
        """Ported for diag REST endpoints."""
        conf = self._screens.get(name)
        if not conf:
            return {"online": False, "error": "No config"}
        import socket
        from datetime import datetime

        result = {
            "online": False,
            "latency": None,
            "ssh_passwordless": False,
            "last_checked": datetime.now().isoformat(),
            "brightness": None,
            "on": None,
        }
        host = conf["host"]
        try:
            with socket.create_connection((host, 22), timeout=timeout):
                result["online"] = True
        except Exception:
            return result

        control = _parse_control(conf.get("brightness_path", ""))
        if not control:
            return result

        cmd = _remote_read_cmd(conf["username"], host, control, int(timeout))
        try:
            proc = subprocess.run(cmd, shell=True, timeout=timeout + 2, capture_output=True, text=True)
            if proc.returncode == 0:
                on, brightness = _state_from_read(control, proc.stdout or "")
                if on is not None:
                    result["on"] = on
                    result["brightness"] = brightness
                    result["ssh_passwordless"] = True
                    self._observed[name] = on
        except Exception as e:
            result["ssh_error"] = str(e)[:200]
        return result

    def manual_toggle(self, name: str, force_on: Optional[bool] = None):
        if force_on is None:
            force_on = not self._observed.get(name, False)
        self.set_screen(name, force_on)

    def shutdown_all(self):
        if not self._screens:
            return
        for name in self._screens:
            threading.Thread(target=self._shutdown_one, args=(name,), daemon=True).start()

    def _shutdown_one(self, name: str):
        conf = self._screens.get(name)
        if not conf:
            return
        label = conf.get("friendly", name)
        cmd = (
            f"ssh {_ssh_options(8)} "
            f"{conf['username']}@{conf['host']} "
            "\"sudo -n shutdown -h now 2>/dev/null || shutdown -h now 2>/dev/null || poweroff\""
        )
        try:
            result = subprocess.run(cmd, shell=True, timeout=12, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"🖥️ Shutdown sent to screen: {label}")
            else:
                err = (result.stderr or result.stdout or "").strip()
                logger.warning(
                    "Screen %s shutdown SSH failed (exit %s): %s",
                    name,
                    result.returncode,
                    err[:200] or "no output",
                )
        except Exception as e:
            logger.warning(f"Screen {name} shutdown SSH: {e}")