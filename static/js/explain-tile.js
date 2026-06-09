/**
 * PCCS4 Policy explain tile — why each light/relay is at its current level.
 */
(function () {
    'use strict';

    const tile = document.getElementById('tile-explain');
    const headlineEl = document.getElementById('explain-headline');
    const detailEl = document.getElementById('explain-detail');
    const lightsEl = document.getElementById('explain-lights');
    const driftsEl = document.getElementById('explain-drifts');
    if (!tile || !headlineEl || !detailEl || !lightsEl || !driftsEl) return;

    const POLL_INTERVAL_MS = 10000;
    let lastPayload = null;

    function formatPercent(value) {
        if (value == null) return '—';
        return `${Math.round(Number(value))}%`;
    }

    function renderLightRow(name, entry) {
        const desired = formatPercent(entry.desired_brightness);
        const observed = formatPercent(entry.observed_brightness);
        const mode = entry.desired_mode && entry.desired_mode !== 'white'
            ? ` · ${entry.desired_mode}`
            : '';
        const driftClass = entry.drift ? ' explain-tile__row--drift' : '';

        return `
            <div class="explain-tile__row${driftClass}">
                <div class="explain-tile__row-main">
                    <span class="explain-tile__name">${name}</span>
                    <span class="explain-tile__levels">${desired}${mode} → ${observed}</span>
                </div>
                <span class="explain-tile__source">${entry.source_label || entry.source || '—'}</span>
            </div>`;
    }

    function renderRelayRow(name, entry) {
        const desired = entry.desired ? 'ON' : 'OFF';
        const observed = entry.observed == null ? '—' : (entry.observed ? 'ON' : 'OFF');
        const driftClass = entry.drift ? ' explain-tile__row--drift' : '';

        return `
            <div class="explain-tile__row${driftClass}">
                <div class="explain-tile__row-main">
                    <span class="explain-tile__name">${name}</span>
                    <span class="explain-tile__levels">${desired} → ${observed}</span>
                </div>
                <span class="explain-tile__source">relay</span>
            </div>`;
    }

    function renderDrifts(drifts) {
        if (!drifts?.length) {
            driftsEl.hidden = true;
            driftsEl.innerHTML = '';
            return;
        }

        driftsEl.hidden = false;
        driftsEl.innerHTML = `
            <p class="explain-tile__drifts-title">Hardware drift</p>
            <ul class="explain-tile__drifts-list">
                ${drifts.map((item) => {
                    const label = item.light || item.relay || 'output';
                    return `<li><strong>${label}</strong> — ${item.detail || 'mismatch'}</li>`;
                }).join('')}
            </ul>`;
    }

    function render(data) {
        if (!data) return;
        lastPayload = data;

        const phase = data.phase || '—';
        const scene = data.active_scene ? ` · scene ${data.active_scene}` : '';
        const forced = data.phase_forced ? ' · phase forced' : '';
        headlineEl.textContent = `${phase}${scene}${forced}`;

        const driftCount = Array.isArray(data.drifts) ? data.drifts.length : 0;
        if (driftCount) {
            detailEl.textContent = `${driftCount} drift${driftCount === 1 ? '' : 's'} · trigger ${data.last_reconcile_trigger || 'unknown'}`;
            detailEl.classList.add('is-warning');
        } else {
            detailEl.textContent = `Aligned · trigger ${data.last_reconcile_trigger || 'unknown'}`;
            detailEl.classList.remove('is-warning');
        }

        const lightRows = Object.entries(data.lights || {})
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([name, entry]) => renderLightRow(name, entry))
            .join('');

        const relayRows = Object.entries(data.relays || {})
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([name, entry]) => renderRelayRow(name, entry))
            .join('');

        lightsEl.innerHTML = lightRows + relayRows || '<p class="explain-tile__empty">No outputs configured</p>';
        renderDrifts(data.drifts || []);
    }

    async function refresh() {
        if (!window.PCCS4?.isSystemTabActive) return;
        try {
            const res = await fetch('/api/explain', { cache: 'no-store' });
            if (!res.ok) return;
            render(await res.json());
        } catch {
            /* keep last values */
        }
    }

    setInterval(refresh, POLL_INTERVAL_MS);

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.explain = { refresh, render, getLast: () => lastPayload };
})();