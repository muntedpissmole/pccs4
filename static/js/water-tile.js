/**
 * PCCS4 Water tile — fresh tank level percent + circular gauge.
 */
(function () {
    'use strict';

    const LOW_THRESHOLD = 25;
    const CRITICAL_THRESHOLD = 10;
    const RING_RADIUS = 52;
    const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

    const tile = document.getElementById('tile-water');
    const els = {
        percent: document.getElementById('water-percent'),
        litres: document.getElementById('water-litres'),
        gauge: document.getElementById('water-gauge'),
        fill: document.getElementById('water-gauge-fill'),
    };

    if (!tile || !els.percent) return;

    let tankCapacityLitres = null;

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

    function formatLitres(pct) {
        if (tankCapacityLitres == null || tankCapacityLitres <= 0 || pct === null) {
            return null;
        }
        return `${Math.round((pct / 100) * tankCapacityLitres)} L`;
    }

    function applyCapacity(capacity) {
        const litres = Number(capacity);
        if (!Number.isFinite(litres) || litres <= 0) return;
        tankCapacityLitres = litres;
    }

    function applyLitres(pct) {
        if (!els.litres) return;

        const text = formatLitres(pct);
        if (!text) {
            els.litres.hidden = true;
            return;
        }

        els.litres.textContent = text;
        els.litres.hidden = false;
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
            const litresLabel = formatLitres(pct);
            els.gauge.setAttribute(
                'aria-label',
                litresLabel
                    ? `Fresh water tank level, ${pct} percent, about ${litresLabel}`
                    : 'Fresh water tank level'
            );
        }
    }

    function update(data) {
        if (data?.water_capacity_litres != null) {
            applyCapacity(data.water_capacity_litres);
        }

        const raw =
            data?.water_percent ??
            data?.water_level ??
            data?.tank_percent ??
            data?.percent;
        const pct = clampPercent(raw);
        if (pct === null) return;

        els.percent.textContent = formatPercent(pct);
        applyLitres(pct);
        setRingLevel(pct);
        applyLevelState(pct);
    }

    function onSensorUpdate(data) {
        if (!data) return;
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

    const POLL_INTERVAL_MS = 5000;

    fetchSensors();
    setInterval(fetchSensors, POLL_INTERVAL_MS);

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.water = { update, onSensorUpdate, refresh: fetchSensors };

    window.waterTile = window.PCCS4.water;
})();