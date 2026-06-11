/**
 * PCCS4 Date & Time tile — clock, sunrise/sunset, sun/moon bezier arc.
 */
(function () {
    'use strict';

    const DAY_MINUTES = 1440;
    const SUN_ANIM_MS = 680;

    /** Known IANA zones → coords (PCCS camper default: Alexandra, VIC). */
    const TIMEZONE_COORDS = {
        'Australia/Melbourne': { lat: -37.191, lng: 145.711 },
        'Australia/Sydney': { lat: -33.8688, lng: 151.2093 },
        'Australia/Brisbane': { lat: -27.4698, lng: 153.0251 },
        'Australia/Hobart': { lat: -42.8821, lng: 147.3272 },
        'Australia/Adelaide': { lat: -34.9285, lng: 138.6007 },
        'Australia/Perth': { lat: -31.9505, lng: 115.8605 },
        'Australia/Darwin': { lat: -12.4634, lng: 130.8456 },
        'Europe/London': { lat: 51.5074, lng: -0.1278 },
    };

    function defaultCoords() {
        let tz = '';
        try {
            tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
        } catch (_) { /* ignore */ }

        if (TIMEZONE_COORDS[tz]) {
            return { ...TIMEZONE_COORDS[tz] };
        }

        if (tz.startsWith('Australia/')) {
            return { lat: -37.191, lng: 145.711 };
        }

        const lng = (-new Date().getTimezoneOffset() / 60) * 15;
        const lat = lng > 65 || lng < -65 ? 51.5 : (new Date().getTimezoneOffset() < 0 ? -35 : 51.5);
        return { lat, lng };
    }

    const home = window.pccs4Location;
    const defaults = home
        ? { lat: home.latitude, lng: home.longitude }
        : defaultCoords();
    let lat = defaults.lat;
    let lng = defaults.lng;

    const els = {
        date: document.getElementById('tile-date'),
        time: document.getElementById('tile-time'),
        sunrise: document.getElementById('sunrise'),
        sunset: document.getElementById('sunset'),
        curve: document.getElementById('sun-curve'),
        dayPath: document.getElementById('day-path'),
        nightPath: document.getElementById('night-path'),
        sun: document.getElementById('sun-position'),
        glow: document.getElementById('sun-glow'),
        phaseEvening: document.getElementById('phase-evening'),
        phaseNight: document.getElementById('phase-night'),
        phaseDay: document.getElementById('phase-day'),
    };

    if (!els.curve || !els.sun) return;

    const ORB_GLOW_RADIUS = parseFloat(els.glow?.getAttribute('r')) || 15.5;

    let sunriseDate = null;
    let sunsetDate = null;

    let curveParams = null;
    let curveReady = false;
    let displayT = 0.5;
    let displayIsDay = true;
    let hasPositioned = false;
    let sunAnimFrame = null;
    let curveAnimFrame = null;
    let lastSunDay = null;

    function stripLeadingZero(str) {
        return str ? str.replace(/^0(\d):/, '$1:') : str;
    }

    /** Minutes since local midnight (wall clock). */
    function localMinutes(date) {
        return date.getHours() * 60 + date.getMinutes() + date.getSeconds() / 60;
    }

    function formatTime12FromMinutes(totalMinutes) {
        const hours24 = Math.floor(totalMinutes / 60) % 24;
        const minutes = Math.floor(totalMinutes % 60);
        const ampm = hours24 >= 12 ? 'PM' : 'AM';
        const hours = hours24 % 12 || 12;
        return stripLeadingZero(`${hours}:${String(minutes).padStart(2, '0')} ${ampm}`);
    }

    function formatTime12(date) {
        return formatTime12FromMinutes(localMinutes(date));
    }

    function formatDate(date) {
        const dayName = date.toLocaleDateString('en-GB', { weekday: 'short' });
        const day = date.getDate();
        const month = date.toLocaleDateString('en-GB', { month: 'short' });
        return `${dayName} ${day} ${month}`;
    }

    function parseTimeToMinutes(str) {
        if (!str || typeof str !== 'string') return null;
        const match = str.trim().toUpperCase().match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/);
        if (!match) return null;
        let hours = parseInt(match[1], 10);
        const minutes = parseInt(match[2], 10);
        const ap = match[3];
        if (ap === 'PM' && hours < 12) hours += 12;
        if (ap === 'AM' && hours === 12) hours = 0;
        return hours * 60 + minutes;
    }

    function getPointOnCurve(t, params) {
        const { x0, y0, x1, y1, x2, y2 } = params;
        const mt = 1 - t;
        return {
            x: mt * mt * x0 + 2 * mt * t * x1 + t * t * x2,
            y: mt * mt * y0 + 2 * mt * t * y1 + t * t * y2,
        };
    }

    function applyCurvePath(params) {
        const d = `M ${params.x0.toFixed(1)} ${params.y0} Q ${params.x1.toFixed(1)} ${params.y1.toFixed(1)} ${params.x2.toFixed(1)} ${params.y2}`;
        els.dayPath?.setAttribute('d', d);
        els.nightPath?.setAttribute('d', d);
        const svg = els.curve.querySelector('svg');
        svg?.setAttribute('viewBox', `0 0 ${params.viewBoxW} ${params.h}`);
    }

    function refreshOrbPosition() {
        if (curveReady && curveParams) updateSunMoonPosition(new Date());
    }

    function updateCurveGeometry() {
        const w = els.curve.clientWidth;
        if (!w || w < 120) return;

        const h = Math.round(els.curve.clientHeight) || 52;
        const bottomPad = Math.round((h * 20) / 72);
        // Keep glow (r=15.5) inside the viewBox when the orb sits on the arc baseline.
        const yBase = Math.min(h - bottomPad, h - ORB_GLOW_RADIUS);
        const archHeight = Math.min(yBase - 4, Math.max(24, 20 + w * 0.04));
        const inset = Math.max(10, w * 0.07);
        const target = {
            x0: inset,
            x1: w / 2,
            x2: w - inset,
            y0: yBase,
            y1: yBase - archHeight,
            y2: yBase,
            viewBoxW: Math.round(w),
            h,
        };

        if (!curveReady || !curveParams) {
            applyCurvePath(target);
            curveParams = target;
            curveReady = true;
            refreshOrbPosition();
            return;
        }

        if (curveAnimFrame) cancelAnimationFrame(curveAnimFrame);
        const from = curveParams;
        const start = performance.now();

        function step(now) {
            const p = Math.min((now - start) / 310, 1);
            const e = 1 - Math.pow(1 - p, 3);
            const live = {
                x0: from.x0 + (target.x0 - from.x0) * e,
                x1: from.x1 + (target.x1 - from.x1) * e,
                x2: from.x2 + (target.x2 - from.x2) * e,
                y0: from.y0 + (target.y0 - from.y0) * e,
                y1: from.y1 + (target.y1 - from.y1) * e,
                y2: from.y2 + (target.y2 - from.y2) * e,
                viewBoxW: Math.round(from.viewBoxW + (target.viewBoxW - from.viewBoxW) * e),
                h,
            };
            applyCurvePath(live);
            curveParams = live;
            applySunPosition(displayT, displayIsDay);
            if (p < 1) curveAnimFrame = requestAnimationFrame(step);
            else {
                curveParams = target;
                applyCurvePath(target);
                refreshOrbPosition();
            }
        }

        curveAnimFrame = requestAnimationFrame(step);
    }

    function applySunPosition(t, isDay) {
        if (!curveParams || !els.sun || !els.glow) return;
        const pt = getPointOnCurve(t, curveParams);
        els.sun.setAttribute('cx', pt.x);
        els.sun.setAttribute('cy', pt.y);
        els.glow.setAttribute('cx', pt.x);
        els.glow.setAttribute('cy', pt.y);

        els.sun.classList.toggle('datetime-tile__orb--day', isDay);
        els.sun.classList.toggle('datetime-tile__orb--night', !isDay);
        els.glow.classList.toggle('datetime-tile__glow--day', isDay);
        els.glow.classList.toggle('datetime-tile__glow--night', !isDay);

        els.dayPath?.classList.toggle('is-active', isDay);
        els.dayPath?.classList.toggle('is-dim', !isDay);
        els.nightPath?.classList.toggle('is-active', !isDay);
        els.nightPath?.classList.toggle('is-dim', isDay);

        displayT = t;
        displayIsDay = isDay;
    }

    function animateSunPosition(targetT, targetIsDay) {
        if (!curveReady || !curveParams) return;

        if (sunAnimFrame) cancelAnimationFrame(sunAnimFrame);

        if (!hasPositioned || Math.abs(targetT - displayT) < 0.012 || targetIsDay !== displayIsDay) {
            applySunPosition(targetT, targetIsDay);
            hasPositioned = true;
            return;
        }

        const startT = displayT;
        const start = performance.now();

        function step(now) {
            const p = Math.min((now - start) / SUN_ANIM_MS, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            applySunPosition(startT + (targetT - startT) * eased, targetIsDay);
            if (p < 1) sunAnimFrame = requestAnimationFrame(step);
            else applySunPosition(targetT, targetIsDay);
        }

        sunAnimFrame = requestAnimationFrame(step);
        hasPositioned = true;
    }

    function updateSunMoonPosition(now) {
        if (!sunriseDate || !sunsetDate) return;

        const current = ((localMinutes(now) % DAY_MINUTES) + DAY_MINUTES) % DAY_MINUTES;
        const sunrise = localMinutes(sunriseDate);
        const sunset = localMinutes(sunsetDate);

        let targetT = 0.5;
        let targetIsDay = true;

        if (current >= sunrise && current <= sunset) {
            const dayLen = sunset - sunrise;
            targetT = dayLen > 0 ? (current - sunrise) / dayLen : 0.5;
        } else {
            targetIsDay = false;
            let nightProgress = 0;
            if (current < sunrise) {
                const prevSunset = sunset - DAY_MINUTES;
                const nightLen = sunrise - prevSunset;
                nightProgress = nightLen > 0 ? (current - prevSunset) / nightLen : 0;
            } else {
                const nextSunrise = sunrise + DAY_MINUTES;
                const nightLen = nextSunrise - sunset;
                nightProgress = nightLen > 0 ? (current - sunset) / nightLen : 0;
            }
            // Night also travels left → right: sunset (t=0) to sunrise (t=1).
            targetT = nightProgress;
        }

        animateSunPosition(Math.max(0, Math.min(1, targetT)), targetIsDay);
    }

    function computeSunTimes(date) {
        if (!window.SunMath) return;
        const noon = new Date(date);
        noon.setHours(12, 0, 0, 0);
        const times = SunMath.getTimes(noon, lat, lng);
        sunriseDate = times.sunrise;
        sunsetDate = times.sunset;
        if (els.sunrise) els.sunrise.textContent = formatTime12(sunriseDate);
        if (els.sunset) els.sunset.textContent = formatTime12(sunsetDate);
    }

    function tick() {
        const now = new Date();
        const dayKey = now.toDateString();

        if (lastSunDay !== dayKey) {
            lastSunDay = dayKey;
            computeSunTimes(now);
        }

        if (els.date) els.date.textContent = formatDate(now);
        if (els.time) els.time.textContent = formatTime12(now);
        updateSunMoonPosition(now);
    }

    function setLocation(newLat, newLng) {
        if (typeof newLat !== 'number' || typeof newLng !== 'number') return;
        lat = newLat;
        lng = newLng;
        computeSunTimes(new Date());
        tick();
        requestAnimationFrame(updateCurveGeometry);
    }

    function update(data) {
        if (!data) return;
        if (typeof data.latitude === 'number' && typeof data.longitude === 'number') {
            setLocation(data.latitude, data.longitude);
        }
        if (data.sunrise) {
            const parsed = parseTimeToMinutes(stripLeadingZero(data.sunrise));
            if (parsed !== null && els.sunrise) {
                els.sunrise.textContent = stripLeadingZero(data.sunrise);
                const base = new Date();
                base.setHours(Math.floor(parsed / 60), parsed % 60, 0, 0);
                sunriseDate = base;
            }
        }
        if (data.sunset) {
            const parsed = parseTimeToMinutes(stripLeadingZero(data.sunset));
            if (parsed !== null && els.sunset) {
                els.sunset.textContent = stripLeadingZero(data.sunset);
                const base = new Date();
                base.setHours(Math.floor(parsed / 60), parsed % 60, 0, 0);
                sunsetDate = base;
            }
        }
        if (data.evening_start && els.phaseEvening) {
            els.phaseEvening.textContent = stripLeadingZero(data.evening_start);
        }
        if (data.night_start && els.phaseNight) {
            els.phaseNight.textContent = stripLeadingZero(data.night_start);
        }
        if (data.day_start && els.phaseDay) {
            els.phaseDay.textContent = stripLeadingZero(data.day_start);
        }
        if (data.local_time) {
            const parsed = parseTimeToMinutes(data.local_time);
            if (parsed !== null) {
                const now = new Date();
                now.setHours(Math.floor(parsed / 60), parsed % 60, 0, 0);
                updateSunMoonPosition(now);
                return;
            }
        }
        tick();
    }

    async function loadPhaseTimes() {
        try {
            const res = await fetch('/api/phases', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            if (data.times) {
                updatePhaseTimes(data.times);
            }
        } catch {
            /* phases tile / socket will update */
        }
    }

    computeSunTimes(new Date());
    tick();
    loadPhaseTimes();
    setInterval(tick, 1000);

    requestAnimationFrame(() => {
        updateCurveGeometry();
        requestAnimationFrame(updateCurveGeometry);
    });

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(updateCurveGeometry, 140);
    });

    function updatePhaseTimes(times) {
        if (!times) return;
        if (times.day_start && els.phaseDay) els.phaseDay.textContent = stripLeadingZero(times.day_start);
        if (times.evening_start && els.phaseEvening) {
            els.phaseEvening.textContent = stripLeadingZero(times.evening_start);
        }
        if (times.night_start && els.phaseNight) els.phaseNight.textContent = stripLeadingZero(times.night_start);
    }

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.datetime = { updatePhaseTimes };

    window.datetimeTile = { update, setLocation, refresh: tick, updatePhaseTimes };
})();