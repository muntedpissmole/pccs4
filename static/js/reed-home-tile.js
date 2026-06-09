/**
 * PCCS4 Home page reed summary — built from reeds_config, updated via reed_update.
 */
(function () {
    'use strict';

    const listEl = document.getElementById('reed-home-list');
    if (!listEl) return;

    const state = {
        reeds: [],
        raw: {},
    };

    function renderList() {
        if (!state.reeds.length) {
            listEl.innerHTML = '<li class="reed-tile__item"><span class="reed-tile__name">Loading panels…</span></li>';
            return;
        }

        listEl.innerHTML = state.reeds.map((reed) => {
            const closed = Object.prototype.hasOwnProperty.call(state.raw, reed.name)
                ? state.raw[reed.name]
                : true;
            const isClosed = closed !== false;
            return `
                <li class="reed-tile__item ${isClosed ? 'is-closed' : 'is-open'}"
                    id="reed-${reed.name}"
                    data-reed-name="${reed.name}">
                    <span class="reed-tile__status" aria-hidden="true"></span>
                    <span class="reed-tile__name">${reed.label}</span>
                    <span class="reed-tile__state" aria-live="polite">${isClosed ? 'Closed' : 'Open'}</span>
                </li>`;
        }).join('');
    }

    function updateReed(name, closed) {
        state.raw[name] = closed;
        const el = document.getElementById(`reed-${name}`);
        if (!el) return;

        const stateEl = el.querySelector('.reed-tile__state');
        const isClosed = closed !== false;

        el.classList.toggle('is-closed', isClosed);
        el.classList.toggle('is-open', !isClosed);
        if (stateEl) stateEl.textContent = isClosed ? 'Closed' : 'Open';
    }

    function onReedsConfig(reeds) {
        if (!Array.isArray(reeds) || !reeds.length) return;
        state.reeds = reeds.map((reed) => ({ ...reed }));
        renderList();
        Object.entries(state.raw).forEach(([name, closed]) => updateReed(name, closed));
    }

    function onReedUpdate(payload) {
        const states = payload?.states || {};
        Object.entries(states).forEach(([name, closed]) => updateReed(name, closed));
    }

    async function loadReeds() {
        try {
            const res = await fetch('/api/reeds', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            onReedsConfig(data.reeds);
            if (data.states) {
                onReedUpdate({ states: data.states });
            }
        } catch {
            /* socket will deliver reeds_config */
        }
    }

    renderList();
    loadReeds();

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.reedsHome = { onReedsConfig, onReedUpdate, refresh: loadReeds };
})();