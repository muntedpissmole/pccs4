/**
 * PCCS4 Socket.IO client — central hub for server → tile handlers.
 */
(function () {
    'use strict';

    window.PCCS4 = window.PCCS4 || {};

    function initSocket() {
        if (typeof io === 'undefined') {
            window.PCCS4.offline?.show();
            return;
        }

        const socket = io({ transports: ['websocket', 'polling'] });
        window.PCCS4.socket = socket;

        window.PCCS4.offline?.hide();
        window.PCCS4.offline?.register(socket);

        socket.on('connect', () => {
            console.info('[PCCS4] socket connected');
            window.PCCS4.offline?.hide();
            socket.emit('get_reeds');
            socket.emit('get_reeds_diag');
            socket.emit('get_victron_state');
            socket.emit('get_network_status');
            socket.emit('sonos_request_state');
            window.PCCS4.water?.refresh?.();
            window.PCCS4.climate?.refreshSensors?.();
            window.powerTile?.refresh?.();
            window.systemTile?.refresh?.();
            window.sonosTile?.refresh?.();
            window.PCCS4.location?.refresh?.();
            window.PCCS4.gpsStatus?.refresh?.();
            window.PCCS4.screensSystem?.refresh?.();
            window.PCCS4.reedsSystem?.refresh?.();
            window.PCCS4.reedsHome?.refresh?.();
            window.PCCS4.lightingHome?.refresh?.();
            window.PCCS4.lighting?.syncFromServer?.();
            window.PCCS4.phases?.refresh?.();
            window.PCCS4.explain?.refresh?.();
            window.PCCS4.wifi?.refresh?.({ quiet: true });
            window.pccsCoreTile?.refresh?.();
            window.colorMode?.refresh?.();
            document.dispatchEvent(new CustomEvent('pccs4:socket-ready', { detail: { socket } }));
            window.colorMode?.registerSocket?.(socket);
            window.themeManager?.registerSocket?.(socket);
        });

        socket.on('disconnect', () => {
            console.warn('[PCCS4] socket disconnected');
        });

        // Lighting
        socket.on('lights_config', (config) => {
            window.PCCS4.lighting?.onLightsConfig(config);
            window.PCCS4.lightingHome?.onLightsConfig?.(config);
        });

        socket.on('state_update', (state) => {
            window.PCCS4.scenes?.onStateUpdate?.(state);
            window.PCCS4.lightingHome?.onStateUpdate?.(state);
            const rampMs = state._ramp_ms ?? window.PCCS4.lighting?.getSceneRampMs?.();
            const animate = !!state._animate;
            window.PCCS4.lighting?.onStateUpdate(state, { rampMs, animate });
            window.PCCS4.explain?.refresh?.();
        });

        socket.on('reed_update', (payload) => {
            window.PCCS4.lighting?.onReedUpdate(payload);
            window.PCCS4.lightingHome?.onReedUpdate?.(payload);
            window.PCCS4.reedsHome?.onReedUpdate(payload);
            window.PCCS4.lighting?.setReedActivating?.(true);
        });

        // Scenes (state_update handles slider ramp after set_scene)

        // Phases
        socket.on('phase_update', (data) => {
            window.PCCS4.phases?.onPhaseUpdate(data);
        });

        socket.on('phase_diag_update', (data) => {
            window.PCCS4.phases?.onPhaseDiagUpdate(data);
        });

        // Reeds (diag)
        socket.on('reeds_config', (config) => {
            const reeds = Array.isArray(config) ? config : config?.reeds;
            window.PCCS4.reedsSystem?.onReedsConfig(reeds);
            window.PCCS4.reedsHome?.onReedsConfig?.(reeds);
        });

        socket.on('reed_diag_update', (payload) => {
            window.PCCS4.reedsSystem?.onReedDiagUpdate(payload);
        });

        // GPS
        socket.on('gps_update', (data) => {
            window.PCCS4.gpsStatus?.onGpsUpdate(data);
            window.PCCS4.location?.onGpsUpdate(data);
        });

        // Sensors (water + temps)
        socket.on('sensor_update', (data) => {
            window.PCCS4.water?.onSensorUpdate(data);
            window.PCCS4.climate?.onSensorUpdate(data);
        });

        // Toasts
        socket.on('toast', (data) => {
            window.pccs4Toasts?.handleServer?.(data);
        });

        // Touchscreens
        socket.on('screens_init', (data) => {
            window.PCCS4.screensSystem?.onScreensInit?.(data);
        });

        socket.on('screens_update', (data) => {
            window.PCCS4.screensSystem?.onScreensUpdate?.(data);
        });

        // Dark mode (phase-driven + manual override)
        socket.on('global_dark_mode_update', (data) => {
            window.colorMode?.applyFromServer?.(data);
        });

        // Victron / power tile
        socket.on('victron_update', (data) => {
            window.powerTile?.onVictronUpdate?.(data);
            window.victronSystemTile?.onVictronUpdate?.(data);
        });

        // Network
        socket.on('network_update', (data) => {
            window.PCCS4.network?.update?.(data);
        });

        // Theme
        socket.on('global_theme_update', (data) => {
            window.themeManager?.applyFromServer?.(data);
        });

        // Sonos
        socket.on('sonos_update', (data) => {
            window.sonosTile?.onSocketUpdate?.(data);
            window.sonosSystemTile?.onSocketUpdate?.(data);
        });

        socket.on('sonos_speakers', (data) => {
            window.sonosSystemTile?.onSpeakersUpdate?.(data);
        });

    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSocket);
    } else {
        initSocket();
    }
})();