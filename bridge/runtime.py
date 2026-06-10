from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from actuators.arduino import ArduinoActuator
from actuators.relays import RelayActuator
from actuators.screens import ScreenActuator
from engine.config_compile import compile_config
from engine.policy import desired_outputs
from engine.reconcile import ANIMATED_RAMP_SOURCES, Reconciler
from engine.world import WorldStore
from inputs.reeds import ReedInput
from modules.arduino import ArduinoManager
from modules.gpio import GPIODeviceManager

logger = logging.getLogger("pccs")


class PCCSRuntime:
    """Central runtime: world store, policy reconcile, inputs."""

    def __init__(self, config, socketio=None, dark_mode_config=None):
        self.config = config
        self.socketio = socketio
        self.compiled = compile_config(config)
        self.dark_mode_config = dark_mode_config

        self.arduino = ArduinoManager(config)
        self.gpio = GPIODeviceManager(config)

        self.world = WorldStore(
            self.compiled.reed_names,
            self.compiled.light_names,
            self.compiled.relay_names,
        )
        self.world.set_light_to_reed_map(self.compiled.light_to_reed)

        self.arduino_actuator = ArduinoActuator(self.arduino, self.compiled)
        self.relay_actuator = RelayActuator(self.gpio, self.compiled.relay_names)
        self.screen_actuator = ScreenActuator(self.compiled.screens, self.compiled) if self.compiled.screens else None

        self.reconciler = Reconciler(
            world=self.world,
            cfg=self.compiled,
            arduino_actuator=self.arduino_actuator,
            relay_actuator=self.relay_actuator,
            screen_actuator=self.screen_actuator,
            on_state_emit=self._emit_state,
            ramp_ms_for_source=self._ramp_ms_for_source,
            on_drift=self._on_hardware_drift,
        )

        self.reed_input: Optional[ReedInput] = None
        self.phase_manager = None
        self.gps = None
        self.sensor_manager = None
        self._shutdown = threading.Event()
        self._reconcile_lock = threading.Lock()

    def _ramp_ms_for_source(self, source: str) -> int:
        return {
            "ui": self.compiled.ui_ramp_ms,
            "scene": self.compiled.scene_ramp_ms,
            "phase": self.compiled.phase_ramp_ms,
            "reed": self.compiled.reed_ramp_ms,
        }.get(source, self.compiled.reed_ramp_ms)

    def reconcile(self, ramp_source: str = "auto"):
        with self._reconcile_lock:
            self.reconciler.reconcile(ramp_source=ramp_source)
        if ramp_source in ANIMATED_RAMP_SOURCES:
            self._schedule_post_ramp_read(self._ramp_ms_for_source(ramp_source))

    def _reconcile_async(self, ramp_source: str = "auto"):
        def _run():
            try:
                self.reconcile(ramp_source=ramp_source)
            except Exception as e:
                logger.warning(f"Async reconcile ({ramp_source}): {e}")

        threading.Thread(
            target=_run,
            daemon=True,
            name=f"Reconcile-{ramp_source}",
        ).start()

    def broadcast_ui_state(self):
        """Push lighting slider state to every connected browser."""
        self._emit_state(self.get_ui_state())

    def _emit_state(self, state: dict):
        if not self.socketio:
            return
        try:
            self.socketio.emit("state_update", state, namespace="/")
        except Exception as e:
            logger.warning(f"state_update broadcast failed: {e}")

    def _schedule_post_ramp_read(self, ramp_ms: int):
        """Re-read hardware after a ramp so observed state catches up before drift checks."""
        delay_s = (
            ramp_ms / 1000.0
            + self.compiled.optimistic_lock_duration_s
            + 0.5
        )

        def _work():
            if self._shutdown.wait(delay_s):
                return
            try:
                if self.arduino.is_connected():
                    self.reconciler.read_hardware()
            except Exception as e:
                logger.debug(f"Post-ramp hardware read: {e}")

        threading.Thread(target=_work, daemon=True, name="PostRampRead").start()

    def _on_hardware_drift(self, drifts: list):
        from modules.toasts import toast_manager
        if not drifts:
            return
        if toast_manager:
            if len(drifts) == 1:
                d = drifts[0]
                key = d.get("light") or d.get("relay") or "output"
                toast_manager.warning(
                    d.get("detail", "hardware mismatch"),
                    title=f"Drift: {key}",
                    duration=8000,
                )
            else:
                toast_manager.warning(
                    f"{len(drifts)} outputs differ from desired state",
                    title="Hardware drift",
                    duration=8000,
                )
        self.broadcast_ui_state()

    def get_explain_json(self) -> dict:
        return self.reconciler.explain_snapshot()

    def effective_reed_states(self) -> dict:
        """Authoritative reed map for the main UI (forces override hardware)."""
        snap = self.world.snapshot()
        effective = dict(snap.reeds)
        for name, closed in snap.reed_forces.items():
            effective[name] = closed
        return effective

    def _emit_reeds(self):
        if not self.socketio:
            return
        self.socketio.emit("reed_update", {"states": self.effective_reed_states()})
        self.socketio.emit("reed_diag_update", self.get_reed_diag_json())

    def on_reeds_updated(self, reeds: dict, transitioned_reeds: list):
        self.world.update_reeds(reeds, transition_reeds=transitioned_reeds)
        for reed in transitioned_reeds or []:
            self.reconciler.invalidate_commanded_for_reed(reed)
        self._emit_state(self._preview_ui_state("reed"))
        self._emit_reeds()
        self._reconcile_async("reed")

    def on_phase_change(self, phase: str, forced: Optional[str], invalidate: bool):
        self.world.set_phase(phase, forced, invalidate=invalidate)
        self.reconcile(ramp_source="phase")
        self.broadcast_ui_state()

    def set_light_intent(self, name: str, brightness: int, mode: Optional[str] = None):
        self.world.set_light_intent(name, brightness, mode, expires="until_reed_close")
        self.reconcile(ramp_source="ui")

    def set_relay_intent(self, name: str, on: bool):
        self.world.set_relay_intent(name, on)
        self.reconcile(ramp_source="ui")

    def set_scene(self, scene_key: str):
        scene = self.compiled.scenes.get(scene_key, {})
        if not scene:
            logger.warning(f"Unknown scene: {scene_key}")
            return

        # One-shot: command scene levels via a transient active_scene, then release.
        # No intents are stored — reeds, automation, and manual UI take over afterward.
        self.world.clear_all_light_intents()
        self.world.set_active_scene(scene_key)
        try:
            self.reconcile(ramp_source="scene")
        finally:
            self.world.clear_active_scene()

        from modules.toasts import toast_manager
        if toast_manager and scene.get("name"):
            title = "All Off" if scene.get("all_off") else None
            toast_manager.success(
                f"{scene['name']} activated" if not scene.get("all_off") else "All lights turned off",
                title=title or scene["name"],
                duration=4000 if scene.get("all_off") else 3500,
            )

    @staticmethod
    def _coerce_reed_closed(closed) -> Optional[bool]:
        if closed is None:
            return None
        if isinstance(closed, bool):
            return closed
        if isinstance(closed, str):
            value = closed.strip().lower()
            if value in ("true", "1", "yes", "on", "closed"):
                return True
            if value in ("false", "0", "no", "off", "open"):
                return False
        return bool(closed)

    def force_reed(self, name: str, closed: Optional[bool]) -> dict:
        closed = self._coerce_reed_closed(closed)
        if name == "all" and closed is None:
            self.world.clear_all_reed_forces()
            for reed in self.compiled.reed_names:
                self.reconciler.invalidate_commanded_for_reed(reed)
        elif closed is None:
            self.world.set_reed_force(name, None)
        else:
            if name not in self.compiled.reed_names:
                logger.warning(f"force_reed ignored — unknown reed: {name}")
                return self.get_ui_state()
            self.world.set_reed_force(name, closed)
        # Match phase force: operator overrides clear slider intents so policy
        # reflects the forced reed state, not stale manual levels.
        self.world.clear_all_light_intents()
        if name != "all":
            self.reconciler.invalidate_commanded_for_reed(name)
        preview = self._preview_ui_state("reed")
        self._emit_state(preview)
        self._emit_reeds()
        self._reconcile_async("reed")
        return preview

    def force_phase(self, phase: Optional[str]):
        if not self.phase_manager:
            return
        if phase is None:
            self.phase_manager.clear_force()
        else:
            self.phase_manager.force_phase(phase)
        pm = self.phase_manager
        self.world.set_phase(pm.get_phase(), pm.forced_phase, invalidate=True)
        self.reconcile(ramp_source="phase")

    def get_ui_state(self) -> dict:
        state = self.reconciler.build_ui_state()
        state.update(self.reconciler._last_emit_meta)
        return state

    def _preview_ui_state(self, ramp_source: str) -> dict:
        """Desired UI levels from policy — no hardware I/O (for instant slider animation)."""
        desired = desired_outputs(self.world.snapshot(), self.compiled)
        state = self.reconciler.build_ui_state(desired)
        if ramp_source in ANIMATED_RAMP_SOURCES:
            state.update({
                "_animate": True,
                "_ramp_ms": self._ramp_ms_for_source(ramp_source),
                "_trigger": ramp_source,
            })
        return state

    def get_reed_diag_json(self) -> dict:
        """Raw hardware + force overrides — diagnostics only."""
        snap = self.world.snapshot()
        return {"states": dict(snap.reeds), "forced": dict(snap.reed_forces)}

    def start_hardware(self):
        """Init serial/GPIO and load reed state. No reconcile yet — phase comes first."""
        self.arduino.init_serial()
        self.gpio.init_devices()

        initial_reeds = {n: self.gpio.reed_states.get(n, True) for n in self.compiled.reed_names}
        self.world.update_reeds(initial_reeds)
        self.reconciler.read_hardware()

    def bootstrap_phase(self):
        """Calculate real phase and write to world before any light automation runs."""
        pm = self.phase_manager
        if not pm:
            logger.warning("🌗 Phase manager not attached — automation deferred")
            return
        use_fallback = not pm._has_valid_gps()
        phase = pm.bootstrap_initial_phase(use_fallback=use_fallback)
        self.world.set_phase(phase, pm.forced_phase, invalidate=False)
        logger.info(f"🌗 Automation unlocked for phase: {phase}")

    def finish_startup(self):
        """Start reed polling and run the first reconcile (phase must already be set)."""
        self.reed_input = ReedInput(
            gpio_manager=self.gpio,
            reed_names=self.compiled.reed_names,
            debounce_ms=self.compiled.reed_debounce_ms,
            on_update=self.on_reeds_updated,
        )
        self.reed_input.start()
        self.reconcile(ramp_source="startup")

    def start_background_threads(self):
        threading.Thread(target=self._sync_loop, daemon=True, name="HardwareSync").start()
        threading.Thread(target=self._reconcile_loop, daemon=True, name="SafetyReconcile").start()

    def _sync_loop(self):
        while not self._shutdown.is_set():
            time.sleep(self.compiled.sync_interval_s)
            try:
                if self.arduino.is_connected():
                    self.reconciler.read_hardware()
                    self.reconciler.report_hardware_drift()
            except Exception as e:
                logger.debug(f"Hardware sync: {e}")

    def _reconcile_loop(self):
        while not self._shutdown.is_set():
            time.sleep(self.compiled.reconcile_interval_s)
            try:
                self.reconcile(ramp_source="auto")
            except Exception as e:
                logger.debug(f"Safety reconcile: {e}")

    def stop(self):
        self._shutdown.set()
        if self.reed_input:
            self.reed_input.stop()
            self.reed_input = None
        if self.phase_manager:
            self.phase_manager.stop()
        if self.sensor_manager:
            self.sensor_manager.stop()
        if self.gps:
            self.gps.cleanup()
        self.gpio.cleanup()
        self.arduino.cleanup()

    def get_frontend_config(self):
        return self.arduino.get_frontend_config()

    def get_reeds_frontend_config(self) -> list:
        """Ordered reed metadata for the system tile UI."""
        reeds = []
        if not self.config.has_section("reeds"):
            return reeds
        for name, line in self.config.get_section("reeds").items():
            parts = [p.strip() for p in str(line).split("|")]
            if len(parts) < 2:
                continue
            icon = parts[4] if len(parts) > 4 else "fa-door-closed"
            try:
                order = int(parts[5]) if len(parts) > 5 else 999
            except ValueError:
                order = 999
            reeds.append({"name": name, "label": parts[0], "icon": icon, "order": order})
        reeds.sort(key=lambda r: r.get("order", 999))
        return reeds