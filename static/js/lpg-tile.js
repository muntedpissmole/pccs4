/**
 * PCCS4 LPG tile — propane tank level percent + circular gauge.
 */
(function () {
    'use strict';

    const POLL_INTERVAL_MS = 5000;
    const LOW_THRESHOLD = 25;
    const CRITICAL_THRESHOLD = 10;
    const RING_RADIUS = 52;
    const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

    const tile = document.getElementById('tile-lpg');
    const els = {
        percent: document.getElementById('lpg-percent'),
        gauge: document.getElementById('lpg-gauge'),
        fill: document.getElementById('lpg-gauge-fill'),
    };

    if (!tile || !els.percent) return;

    function clampPercent(value) {
        const n = Number(value);
        if (Number.isNaN(n)) return null;
        return Math.max(0, Math.min(100, Math.round(n)));
    }

    function formatPercent(value) {
        const pct = clampPercent(value);
        if (pct === null) return '—%';
        return `${pct}%`;
    }

    function applyLevelState(pct) {
        tile.classList.toggle('is-low', pct > 0 && pct <= LOW_THRESHOLD);
        tile.classList.toggle('is-critical', pct > 0 && pct <= CRITICAL_THRESHOLD);
    }

    function setRingLevel(pct) {
        const offset = RING_CIRCUMFERENCE * (1 - pct / 100);

        if (els.fill) {
            els.fill.style.strokeDasharray = String(RING_CIRCUMFERENCE);
            els.fill.style.strokeDashoffset = String(offset);
            els.fill.style.setProperty('--ring-offset', String(offset));
        }

        if (els.gauge) {
            els.gauge.setAttribute('aria-valuenow', String(pct));
        }
    }

    function update(data) {
        if (!data) return;

        const unconfigured = data.enabled === false || data.source === 'unconfigured';
        tile.classList.toggle('is-unconfigured', unconfigured);
        if (unconfigured) {
            els.percent.textContent = 'N/A';
            if (els.gauge) els.gauge.setAttribute('aria-valuenow', '0');
            setRingLevel(0);
            tile.classList.remove('is-low', 'is-critical');
            return;
        }

        const raw =
            data.level_percent ??
            data.lpg_percent ??
            data.percent ??
            data.level;
        const pct = clampPercent(raw);
        if (pct === null) return;

        els.percent.textContent = formatPercent(pct);
        setRingLevel(pct);
        applyLevelState(pct);
    }

    async function fetchStatus() {
        try {
            const res = await fetch('/api/lpg', { cache: 'no-store' });
            if (!res.ok) return;
            update(await res.json());
        } catch {
            /* keep last values */
        }
    }

    function onSensorUpdate(data) {
        if (!data || data.lpg_percent == null) return;
        update(data);
    }

    async function fetchSensors() {
        try {
            const res = await fetch('/api/sensors', { cache: 'no-store' });
            if (!res.ok) return;
            onSensorUpdate(await res.json());
        } catch {
            /* socket will deliver sensor_update */
        }
    }

    fetchStatus();
    fetchSensors();
    setInterval(fetchStatus, POLL_INTERVAL_MS);

    window.lpgTile = { update, onSensorUpdate, refresh: fetchStatus };
})();