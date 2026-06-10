/**
 * PCCS4 Reed switches tile — live hardware + diag force controls.
 */
(function () {
    'use strict';

    const grid = document.getElementById('reeds-system-grid');
    const headlineEl = document.getElementById('reeds-summary-headline');
    const detailEl = document.getElementById('reeds-summary-detail');
    if (!grid || !headlineEl || !detailEl) return;

    const state = {
        reeds: [],
        raw: {},
        forced: {},
    };

    function getSocket() {
        return window.PCCS4?.socket ?? null;
    }

    function isForced(name) {
        return Object.prototype.hasOwnProperty.call(state.forced, name);
    }

    function getEffectiveClosed(reed) {
        if (isForced(reed.name)) return state.forced[reed.name];
        if (Object.prototype.hasOwnProperty.call(state.raw, reed.name)) {
            return state.raw[reed.name];
        }
        return reed.closed;
    }

    function sourceLabel(reed) {
        if (isForced(reed.name)) {
            const forcedText = getEffectiveClosed(reed) ? 'Forced closed' : 'Forced open';
            if (Object.prototype.hasOwnProperty.call(state.raw, reed.name)) {
                const sensorClosed = state.raw[reed.name];
                const sensorText = sensorClosed ? 'sensor closed' : 'sensor open';
                if (sensorClosed !== state.forced[reed.name]) {
                    return `${forcedText} · ${sensorText}`;
                }
            }
            return forcedText;
        }
        return 'Live sensor';
    }

    function renderSummary() {
        const total = state.reeds.length;
        if (!total) return;
        const closed = state.reeds.filter((reed) => getEffectiveClosed(reed)).length;
        const open = total - closed;
        const forcedCount = Object.keys(state.forced).length;

        headlineEl.textContent = `${closed} secure · ${open} open`;

        if (forcedCount > 0) {
            detailEl.textContent = `${forcedCount} override${forcedCount === 1 ? '' : 's'} active`;
            detailEl.classList.add('is-warning');
            return;
        }

        detailEl.textContent = open === 0 ? 'All panels latched' : 'Following live sensors';
        detailEl.classList.toggle('is-warning', open > 0);
    }

    function renderCard(reed) {
        const closed = getEffectiveClosed(reed);
        const forced = isForced(reed.name);

        const modifiers = [
            closed ? 'is-closed' : 'is-open',
            forced ? 'is-forced' : '',
        ].filter(Boolean).join(' ');

        return `
            <article class="reeds-system-tile__card ${modifiers}"
                     data-reed-name="${reed.name}"
                     role="listitem"
                     aria-label="${reed.label}">
                <div class="reeds-system-tile__panel" aria-hidden="true">
                    <div class="reeds-system-tile__frame">
                        <div class="reeds-system-tile__gap"></div>
                        <div class="reeds-system-tile__leaf">
                            <i class="fa-solid ${reed.icon}" aria-hidden="true"></i>
                        </div>
                    </div>
                    ${forced ? '<span class="reeds-system-tile__pin" aria-hidden="true"><i class="fa-solid fa-thumbtack"></i></span>' : ''}
                </div>

                <h3 class="reeds-system-tile__title">${reed.label}</h3>

                <div class="reeds-system-tile__segmented" role="group" aria-label="${reed.label} position">
                    <button type="button"
                            class="reeds-system-tile__segment${closed ? ' is-selected' : ''}"
                            data-reed-action="closed"
                            aria-pressed="${closed ? 'true' : 'false'}">
                        Closed
                    </button>
                    <button type="button"
                            class="reeds-system-tile__segment${!closed ? ' is-selected' : ''}"
                            data-reed-action="open"
                            aria-pressed="${!closed ? 'true' : 'false'}">
                        Open
                    </button>
                </div>

                <div class="reeds-system-tile__footer">
                    <span class="reeds-system-tile__source${forced ? ' is-override' : ''}" aria-live="polite">
                        ${sourceLabel(reed)}
                    </span>
                    <button type="button"
                            class="reeds-system-tile__clear"
                            data-reed-action="clear"
                            aria-label="Clear override for ${reed.label}"
                            ${forced ? '' : 'disabled'}>
                        <i class="fa-solid fa-xmark" aria-hidden="true"></i>
                    </button>
                </div>
            </article>`;
    }

    function render() {
        renderSummary();
        if (!state.reeds.length) {
            grid.innerHTML = '<p class="reeds-system-tile__empty">Loading reed switches…</p>';
            return;
        }
        grid.innerHTML = state.reeds.map(renderCard).join('');
    }

    function applyForceResult(data) {
        if (data?.reeds) onReedDiagUpdate(data.reeds);
        if (!data?.state) return;
        const rampMs = data.ramp_ms || data.state._ramp_ms || 2000;
        window.PCCS4.lighting?.onStateUpdate(data.state, { animate: true, rampMs });
        window.PCCS4.lightingHome?.onStateUpdate?.(data.state);
    }

    function emitForceReed(name, closed) {
        const socket = getSocket();
        if (socket?.connected) {
            socket.emit('force_reed', { name, closed });
            return;
        }
        fetch('/api/reeds/force', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, closed }),
            keepalive: true,
        })
            .then((res) => (res.ok ? res.json() : null))
            .then(applyForceResult)
            .catch((err) => console.warn('[PCCS4] force_reed HTTP failed', err));
    }

    function forceReed(name, closed) {
        state.forced[name] = closed;
        render();
        window.PCCS4.lighting?.setReedActivating?.(true);
        emitForceReed(name, closed);
    }

    function clearReedForce(name) {
        delete state.forced[name];
        render();
        emitForceReed(name, null);
    }

    function onReedsConfig(config) {
        if (!Array.isArray(config) || !config.length) return;
        state.reeds = config.map((reed) => ({
            name: reed.name,
            label: reed.label,
            icon: reed.icon || 'fa-door-closed',
            closed: state.raw[reed.name] ?? true,
        }));
        render();
    }

    function onReedDiagUpdate(payload) {
        if (!payload) return;
        state.raw = payload.states || {};
        state.forced = payload.forced || {};
        state.reeds = state.reeds.map((reed) => ({
            ...reed,
            closed: state.raw[reed.name] ?? reed.closed,
        }));
        render();
    }

    grid.addEventListener('click', (event) => {
        const button = event.target.closest('[data-reed-action]');
        if (!button || button.disabled) return;

        const card = button.closest('[data-reed-name]');
        if (!card) return;

        const name = card.dataset.reedName;
        const action = button.dataset.reedAction;

        if (action === 'closed') {
            forceReed(name, true);
            return;
        }
        if (action === 'open') {
            forceReed(name, false);
            return;
        }
        if (action === 'clear') {
            clearReedForce(name);
        }
    });

    async function loadReeds() {
        if (!window.PCCS4?.isSystemTabActive) return;
        try {
            const res = await fetch('/api/reeds', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            onReedsConfig(data.reeds);
            if (data.raw || data.forced) {
                onReedDiagUpdate({
                    states: data.raw || {},
                    forced: data.forced || {},
                });
            }
        } catch (err) {
            console.warn('[PCCS4] Failed to load reeds', err);
        }
    }

    render();

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.reedsSystem = {
        onReedsConfig,
        onReedDiagUpdate,
        forceReed,
        clearReedForce,
        getState: () => ({
            reeds: state.reeds.map((reed) => ({ ...reed })),
            forced: { ...state.forced },
            raw: { ...state.raw },
        }),
        refresh: loadReeds,
    };

    window.reedsSystemTile = window.PCCS4.reedsSystem;
})();