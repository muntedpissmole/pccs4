/**
 * PCCS4 Lighting tab — sliders and relays via Socket.IO + HTTP fallback.
 */
(function () {
    'use strict';

    const JUST_SET_DURATION = 2800;
    const SCENE_RAMP_MS = 4000;
    let backendConnected = false;
    let sceneActivating = false;
    const sceneAnimationCancels = {};

    const state = {
        lightsConfig: [],
        currentState: {},
        currentModes: {},
        currentReeds: {},
        lastRenderConfigHash: '',
        currentlyDragging: new Set(),
        userJustSet: new Set(),
    };

    let lastTouchPointerUp = 0;
    let lastColumnCount = 1;

    function getSocket() {
        return window.PCCS4?.socket ?? null;
    }

    function emitLightChange(payload) {
        const socket = getSocket();
        if (socket?.connected) {
            socket.emit('light_change', payload);
        }
        fetch('/api/light', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            keepalive: true,
        })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (data?.state) applyStateToUI(data.state);
            })
            .catch((err) => console.warn('[PCCS4] light_change HTTP failed', err));
    }

    function emitRelayChange(name, on) {
        const socket = getSocket();
        if (!socket?.connected) {
            console.warn('[PCCS4] relay_change skipped — socket unavailable', name);
            return false;
        }
        socket.emit('relay_change', { name, on });
        return true;
    }

    function cancelSceneAnimations() {
        Object.values(sceneAnimationCancels).forEach((cancel) => {
            if (typeof cancel === 'function') cancel();
        });
        Object.keys(sceneAnimationCancels).forEach((k) => delete sceneAnimationCancels[k]);
    }

    function setSliderMotion(wrapper, enabled) {
        if (!wrapper) return;
        const fill = wrapper.querySelector('.slider-fill');
        const thumb = wrapper.querySelector('.slider-thumb');
        const transition = enabled ? '' : 'none';
        if (fill) fill.style.transition = transition;
        if (thumb) thumb.style.transition = transition;
    }

    function animateSlider(name, from, to, rampMs, onComplete) {
        const wrapper = document.querySelector(`.slider-wrapper[data-name="${name}"]`);
        const start = performance.now();
        let frameId = null;

        function cancel() {
            if (frameId) cancelAnimationFrame(frameId);
            delete sceneAnimationCancels[name];
        }

        function step(now) {
            const t = Math.min(1, (now - start) / rampMs);
            const value = Math.round(from + (to - from) * t);
            updateLightUI(name, value);
            if (t < 1) {
                frameId = requestAnimationFrame(step);
            } else {
                updateLightUI(name, to);
                setSliderMotion(wrapper, true);
                delete sceneAnimationCancels[name];
                onComplete?.();
            }
        }

        sceneAnimationCancels[name] = cancel;
        setSliderMotion(wrapper, false);
        frameId = requestAnimationFrame(step);
        return cancel;
    }

    const STATE_META_KEYS = new Set(['last_scene']);

    function applyStateToUI(newState, { animate = false, rampMs = SCENE_RAMP_MS } = {}) {
        const protectedLights = new Set([...state.currentlyDragging]);
        if (!animate) {
            state.userJustSet.forEach((name) => protectedLights.add(name));
        }

        state.lightsConfig.forEach((light) => {
            const modeKey = `${light.name}_mode`;
            if (light.has_mode && newState[modeKey] && !protectedLights.has(light.name)) {
                state.currentModes[light.name] = newState[modeKey];
            }
        });

        if (!animate) {
            Object.keys(newState).forEach((k) => {
                if (k.endsWith('_mode') || STATE_META_KEYS.has(k)) return;
                if (!protectedLights.has(k)) state.currentState[k] = newState[k];
            });
            updateUIFromState();
            return;
        }

        cancelSceneAnimations();

        state.lightsConfig.forEach((light) => {
            if (protectedLights.has(light.name)) return;

            const target = newState[light.name];
            if (target === undefined) return;

            if (light.type === 'relay') {
                state.currentState[light.name] = !!target;
                updateLightUI(light.name, !!target);
                return;
            }

            const wrapper = document.querySelector(`.slider-wrapper[data-name="${light.name}"]`);
            const startVal = parseInt(wrapper?.dataset.value, 10);
            const from = Number.isFinite(startVal) ? startVal : (state.currentState[light.name] || 0);
            const end = Math.max(0, Math.min(100, target || 0));
            state.currentState[light.name] = end;

            if (from === end) {
                updateLightUI(light.name, end);
                return;
            }

            animateSlider(light.name, from, end, rampMs);
        });

        updateRooftopTentControls();
    }

    function getCurrentColumns() {
        const container = document.getElementById('lighting-controls');
        if (!container) return 1;

        const style = window.getComputedStyle(container);
        const gridTemplate = style.gridTemplateColumns || style.getPropertyValue('grid-template-columns');

        if (gridTemplate.includes('repeat(1') || gridTemplate.split(' ').length === 1) return 1;
        if (gridTemplate.includes('repeat(2') || gridTemplate.split(' ').length === 2) return 2;
        if (gridTemplate.includes('repeat(3') || gridTemplate.split(' ').length === 3) return 3;

        const children = container.children.length;
        if (children > 0) {
            const firstChild = container.children[0];
            const containerRect = container.getBoundingClientRect();
            const childRect = firstChild.getBoundingClientRect();

            if (containerRect.width > 0) {
                const approxCols = Math.round(containerRect.width / (childRect.width + 16));
                return Math.max(1, Math.min(3, approxCols));
            }
        }

        return 1;
    }

    function isRooftopTentPhysicallyClosed() {
        return state.currentReeds.rooftop_tent !== false;
    }

    function updateRooftopTentControls() {
        const tentCard = document.querySelector('.slider-wrapper[data-name="rooftop_tent"]')?.closest('.slider-card');
        if (!tentCard) return;

        const isClosed = isRooftopTentPhysicallyClosed();

        if (isClosed) {
            tentCard.classList.add('rooftop-disabled');
            updateLightUI('rooftop_tent', 0);
        } else {
            tentCard.classList.remove('rooftop-disabled');
        }
    }

    function updateLightUI(name, value) {
        const light = state.lightsConfig.find((l) => l.name === name);
        if (!light) return;

        const valueEl = document.getElementById(`val-${name}`);
        const pills = document.querySelectorAll(
            `.toggle-pill[data-name="${name}"], .relay-toggle[data-name="${name}"]`
        );

        if (light.type === 'relay') {
            const isOn = !!value;

            pills.forEach((toggle) => {
                toggle.classList.toggle('on', isOn);
                toggle.dataset.state = isOn ? 'on' : 'off';
            });

            if (valueEl) valueEl.textContent = isOn ? 'On' : 'Off';
            return;
        }

        const wrapper = document.querySelector(`.slider-wrapper[data-name="${name}"]`);
        const fill = wrapper ? wrapper.querySelector('.slider-fill') : null;
        const thumb = wrapper ? wrapper.querySelector('.slider-thumb') : null;
        const brightness = Math.max(0, Math.min(100, value || 0));
        const card = wrapper ? wrapper.closest('.slider-card') : null;

        if (wrapper) {
            wrapper.dataset.value = brightness;
            if (brightness > 0) wrapper.dataset.lastBrightness = brightness;

            if (fill) fill.style.width = `${brightness}%`;
            if (thumb) thumb.style.left = `${brightness}%`;
            if (valueEl) valueEl.textContent = `${brightness}%`;
        }

        const isBugMode = light.has_mode && (state.currentModes[name] || 'white') === 'red';
        const pillOn = light.has_mode ? isBugMode : brightness > 0;

        pills.forEach((pill) => {
            pill.classList.toggle('on', pillOn);
            pill.classList.toggle('bug-mode', isBugMode);
            pill.dataset.state = pillOn ? 'on' : 'off';
        });

        if (card) card.classList.toggle('bug-mode', isBugMode);

        if (wrapper) {
            wrapper.classList.toggle('bug-mode', isBugMode);
            if (fill) fill.classList.toggle('bug-mode', isBugMode);
            if (thumb) thumb.classList.toggle('bug-mode', isBugMode);
        }
    }

    function updateUIFromState() {
        state.lightsConfig.forEach((light) => {
            if (state.currentlyDragging.has(light.name) || state.userJustSet.has(light.name)) {
                return;
            }

            const val = state.currentState[light.name];
            if (val === undefined) return;

            updateLightUI(light.name, light.type === 'relay' ? !!val : (val || 0));
        });

        updateRooftopTentControls();
    }

    function toggleControl(el) {
        const name = el.dataset.name;
        const light = state.lightsConfig.find((l) => l.name === name);
        if (!light) return;

        if (name === 'rooftop_tent' && isRooftopTentPhysicallyClosed()) return;

        state.userJustSet.add(name);
        setTimeout(() => state.userJustSet.delete(name), JUST_SET_DURATION);

        if (light.type === 'relay') {
            const isCurrentlyOn = el.dataset.state === 'on';
            const newState = !isCurrentlyOn;

            state.currentState[name] = newState ? 1 : 0;
            updateLightUI(name, newState ? 1 : 0);
            emitRelayChange(name, newState);
            return;
        }

        if (light.has_mode) {
            const currentMode = state.currentModes[name] || 'white';
            const newMode = currentMode === 'white' ? 'red' : 'white';
            state.currentModes[name] = newMode;
            state.currentState[`${name}_mode`] = newMode;

            const currentBrightness = state.currentState[name] || 0;
            updateLightUI(name, currentBrightness);
            emitLightChange({ name, brightness: currentBrightness, mode: newMode });
            return;
        }

        const wrapper = document.querySelector(`.slider-wrapper[data-name="${name}"]`);
        const currentBrightness = wrapper ? parseInt(wrapper.dataset.value, 10) || 0 : 0;
        const isOn = el.dataset.state === 'on';
        const newBrightness = isOn ? 0 : (parseInt(wrapper?.dataset.lastBrightness, 10) || 100);

        state.currentState[name] = newBrightness;
        updateLightUI(name, newBrightness);
        emitLightChange({ name, brightness: newBrightness });
    }

    function initUnifiedToggleListeners() {
        const container = document.getElementById('lighting-controls');
        if (!container) return;

        container.removeEventListener('click', handleLightingClick);

        function handleLightingClick(e) {
            const toggle = e.target.closest('.relay-toggle, .toggle-pill');
            if (!toggle) return;

            if (toggle.dataset.justClicked === 'true') return;
            toggle.dataset.justClicked = 'true';
            setTimeout(() => delete toggle.dataset.justClicked, 350);

            toggleControl(toggle);
        }

        container.addEventListener('click', handleLightingClick);
    }

    function makeDraggable(wrapper) {
        if (wrapper.dataset.pccsSliderBound === '1') return;
        wrapper.dataset.pccsSliderBound = '1';

        const inner = wrapper.querySelector('.slider-inner');
        const fill = wrapper.querySelector('.slider-fill');
        const thumb = wrapper.querySelector('.slider-thumb');
        const name = wrapper.dataset.name;
        const valueEl = document.getElementById(`val-${name}`);

        let isDragging = false;
        let activePointerId = null;
        let startX = 0;
        let startY = 0;
        let valueAtPointerStart = 0;

        function updatePosition(clientX) {
            const rect = inner.getBoundingClientRect();
            const percent = Math.max(
                0,
                Math.min(100, Math.round(((clientX - rect.left) / rect.width) * 100))
            );

            wrapper.dataset.value = percent;
            if (fill) fill.style.width = `${percent}%`;
            if (thumb) thumb.style.left = `${percent}%`;
            if (valueEl) valueEl.textContent = `${percent}%`;
        }

        function startDrag() {
            if (isDragging) return;
            isDragging = true;
            wrapper.classList.add('dragging');
            state.currentlyDragging.add(name);
            state.userJustSet.delete(name);
            if (fill) fill.style.transition = 'none';
            if (thumb) thumb.style.transition = 'none';
        }

        function commitDrag(force) {
            if (!force && !isDragging) return;

            const final = parseInt(wrapper.dataset.value, 10) || 0;
            isDragging = false;
            activePointerId = null;
            wrapper.classList.remove('dragging');
            state.currentlyDragging.delete(name);

            state.userJustSet.add(name);
            setTimeout(() => state.userJustSet.delete(name), JUST_SET_DURATION);
            state.currentState[name] = final;
            updateLightUI(name, final);

            const light = state.lightsConfig.find((l) => l.name === name);
            const payload = { name, brightness: final };
            if (light?.has_mode && state.currentModes[name]) {
                payload.mode = state.currentModes[name];
            }
            emitLightChange(payload);
        }

        wrapper.addEventListener('pointerdown', (e) => {
            if (e.button !== 0) return;
            if (name === 'rooftop_tent' && isRooftopTentPhysicallyClosed()) return;
            if (e.pointerType === 'mouse' && Date.now() - lastTouchPointerUp < 600) return;

            activePointerId = e.pointerId;
            startX = e.clientX;
            startY = e.clientY;
            valueAtPointerStart = parseInt(wrapper.dataset.value, 10) || 0;
            isDragging = false;

            if (e.pointerType === 'mouse') {
                e.preventDefault();
                wrapper.setPointerCapture(e.pointerId);
                startDrag();
                updatePosition(e.clientX);
            }
        });

        wrapper.addEventListener('pointermove', (e) => {
            if (e.pointerId !== activePointerId) return;
            if (name === 'rooftop_tent' && isRooftopTentPhysicallyClosed()) return;

            const deltaX = Math.abs(e.clientX - startX);
            const deltaY = Math.abs(e.clientY - startY);

            if (!isDragging) {
                if (e.pointerType === 'mouse') {
                    startDrag();
                } else if (deltaX > 10 && deltaX > deltaY * 1.5) {
                    e.preventDefault();
                    wrapper.setPointerCapture(e.pointerId);
                    startDrag();
                } else {
                    return;
                }
            }

            e.preventDefault();
            updatePosition(e.clientX);
        });

        wrapper.addEventListener('pointerup', (e) => {
            if (e.pointerId !== activePointerId) return;
            if (e.pointerType === 'touch') lastTouchPointerUp = Date.now();
            try {
                wrapper.releasePointerCapture(e.pointerId);
            } catch (_) {
                /* ok */
            }

            const final = parseInt(wrapper.dataset.value, 10) || 0;
            const changed = isDragging || final !== valueAtPointerStart;
            if (changed) commitDrag(true);
            else {
                isDragging = false;
                activePointerId = null;
            }
        });

        wrapper.addEventListener('pointercancel', (e) => {
            if (e.pointerId !== activePointerId) return;
            if (isDragging) commitDrag(true);
            else {
                isDragging = false;
                activePointerId = null;
            }
        });
    }

    function initSliders() {
        document
            .querySelectorAll('.slider-wrapper:not([data-pccs-slider-bound="1"])')
            .forEach(makeDraggable);
    }

    function renderLightingControls() {
        const container = document.getElementById('lighting-controls');
        if (!container) return false;

        if (!state.lightsConfig.length) {
            container.innerHTML = '<p class="lighting-connecting">Connecting to lighting backend…</p>';
            return false;
        }

        const currentHash = JSON.stringify(state.lightsConfig.map((l) => l.name + l.type));
        if (currentHash === state.lastRenderConfigHash && state.lightsConfig.length > 0) {
            updateUIFromState();
            return true;
        }

        state.lastRenderConfigHash = currentHash;
        container.innerHTML = '';

        const columns = getCurrentColumns();

        let i = 0;
        while (i < state.lightsConfig.length) {
            const light = state.lightsConfig[i];

            const canPair =
                light.type === 'relay' &&
                i + 1 < state.lightsConfig.length &&
                state.lightsConfig[i + 1].type === 'relay';

            let shouldPair = canPair;

            if (canPair) {
                if (columns === 1) {
                    shouldPair = false;
                } else if (columns === 2) {
                    const isLastPair = i + 2 === state.lightsConfig.length;
                    shouldPair = !isLastPair;
                }
            }

            if (shouldPair) {
                const relay1 = light;
                const relay2 = state.lightsConfig[i + 1];

                container.insertAdjacentHTML(
                    'beforeend',
                    `
                    <div class="slider-card paired-relay-card">
                        <div class="paired-relay-inner">
                            <div class="paired-relay-row">
                                <div class="slider-card-left">
                                    <div class="slider-card-title">
                                        <i class="fa-solid ${relay1.icon}"></i>
                                        <span class="slider-label">${relay1.label}</span>
                                    </div>
                                </div>
                                <div class="slider-card-right">
                                    <div class="value-display" id="val-${relay1.name}">${state.currentState[relay1.name] ? 'On' : 'Off'}</div>
                                    <div class="relay-toggle ${state.currentState[relay1.name] ? 'on' : ''}"
                                         data-name="${relay1.name}"
                                         data-state="${state.currentState[relay1.name] ? 'on' : 'off'}">
                                        <div class="relay-knob"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="paired-relay-divider"></div>
                            <div class="paired-relay-row">
                                <div class="slider-card-left">
                                    <div class="slider-card-title">
                                        <i class="fa-solid ${relay2.icon}"></i>
                                        <span class="slider-label">${relay2.label}</span>
                                    </div>
                                </div>
                                <div class="slider-card-right">
                                    <div class="value-display" id="val-${relay2.name}">${state.currentState[relay2.name] ? 'On' : 'Off'}</div>
                                    <div class="relay-toggle ${state.currentState[relay2.name] ? 'on' : ''}"
                                         data-name="${relay2.name}"
                                         data-state="${state.currentState[relay2.name] ? 'on' : 'off'}">
                                        <div class="relay-knob"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>`
                );

                i += 2;
                continue;
            }

            const isRelay = light.type === 'relay';
            const currentVal = state.currentState[light.name] || 0;
            const isOn = isRelay ? !!currentVal : false;
            const brightness = isRelay ? 0 : Math.max(0, Math.min(100, currentVal || 0));

            let html = `
                <div class="slider-card">
                    <div class="slider-card-header">
                        <div class="slider-card-left">
                            <div class="slider-card-title">
                                <i class="fa-solid ${light.icon}"></i>
                                <span class="slider-label">${light.label}</span>
                            </div>
                        </div>
                        <div class="slider-card-right">
                            <div class="value-display" id="val-${light.name}">
                                ${isRelay ? (isOn ? 'On' : 'Off') : `${brightness}%`}
                            </div>`;

            if (isRelay) {
                html += `
                            <div class="relay-toggle ${isOn ? 'on' : ''}"
                                 data-name="${light.name}"
                                 data-state="${isOn ? 'on' : 'off'}">
                                <div class="relay-knob"></div>
                            </div>`;
            } else {
                const extraClass = light.has_mode ? 'colour-toggle' : '';
                html += `
                            <div class="toggle-pill ${extraClass}" data-name="${light.name}" data-state="off">
                                <div class="toggle-knob"></div>
                            </div>`;
            }

            html += '</div></div>';

            if (!isRelay) {
                html += `
                    <div class="slider-wrapper" data-name="${light.name}" data-value="${brightness}" data-last-brightness="${brightness || 100}">
                        <div class="slider-inner">
                            <div class="slider-track"></div>
                            <div class="slider-fill" style="width: ${brightness}%"></div>
                            <div class="slider-thumb" style="left: ${brightness}%"></div>
                        </div>
                    </div>`;
            }

            html += '</div>';
            container.insertAdjacentHTML('beforeend', html);
            i += 1;
        }

        initUnifiedToggleListeners();
        initSliders();
        setTimeout(updateUIFromState, 100);
        return true;
    }

    function initResize() {
        function handleResizeForLighting() {
            const newCols = getCurrentColumns();
            if (newCols !== lastColumnCount && state.lightsConfig.length > 0) {
                lastColumnCount = newCols;
                renderLightingControls();
            }
        }

        window.addEventListener('resize', handleResizeForLighting);
        setTimeout(() => {
            lastColumnCount = getCurrentColumns();
        }, 300);
    }

    function init() {
        if (!document.getElementById('lighting-controls')) return;

        state.lightsConfig.forEach((light) => {
            const mode = state.currentState[`${light.name}_mode`];
            if (light.has_mode && mode) state.currentModes[light.name] = mode;
        });

        renderLightingControls();
        initResize();
    }

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.lighting = {
        onLightsConfig(config) {
            backendConnected = true;
            state.lightsConfig = config || [];
            state.currentState = {};
            state.currentModes = {};
            state.lastRenderConfigHash = '';
            state.lightsConfig.forEach((light) => {
                const mode = state.currentState[`${light.name}_mode`];
                if (light.has_mode && mode) state.currentModes[light.name] = mode;
            });
            renderLightingControls();
            const socket = getSocket();
            if (socket?.connected) socket.emit('get_reeds');
            if (Object.keys(state.currentState).length > 0) updateUIFromState();
        },
        onStateUpdate(newState, options = {}) {
            const animate = options.animate ?? sceneActivating;
            if (sceneActivating) sceneActivating = false;
            applyStateToUI(newState, {
                animate,
                rampMs: options.rampMs ?? SCENE_RAMP_MS,
            });
        },
        setSceneActivating(value, rampMs) {
            sceneActivating = !!value;
            if (rampMs) window.PCCS4._sceneRampMs = rampMs;
        },
        getSceneRampMs() {
            return window.PCCS4._sceneRampMs || SCENE_RAMP_MS;
        },
        onReedUpdate(payload) {
            state.currentReeds = payload.states || {};
            updateRooftopTentControls();
        },
        initResize,
        isBackendConnected() {
            return backendConnected;
        },
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();