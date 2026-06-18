"""PCCS4 — Flask + SocketIO bridge for lighting/relay control."""

from __future__ import annotations

import atexit
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from bridge.runtime import PCCSRuntime
from gps import get_gps_status, set_gps_module
from modules.config import config
from modules.logger import setup_logging
from modules.phases import PhaseManager
from modules.toasts import ToastManager
from modules.ui_state import ConfigManager

import modules.toasts
from network import build_network_status
from sonos import get_sonos_status, set_muted, set_sonos_manager, set_transport, set_volume
from system import get_system_status, set_gps_module as set_system_gps, set_runtime, set_victron_module
from victron import get_power_status, set_victron_manager as set_power_victron
from weather import get_weather_status, set_gps_module as set_weather_gps
from wifi import connect_wifi, get_wifi_status, scan_wifi_networks

logger = setup_logging(config)

if config.getboolean("logging", "suppress_werkzeug", fallback=True):
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
if config.getboolean("logging", "suppress_engineio", fallback=True):
    logging.getLogger("engineio").setLevel(logging.WARNING)
if config.getboolean("logging", "suppress_socketio", fallback=True):
    logging.getLogger("socketio").setLevel(logging.WARNING)


def log_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = log_exception


def _patch_engineio_werkzeug_websocket() -> None:
    """Engine.IO hijacks the socket for WebSocket upgrades without calling WSGI start_response.

    Werkzeug then raises AssertionError: write() before start_response when the
    handler returns. Signal a dropped connection instead (same idea as gunicorn's
    StopIteration path in engineio's SimpleWebSocketWSGI).
    """
    from engineio.async_drivers import _websocket_wsgi as wswsgi

    if getattr(wswsgi.SimpleWebSocketWSGI, "_pccs4_werkzeug_patch", False):
        return

    _orig_call = wswsgi.SimpleWebSocketWSGI.__call__

    def __call__(self, environ, start_response):
        ret = _orig_call(self, environ, start_response)
        if getattr(getattr(self, "ws", None), "mode", None) == "werkzeug":
            raise ConnectionError("WebSocket connection handled outside WSGI")
        return ret

    wswsgi.SimpleWebSocketWSGI.__call__ = __call__
    wswsgi.SimpleWebSocketWSGI._pccs4_werkzeug_patch = True


_patch_engineio_werkzeug_websocket()

app = Flask(__name__)
app.config["SECRET_KEY"] = config.get("system", "secret_key", fallback="pccs4-secret")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

debug_mode = config.getboolean("system", "debug", fallback=False)
if debug_mode:
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

toast_manager = ToastManager(config, socketio)
modules.toasts.toast_manager = toast_manager

dark_mode_config = ConfigManager("active_dark_mode.json", {"mode": "dark", "manual": False})
_default_theme = config.get("ui", "default_theme", fallback="neuglass")
if _default_theme == "base":
    _default_theme = "neuglass"
theme_config = ConfigManager("active_theme.json", {"theme": _default_theme})
current_global_theme = theme_config.load()["theme"]

runtime = PCCSRuntime(config, socketio=socketio, dark_mode_config=dark_mode_config)
set_runtime(runtime)

gps_module = None
phase_manager = None
sensor_manager = None
victron_module = None
sonos_module = None
first_state_read_done = False
shutdown_event = threading.Event()
_cleanup_done = False
_demo_reed_scheduler = None


def _is_demo_mode() -> bool:
    return config.getboolean("demo", "enabled", fallback=False)


def _theme_sort_key(item: dict) -> tuple:
    name = item["name"].lower()
    return (0 if name.endswith("morphism") else 1, name)


def _extract_css_friendly_name(filepath: str, fallback: str) -> str:
    try:
        with open(filepath, encoding="utf-8") as handle:
            first = handle.readline().strip()
            if first.startswith("/*") and first.endswith("*/"):
                comment = first[2:-2].strip()
                if comment:
                    return comment
    except OSError:
        pass
    return fallback


def _network_status_payload() -> dict:
    start_time = getattr(app, "_start_time", None)
    return build_network_status(start_time)


def network_status_broadcaster() -> None:
    while not shutdown_event.is_set():
        try:
            socketio.emit("network_update", _network_status_payload())
        except Exception:
            pass
        if shutdown_event.wait(8.5):
            break

NAV_ITEMS = [
    {"id": "home", "label": "Home", "icon": "fa-house"},
    {"id": "lighting", "label": "Lighting", "icon": "fa-lightbulb"},
    {"id": "scenes", "label": "Scenes", "icon": "fa-wand-magic-sparkles"},
    {"id": "system", "label": "System", "icon": "fa-gear"},
]


@app.context_processor
def inject_nav():
    return {"nav_items": NAV_ITEMS}


@app.route("/")
def index():
    return render_template("index.html", active_page="home")


@app.route("/api/power")
def api_power():
    return jsonify(get_power_status())


@app.route("/api/victron")
def api_victron():
    if victron_module:
        return jsonify(victron_module.get_state())
    return jsonify({"stale": True, "shunt": {"configured": False}, "mppt": {"configured": False}})


@app.route("/api/gps")
def api_gps():
    return jsonify(get_gps_status())


@app.route("/api/system")
def api_system():
    return jsonify(get_system_status())


@app.route("/api/weather")
def api_weather():
    return jsonify(get_weather_status())


@app.route("/api/network")
def api_network():
    return jsonify(_network_status_payload())


@app.route("/api/themes")
def api_get_themes():
    themes, seen = [], set()
    themes_dir = os.path.join(app.static_folder, "css", "themes")
    if os.path.isdir(themes_dir):
        for filename in sorted(os.listdir(themes_dir)):
            if not filename.endswith(".css"):
                continue
            base = filename[:-4]
            if base in seen:
                continue
            seen.add(base)
            path = os.path.join(themes_dir, filename)
            fallback = base.replace("-", " ").replace("_", " ").title()
            themes.append({"file": base, "name": _extract_css_friendly_name(path, fallback)})
    themes.sort(key=_theme_sort_key)
    return jsonify({"themes": themes})


@app.route("/api/current-theme")
def api_get_current_theme():
    return jsonify({"theme": current_global_theme})


@app.route("/api/sonos")
def api_sonos():
    return jsonify(get_sonos_status())


@app.route("/api/sonos/transport", methods=["POST"])
def api_sonos_transport():
    payload = request.get_json(silent=True) or {}
    return jsonify(set_transport(str(payload.get("action", ""))))


@app.route("/api/sonos/volume", methods=["POST"])
def api_sonos_volume():
    payload = request.get_json(silent=True) or {}
    try:
        level = int(payload.get("level", 0))
    except (TypeError, ValueError):
        level = 0
    return jsonify(set_volume(level))


@app.route("/api/sonos/mute", methods=["POST"])
def api_sonos_mute():
    payload = request.get_json(silent=True) or {}
    return jsonify(set_muted(bool(payload.get("muted"))))


@app.route("/sonos-art")
def proxy_sonos_album_art():
    art_url = request.args.get("url")
    if not art_url:
        return "Missing url", 400
    try:
        import requests

        parsed = urlparse(art_url)
        if parsed.port != 1400:
            return "Invalid", 403
        resp = requests.get(art_url, timeout=10, stream=True)
        if resp.status_code != 200:
            return "Failed", resp.status_code
        return Response(
            resp.iter_content(8192),
            content_type=resp.headers.get("content-type", "image/jpeg"),
            headers={"Cache-Control": "public, max-age=7200"},
        )
    except Exception as e:
        logger.warning(f"Sonos art proxy: {e}")
        return "Error", 502


@app.route("/api/wifi")
def api_wifi():
    return jsonify(get_wifi_status())


@app.route("/api/wifi/scan", methods=["POST"])
def api_wifi_scan():
    return jsonify(scan_wifi_networks())


@app.route("/api/wifi/connect", methods=["POST"])
def api_wifi_connect():
    payload = request.get_json(silent=True) or {}
    password = payload.get("password")
    if password is not None:
        password = str(password)
    return jsonify(connect_wifi(str(payload.get("ssid", "")), password))


def _apply_light_change(data, *, source: str = "socket"):
    if not data or "name" not in data:
        logger.warning(f"light_change ignored ({source}) — bad payload: {data!r}")
        return None
    name = data["name"]
    if name not in runtime.compiled.light_names:
        logger.warning(f"light_change ignored ({source}) — unknown light: {name}")
        return None
    try:
        target = max(0, min(100, int(data.get("brightness", 0))))
    except (TypeError, ValueError):
        logger.warning(f"light_change ignored ({source}) — invalid brightness: {data.get('brightness')!r}")
        return None
    mode = data.get("mode", "white") if name in runtime.compiled.rgb_lights else None
    runtime.set_light_intent(name, target, mode)
    return runtime.get_ui_state()


@app.route("/api/light", methods=["POST"])
def api_light_change():
    state = _apply_light_change(request.get_json(silent=True) or {}, source="http")
    if state is None:
        return jsonify({"ok": False}), 400
    return jsonify({"ok": True, "state": state})


@app.route("/api/relay", methods=["POST"])
def api_relay_change():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if name not in runtime.compiled.relay_names:
        logger.warning(f"relay_change ignored (http) — unknown relay: {name}")
        return jsonify({"ok": False}), 400
    runtime.set_relay_intent(name, bool(data.get("on", False)))
    return jsonify({"ok": True})


@app.route("/api/explain")
def api_explain():
    return jsonify(runtime.get_explain_json())


@app.route("/api/scenes")
def api_get_scenes():
    scenes = dict(
        sorted(runtime.compiled.scenes.items(), key=lambda item: item[1].get("order", 999))
    )
    return jsonify({
        "scenes": [
            {
                "key": k,
                "name": d["name"],
                "icon": d["icon"],
                "description": d["description"],
                "all_off": d["all_off"],
            }
            for k, d in scenes.items()
        ]
    })


@app.route("/api/scene", methods=["POST"])
def api_set_scene():
    data = request.get_json(silent=True) or {}
    scene = data.get("scene")
    if not scene or scene not in runtime.compiled.scenes:
        return jsonify({"ok": False}), 400
    runtime.set_scene(scene)
    return jsonify({
        "ok": True,
        "state": runtime.get_ui_state(),
        "ramp_ms": runtime.compiled.scene_ramp_ms,
    })


@app.route("/api/lights")
def api_get_lights():
    return jsonify({
        "lights": runtime.get_frontend_config(),
        "state": runtime.get_ui_state(),
    })


@app.route("/api/reeds/force", methods=["POST"])
def api_force_reed():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if name is None:
        return jsonify({"ok": False, "error": "name required"}), 400
    state = runtime.force_reed(name, data.get("closed"))
    return jsonify({
        "ok": True,
        "state": state,
        "ramp_ms": state.get("_ramp_ms") or runtime.compiled.reed_ramp_ms,
        "reeds": runtime.get_reed_diag_json(),
        "effective": runtime.effective_reed_states(),
    })


@app.route("/api/reeds")
def api_get_reeds():
    diag = runtime.get_reed_diag_json()
    return jsonify({
        "reeds": runtime.get_reeds_frontend_config(),
        "states": runtime.effective_reed_states(),
        "raw": diag.get("states", {}),
        "forced": diag.get("forced", {}),
    })


def _screen_frontend_item(name: str, conf: dict, conn: dict | None = None) -> dict:
    """Build one screen record for the system tile."""
    observed_pct = 0
    if runtime.screen_actuator:
        observed_pct = runtime.screen_actuator._observed.get(name, 0)

    item = {
        "name": name,
        "label": conf.get("friendly", name),
        "icon": conf.get("icon", "fa-display"),
        "online": False,
        "latency": None,
        "on": observed_pct > 0,
        "brightness": None,
        "brightness_pct": observed_pct if observed_pct > 0 else None,
        "ssh_passwordless": False,
        "ssh_error": None,
    }
    if conn:
        if conn.get("on") is not None:
            item["on"] = conn["on"]
        item["online"] = conn.get("online", False)
        item["brightness"] = conn.get("brightness")
        if conn.get("brightness_pct") is not None:
            item["brightness_pct"] = conn["brightness_pct"]
        item["ssh_passwordless"] = conn.get("ssh_passwordless", False)
        item["ssh_error"] = conn.get("ssh_error")
    return item


def _screens_list(*, probe: bool = False) -> list:
    if not runtime.screen_actuator:
        return []
    screens = []
    for name, conf in runtime.compiled.screens.items():
        conn = None
        if probe:
            conn = runtime.screen_actuator.test_connectivity(name)
        screens.append(_screen_frontend_item(name, conf, conn))
    return screens


@app.route("/api/screens")
def api_get_screens():
    return jsonify({"screens": _screens_list()})


@app.route("/api/screens/status")
def api_get_screens_status():
    return jsonify({"screens": _screens_list(probe=True)})


def _cleanup_best_effort(timeout_s: float = 10) -> None:
    """Run cleanup without blocking shutdown if hardware teardown hangs."""
    try:
        worker = threading.Thread(target=cleanup, daemon=True, name="shutdown-cleanup")
        worker.start()
        worker.join(timeout=timeout_s)
        if worker.is_alive():
            logger.warning("Shutdown cleanup did not finish within %.0fs", timeout_s)
    except Exception as e:
        logger.error(f"Shutdown cleanup error: {e}")


def _issue_host_shutdown() -> bool:
    """Schedule host power-off. Never call this in tests without mocking."""
    try:
        subprocess.Popen(
            ["sudo", "-n", "shutdown", "-h", "now"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.warning("Host shutdown command issued")
        return True
    except Exception as e:
        logger.error(f"Host shutdown failed: {e}")
        return False


@app.route("/api/system/shutdown", methods=["POST"])
def api_system_shutdown():
    """Shut down remote touchscreens, then this Pi."""
    logger.warning("System shutdown requested via API")

    if runtime.screen_actuator:
        runtime.screen_actuator.shutdown_all()

    def _shutdown_host():
        import time

        # Issue host shutdown before cleanup — GPIO factory.close() can hang
        # indefinitely and previously prevented shutdown from ever running.
        if not _issue_host_shutdown():
            return

        time.sleep(2)
        _cleanup_best_effort()

    threading.Thread(target=_shutdown_host, daemon=True, name="shutdown-host").start()
    return jsonify({"ok": True, "message": "Shutting down…"})


@app.route("/api/phases")
def api_get_phases():
    if not phase_manager:
        return jsonify({"phase": None, "forced": False, "times": {}})
    times = {}
    try:
        times = phase_manager.get_phase_times()
    except Exception:
        pass
    return jsonify({
        "phase": phase_manager.get_phase(),
        "forced": phase_manager.is_forced(),
        "times": times,
    })


@app.route("/api/sensors")
def api_get_sensors():
    if not sensor_manager:
        return jsonify({"source": "unavailable"})
    reading = getattr(sensor_manager, "last_reading", None) or {}
    payload = dict(reading)
    payload["source"] = "live" if reading else "waiting"
    return jsonify(payload)


@app.route("/api/dark-mode")
def api_get_dark_mode():
    if not phase_manager:
        return jsonify({"mode": "dark", "manual": False})
    return jsonify({
        "mode": phase_manager.get_current_dark_mode(),
        "manual": phase_manager.manual_dark_mode is not None,
    })


@socketio.on("light_change")
def handle_light_change(data):
    state = _apply_light_change(data, source="socket")
    if state is not None:
        emit("state_update", state)


@socketio.on("relay_change")
def handle_relay_change(data):
    name = data.get("name")
    if name not in runtime.compiled.relay_names:
        logger.warning(f"relay_change ignored — unknown relay: {name}")
        return
    runtime.set_relay_intent(name, bool(data.get("on", False)))


@socketio.on("get_reeds")
def handle_get_reeds():
    emit("reed_update", {"states": runtime.effective_reed_states()})


@socketio.on("force_reed")
def handle_force_reed(data):
    name = data.get("name")
    if name is None:
        return
    runtime.force_reed(name, data.get("closed"))


@socketio.on("set_scene")
def handle_set_scene(data):
    scene = data.get("scene")
    if not scene or scene not in runtime.compiled.scenes:
        return
    runtime.set_scene(scene)
    emit("state_update", runtime.get_ui_state(), broadcast=True)


@socketio.on("force_phase")
def handle_force_phase(data):
    runtime.force_phase(data.get("phase"))


@socketio.on("get_reeds_diag")
def handle_get_reeds_diag():
    emit("reed_diag_update", runtime.get_reed_diag_json())


@socketio.on("set_gps_simulation")
def handle_gps_simulation(data):
    if not gps_module:
        return
    payload = data or {}
    if "no_hardware" in payload and hasattr(gps_module, "set_no_hardware_simulation"):
        gps_module.set_no_hardware_simulation(bool(payload.get("no_hardware")))
    if "no_fix" in payload and hasattr(gps_module, "set_no_fix_simulation"):
        gps_module.set_no_fix_simulation(bool(payload.get("no_fix")))


@socketio.on("screen_manual_toggle")
def handle_screen_manual_toggle(data):
    if not runtime.screen_actuator:
        return
    name = data.get("name")
    if not name:
        return

    brightness = data.get("brightness_pct")
    if brightness is not None:
        try:
            brightness = max(0, min(100, int(brightness)))
        except (TypeError, ValueError):
            return
        runtime.screen_actuator.manual_toggle(name, brightness_pct=brightness)
        runtime._emit_screens_observed([name])
        return

    on = data.get("on")
    if on:
        from engine.precedence import resolve_screen

        screen = runtime.compiled.screens.get(name)
        if screen:
            brightness = resolve_screen(screen, runtime.world.snapshot(), runtime.compiled)
            runtime.screen_actuator.manual_toggle(name, brightness_pct=brightness)
            runtime._emit_screens_observed([name])
        return
    runtime.screen_actuator.manual_toggle(name, force_on=on)
    runtime._emit_screens_observed([name])


@socketio.on("set_global_dark_mode")
def handle_set_global_dark_mode(data):
    mode = data.get("mode")
    if mode not in ("dark", "light"):
        return
    if phase_manager:
        phase_manager.set_manual_dark_mode(mode)
    emit("global_dark_mode_update", {"mode": mode, "manual": True}, broadcast=True)


@socketio.on("set_global_theme")
def handle_set_global_theme(data):
    global current_global_theme
    theme = data.get("theme")
    if not theme:
        return
    current_global_theme = theme
    theme_config.save({"theme": theme})
    emit("global_theme_update", {"theme": theme}, broadcast=True)


@socketio.on("get_network_status")
def handle_get_network_status():
    emit("network_update", _network_status_payload())


@socketio.on("sonos_command")
def handle_sonos_command(data):
    if not sonos_module:
        return
    result = sonos_module.execute_command(data or {})
    if isinstance(result, dict) and result.get("error"):
        emit("toast", {"type": "error", "message": f"Sonos: {result['error']}"})


@socketio.on("sonos_switch_speaker")
def handle_sonos_switch_speaker(data):
    if sonos_module and sonos_module.switch_speaker(data.get("name")):
        emit("sonos_update", sonos_module.get_current_state(), broadcast=True)
        emit("sonos_speakers", {
            "speakers": list(sonos_module.speakers.keys()),
            "current": sonos_module.current_speaker,
            "enabled": sonos_module.enabled,
        }, broadcast=True)


@socketio.on("sonos_request_state")
def handle_sonos_request_state():
    if sonos_module and sonos_module.enabled:
        sonos_module.request_state()
    else:
        emit("sonos_update", {"enabled": False})


@socketio.on("get_victron_state")
def handle_get_victron_state():
    if victron_module:
        emit("victron_update", victron_module.get_state())
    else:
        emit("victron_update", {"stale": True})


@socketio.on("toast_test")
def handle_toast_test(data):
    if toast_manager:
        toast_manager.send_toast(
            title=data.get("title"),
            message=data.get("message", "Test"),
            toast_type=data.get("type", "info"),
            duration=data.get("duration", 4500),
            persistent=data.get("persistent", False),
        )


@socketio.on("connect")
def handle_connect():
    global first_state_read_done
    emit("lights_config", runtime.get_frontend_config())
    emit("reeds_config", runtime.get_reeds_frontend_config())

    if not first_state_read_done:
        runtime.reconciler.read_hardware()
        first_state_read_done = True
    emit("state_update", runtime.get_ui_state())

    if phase_manager:
        phase_data = {"phase": phase_manager.get_phase()}
        try:
            phase_data.update(phase_manager.get_phase_times())
        except Exception:
            pass
        emit("phase_update", phase_data)
        emit("phase_diag_update", {"forced": phase_manager.is_forced()})
        emit("global_dark_mode_update", {
            "mode": phase_manager.get_current_dark_mode(),
            "manual": phase_manager.manual_dark_mode is not None,
        })

    if runtime.screen_actuator:
        emit("screens_init", {"screens": _screens_list()})

    if victron_module:
        emit("victron_update", victron_module.get_state())

    emit("global_theme_update", {"theme": current_global_theme})
    emit("network_update", _network_status_payload())

    if sonos_module and sonos_module.enabled:
        try:
            emit("sonos_update", sonos_module.get_current_state())
            emit("sonos_speakers", {
                "speakers": list(sonos_module.speakers.keys()),
                "current": sonos_module.current_speaker,
                "enabled": True,
            })
        except Exception as e:
            logger.debug(f"Sonos connect emit: {e}")
    else:
        emit("sonos_update", {"enabled": False})

    emit("reed_update", {"states": runtime.effective_reed_states()})
    emit("reed_diag_update", runtime.get_reed_diag_json())

    if gps_module:
        emit("gps_update", gps_module.get_state())

    if sensor_manager:
        try:
            sensor_manager.update_sensors()
        except Exception as e:
            logger.debug(f"Initial sensor read failed: {e}")


def cleanup():
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True

    logger.info("Cleaning up runtime...")
    shutdown_event.set()

    if phase_manager:
        try:
            phase_manager.stop()
        except Exception as e:
            logger.debug(f"Phase manager stop: {e}")

    if sensor_manager:
        try:
            sensor_manager.stop()
        except Exception as e:
            logger.debug(f"Sensor manager stop: {e}")

    if gps_module:
        try:
            gps_module.cleanup()
        except Exception as e:
            logger.debug(f"GPS cleanup: {e}")

    if victron_module:
        try:
            victron_module.stop()
        except Exception as e:
            logger.debug(f"Victron stop: {e}")

    if sonos_module:
        try:
            sonos_module.stop()
        except Exception as e:
            logger.debug(f"Sonos stop: {e}")

    global _demo_reed_scheduler
    if _demo_reed_scheduler:
        try:
            _demo_reed_scheduler.stop()
        except Exception as e:
            logger.debug(f"Demo reed scheduler stop: {e}")
        _demo_reed_scheduler = None

    try:
        runtime.stop()
    except Exception as e:
        logger.error(f"Runtime cleanup error: {e}")


def _startup():
    global gps_module, phase_manager, sensor_manager, victron_module, sonos_module, _demo_reed_scheduler

    demo = _is_demo_mode()
    logger.info("Starting PCCS4 %s backend...", "demo" if demo else "lighting")
    from modules.clock import ensure_clock_for_automation, log_clock_status

    log_clock_status(logger)
    app._start_time = datetime.now()

    runtime.start_hardware()

    if demo:
        from demo.mock_gps import DemoGPSModule
        from demo.mock_sensors import DemoSensorManager
        from demo.reed_scheduler import DemoReedScheduler

        gps_module = DemoGPSModule(config, socketio)
        sensor_manager = DemoSensorManager(config, runtime.arduino.send_command, socketio)
    else:
        from modules.gps import GPSModule
        from modules.sensors import SensorManager

        gps_module = GPSModule(config, socketio)
        sensor_manager = SensorManager(config, runtime.arduino.send_command, socketio)

    set_gps_module(gps_module)
    set_weather_gps(gps_module)
    set_system_gps(gps_module)
    phase_manager = PhaseManager(config, gps_module, socketio, dark_mode_config)
    phase_manager.on_phase_change = lambda p, f, inv: runtime.on_phase_change(p, f, inv)
    runtime.phase_manager = phase_manager
    runtime.gps = gps_module

    gps_module.init_gps()
    gps_module.init_geolocator()

    if not demo:
        ensure_clock_for_automation(logger, config)

    runtime.bootstrap_phase()
    runtime.finish_startup()
    phase_manager.start()
    sensor_manager.start()

    runtime.start_background_threads()

    if demo:
        gps_module.start_reader()
        from demo.mock_victron import DemoVictronManager
        from demo.mock_sonos import DemoSonosManager

        try:
            victron_module = DemoVictronManager(socketio, config, phase_manager=phase_manager)
            victron_module.start()
            set_victron_module(victron_module)
            set_power_victron(victron_module)
            phase_manager.register_night_listener(victron_module.reset_daily_generation)
        except Exception as e:
            logger.error(f"Demo Victron init failed: {e}")
            victron_module = None

        try:
            sonos_module = DemoSonosManager(socketio, config)
            sonos_module.start()
            set_sonos_manager(sonos_module)
        except Exception as e:
            logger.error(f"Demo Sonos init failed: {e}")
            sonos_module = None

        _demo_reed_scheduler = DemoReedScheduler(runtime.gpio, config)
        _demo_reed_scheduler.start()
    else:
        if getattr(gps_module, "serial", None):
            gps_module.start_reader()

        try:
            from modules.victron import VictronManager

            victron_module = VictronManager(socketio, config, phase_manager=phase_manager)
            victron_module.start()
            set_victron_module(victron_module)
            set_power_victron(victron_module)
            phase_manager.register_night_listener(victron_module.reset_daily_generation)
        except Exception as e:
            logger.error(f"Victron init failed: {e}")
            victron_module = None

        try:
            from modules.sonos import SonosManager

            sonos_module = SonosManager(socketio, config)
            sonos_module.start()
            set_sonos_manager(sonos_module)
        except Exception as e:
            logger.error(f"Sonos init failed: {e}")
            sonos_module = None

    threading.Thread(target=network_status_broadcaster, daemon=True).start()

    logger.info("PCCS4 %s backend ready", "demo" if demo else "lighting")


if __name__ == "__main__":
    atexit.register(cleanup)
    try:
        _startup()
        host = config.get("system", "host", fallback="0.0.0.0")
        port = config.getint("system", "port", fallback=5000)
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug_mode,
            use_reloader=False,
            allow_unsafe_werkzeug=True,
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested")
    finally:
        cleanup()