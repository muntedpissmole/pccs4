/**
 * PCCS4 Scenes tab — loads from /api/scenes, activates via socket + HTTP fallback.
 */
(function () {
    'use strict';

    const state = {
        currentScenes: [],
        backendLoaded: false,
        activeScene: null,
        activatingScene: null,
    };

    function getSocket() {
        return window.PCCS4?.socket ?? null;
    }

    function setActiveScene(sceneKey) {
        state.activeScene = sceneKey || null;
        document.querySelectorAll('.scene-btn').forEach((btn) => {
            btn.classList.toggle('active', Boolean(sceneKey) && btn.dataset.scene === sceneKey);
        });
    }

    function setScene(sceneKey) {
        state.activatingScene = sceneKey;
        setActiveScene(sceneKey);

        window.PCCS4?.lighting?.setSceneActivating(true);

        const socket = getSocket();
        if (socket?.connected) {
            socket.emit('set_scene', { scene: sceneKey });
            return;
        }

        fetch('/api/scene', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scene: sceneKey }),
        })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (!data?.state) {
                    window.PCCS4?.lighting?.setSceneActivating(false);
                    state.activatingScene = null;
                    return;
                }
                const rampMs = data.ramp_ms || window.PCCS4?.lighting?.getSceneRampMs?.();
                window.PCCS4?.lighting?.onStateUpdate(data.state, { animate: true, rampMs });
                setActiveScene(data.state.last_scene || null);
                state.activatingScene = null;
            })
            .catch((err) => {
                window.PCCS4?.lighting?.setSceneActivating(false);
                state.activatingScene = null;
                console.warn('[PCCS4] set_scene HTTP failed', err);
            });
    }

    function onStateUpdate(payload) {
        const sceneKey = payload?.last_scene || null;
        if (state.activatingScene && sceneKey && state.activatingScene !== sceneKey) return;
        setActiveScene(sceneKey);
        state.activatingScene = null;
    }

    function getSceneGridColumns() {
        if (window.matchMedia('(min-width: 157.5625rem)').matches) return 6;
        if (window.matchMedia('(max-width: 40rem)').matches) return 1;
        if (window.matchMedia('(max-width: 64rem)').matches) return 2;
        return 3;
    }

    function fixLastRowStretching(container) {
        const cols = getSceneGridColumns();
        const total = state.currentScenes.length;
        if (total <= cols) return;

        const remainder = total % cols;
        if (remainder === 0) return;

        container.querySelectorAll('.last-row').forEach((el) => {
            Array.from(el.children).forEach((kid) => container.appendChild(kid));
            el.remove();
        });

        const buttons = Array.from(container.children).filter(
            (el) => el.classList?.contains('scene-btn'),
        );

        buttons.forEach((btn) => {
            btn.style.gridColumn = '';
        });

        const lastRowStart = total - remainder;

        if (remainder === 1) {
            buttons[lastRowStart].style.gridColumn = '1 / -1';
            return;
        }

        if (remainder === 2 && cols >= 2) {
            const btn1 = buttons[lastRowStart];
            const btn2 = buttons[lastRowStart + 1];
            const wrapper = document.createElement('div');

            wrapper.className = 'last-row';
            wrapper.style.gridColumn = '1 / -1';
            wrapper.appendChild(btn1);
            wrapper.appendChild(btn2);
            container.appendChild(wrapper);
        }
    }

    function renderScenes() {
        const container = document.getElementById('scenes-grid');
        if (!container) return;

        container.innerHTML = '';

        if (!state.currentScenes.length) {
            container.innerHTML = '<p class="scenes-grid__loading">Loading scenes…</p>';
            return;
        }

        state.currentScenes.forEach((scene) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `scene-btn${scene.all_off ? ' all-off-btn' : ''}`;
            btn.dataset.scene = scene.key;

            if (scene.description) {
                btn.title = scene.description;
            }

            btn.innerHTML = `
                <i class="fa-solid ${scene.icon}" aria-hidden="true"></i>
                <span>${scene.name}</span>
            `;

            btn.addEventListener('click', () => setScene(scene.key));
            container.appendChild(btn);
        });

        fixLastRowStretching(container);
        if (state.activeScene) {
            setActiveScene(state.activeScene);
        }
    }

    async function loadScenes() {
        try {
            const res = await fetch('/api/scenes');
            if (!res.ok) return;
            const data = await res.json();
            if (Array.isArray(data.scenes) && data.scenes.length > 0) {
                state.currentScenes = data.scenes;
                state.backendLoaded = true;
                renderScenes();
            }
        } catch (err) {
            console.warn('[PCCS4] Failed to load scenes', err);
        }
    }

    let resizeTimer = null;

    function onResize() {
        const container = document.getElementById('scenes-grid');
        if (!container || !state.currentScenes.length) return;
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => fixLastRowStretching(container), 100);
    }

    function init() {
        if (!document.getElementById('scenes-grid')) return;
        renderScenes();
        loadScenes();
        window.addEventListener('resize', onResize);
    }

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.scenes = {
        loadScenes,
        setScene,
        renderScenes,
        onStateUpdate,
        setActiveScene,
        isBackendLoaded: () => state.backendLoaded,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();