/**
 * PCCS4 Phases tile — schedule, day timeline, and force controls (socket-backed).
 */
(function () {
    'use strict';

    const TICK_INTERVAL_MS = 30000;
    const DAY_MINUTES = 24 * 60;

    const PHASE_ORDER = ['Day', 'Evening', 'Night'];

    const PHASE_META = {
        Day: { icon: 'fa-sun', tileClass: 'is-day', trackClass: 'phases-tile__track-segment--day' },
        Evening: { icon: 'fa-cloud-sun', tileClass: 'is-evening', trackClass: 'phases-tile__track-segment--evening' },
        Night: { icon: 'fa-moon', tileClass: 'is-night', trackClass: 'phases-tile__track-segment--night' },
    };

    const tile = document.getElementById('tile-phases');
    const els = {
        summaryIcon: document.getElementById('phases-summary-icon'),
        headline: document.getElementById('phases-headline'),
        detail: document.getElementById('phases-detail'),
        next: document.getElementById('phases-next'),
        trackBar: document.getElementById('phases-track-bar'),
        trackNow: document.getElementById('phases-track-now'),
        schedule: document.getElementById('phases-schedule'),
        clearBtn: document.getElementById('phases-clear-btn'),
        segments: document.querySelectorAll('.phases-tile__segment'),
    };

    if (!tile || !els.headline) return;

    const state = {
        times: {
            day_start: '—',
            evening_start: '—',
            night_start: '—',
        },
        forcedPhase: null,
        serverPhase: null,
    };

    function getSocket() {
        return window.PCCS4?.socket ?? null;
    }

    function stripLeadingZero(str) {
        return str ? str.replace(/^0(\d):/, '$1:') : str;
    }

    function parseTimeToMinutes(value) {
        if (!value || value === '—') return null;

        const match = String(value)
            .trim()
            .match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i);
        if (!match) return null;

        let hours = parseInt(match[1], 10);
        const minutes = parseInt(match[2], 10);
        const meridiem = match[3]?.toUpperCase();

        if (meridiem === 'PM' && hours !== 12) hours += 12;
        if (meridiem === 'AM' && hours === 12) hours = 0;

        return hours * 60 + minutes;
    }

    function formatDuration(totalMinutes) {
        const minutes = Math.max(0, Math.round(totalMinutes));
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        if (hours > 0 && mins > 0) return `${hours}h ${mins}m`;
        if (hours > 0) return `${hours}h`;
        return `${mins}m`;
    }

    function getScheduleMinutes() {
        return {
            day: parseTimeToMinutes(state.times.day_start),
            evening: parseTimeToMinutes(state.times.evening_start),
            night: parseTimeToMinutes(state.times.night_start),
        };
    }

    function resolveAutomaticPhase(now = new Date()) {
        const { day, evening, night } = getScheduleMinutes();
        const nowMinutes = now.getHours() * 60 + now.getMinutes();

        if (day === null || evening === null || night === null) {
            return 'Day';
        }

        if (nowMinutes < day || nowMinutes >= night) {
            return 'Night';
        }
        if (nowMinutes >= evening) {
            return 'Evening';
        }
        return 'Day';
    }

    function activePhase() {
        if (state.forcedPhase) return state.forcedPhase;
        if (state.serverPhase) return state.serverPhase;
        return resolveAutomaticPhase();
    }

    function nextAutomaticTransition(now = new Date()) {
        const { day, evening, night } = getScheduleMinutes();
        const nowMinutes = now.getHours() * 60 + now.getMinutes();

        if (day === null || evening === null || night === null) {
            return null;
        }

        const transitions = [
            { at: day, phase: 'Day' },
            { at: evening, phase: 'Evening' },
            { at: night, phase: 'Night' },
            { at: day + DAY_MINUTES, phase: 'Day' },
        ].sort((a, b) => a.at - b.at);

        const upcoming = transitions.find((entry) => entry.at > nowMinutes);
        if (!upcoming) {
            return { phase: 'Day', minutesUntil: (day + DAY_MINUTES) - nowMinutes };
        }

        return {
            phase: upcoming.phase,
            minutesUntil: upcoming.at - nowMinutes,
        };
    }

    function buildTrackSegments() {
        const { day, evening, night } = getScheduleMinutes();
        if (day === null || evening === null || night === null) {
            return [];
        }

        return [
            { phase: 'Night', start: 0, end: day },
            { phase: 'Day', start: day, end: evening },
            { phase: 'Evening', start: evening, end: night },
            { phase: 'Night', start: night, end: DAY_MINUTES },
        ];
    }

    function setPhaseClasses(phase) {
        tile.classList.remove('is-day', 'is-evening', 'is-night');
        const meta = PHASE_META[phase];
        if (meta?.tileClass) tile.classList.add(meta.tileClass);
    }

    function renderSummary(phase, now = new Date()) {
        const meta = PHASE_META[phase] || PHASE_META.Day;

        if (els.summaryIcon) {
            els.summaryIcon.className = `fa-solid ${meta.icon} phases-tile__summary-icon`;
        }
        if (els.headline) {
            els.headline.textContent = `${phase} phase`;
        }
        if (els.detail) {
            els.detail.textContent = state.forcedPhase ? `Forced to ${state.forcedPhase}` : 'Following schedule';
            els.detail.classList.toggle('is-forced', state.forcedPhase !== null);
        }
        if (els.next) {
            if (state.forcedPhase) {
                els.next.textContent = 'Clear force to resume automatic phases';
            } else {
                const upcoming = nextAutomaticTransition(now);
                if (upcoming) {
                    els.next.textContent = `${upcoming.phase} in ${formatDuration(upcoming.minutesUntil)}`;
                } else {
                    els.next.textContent = '';
                }
            }
        }
    }

    function renderTrack(phase, now = new Date()) {
        if (!els.trackBar || !els.trackNow) return;

        const segments = buildTrackSegments();
        if (!segments.length) {
            els.trackBar.innerHTML = '';
            els.trackNow.style.left = '0%';
            return;
        }

        els.trackBar.innerHTML = segments.map((segment) => {
            const width = ((segment.end - segment.start) / DAY_MINUTES) * 100;
            const meta = PHASE_META[segment.phase];
            const active = segment.phase === phase;
            return `
                <span class="phases-tile__track-segment ${meta.trackClass}${active ? ' is-active' : ''}"
                      style="width: ${width}%"
                      title="${segment.phase}"></span>
            `;
        }).join('');

        const nowMinutes = now.getHours() * 60 + now.getMinutes();
        const markerLeft = (nowMinutes / DAY_MINUTES) * 100;
        els.trackNow.style.left = `${markerLeft}%`;
    }

    function renderSchedule(phase) {
        if (!els.schedule) return;

        const schedule = [
            { phase: 'Day', time: stripLeadingZero(state.times.day_start) },
            { phase: 'Evening', time: stripLeadingZero(state.times.evening_start) },
            { phase: 'Night', time: stripLeadingZero(state.times.night_start) },
        ];

        els.schedule.innerHTML = schedule.map((entry) => {
            const meta = PHASE_META[entry.phase];
            const active = entry.phase === phase;
            return `
                <article class="phases-tile__card${active ? ' is-active' : ''}"
                         data-phase="${entry.phase}"
                         role="listitem"
                         aria-label="${entry.phase} starts at ${entry.time}">
                    <div class="phases-tile__card-top">
                        <i class="fa-solid ${meta.icon} phases-tile__card-icon" aria-hidden="true"></i>
                        <span class="phases-tile__card-badge">${active ? 'Now' : ''}</span>
                    </div>
                    <p class="phases-tile__card-name">${entry.phase}</p>
                    <p class="phases-tile__card-time">${entry.time}</p>
                </article>
            `;
        }).join('');
    }

    function updateForceControls() {
        els.segments.forEach((segment) => {
            const phase = segment.dataset.phase;
            segment.classList.toggle('is-selected', state.forcedPhase === phase);
            segment.setAttribute('aria-pressed', String(state.forcedPhase === phase));
        });

        if (els.clearBtn) {
            els.clearBtn.hidden = state.forcedPhase === null;
        }
    }

    function render(phase = activePhase(), now = new Date()) {
        setPhaseClasses(phase);
        renderSummary(phase, now);
        renderTrack(phase, now);
        renderSchedule(phase);
        updateForceControls();
    }

    function emitForcePhase(phase) {
        const socket = getSocket();
        if (socket?.connected) {
            socket.emit('force_phase', { phase });
        }
    }

    function forcePhase(phase) {
        state.forcedPhase = phase;
        render(phase);
        emitForcePhase(phase);
    }

    function clearForce() {
        state.forcedPhase = null;
        render(activePhase());
        const socket = getSocket();
        if (socket?.connected) {
            socket.emit('force_phase', { phase: null });
        }
    }

    function tick() {
        if (state.forcedPhase) return;
        render(activePhase());
    }

    function onPhaseUpdate(data) {
        if (!data) return;
        if (data.day_start) state.times.day_start = data.day_start;
        if (data.evening_start) state.times.evening_start = data.evening_start;
        if (data.night_start) state.times.night_start = data.night_start;
        if (data.phase) state.serverPhase = data.phase;
        render(activePhase());
        window.PCCS4?.datetime?.updatePhaseTimes?.(state.times);
    }

    function onPhaseDiagUpdate(data) {
        if (!data) return;
        if (!data.forced) {
            state.forcedPhase = null;
        } else if (state.serverPhase) {
            state.forcedPhase = state.serverPhase;
        }
        render(activePhase());
    }

    function bindControls() {
        els.segments.forEach((segment) => {
            segment.addEventListener('click', () => {
                const phase = segment.dataset.phase;
                if (!phase) return;
                forcePhase(phase);
            });
        });

        els.clearBtn?.addEventListener('click', clearForce);
    }

    async function loadPhases() {
        if (!window.PCCS4?.isSystemTabActive) return;
        try {
            const res = await fetch('/api/phases', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            onPhaseUpdate({
                phase: data.phase,
                ...data.times,
            });
            if (data.forced && data.phase) {
                onPhaseDiagUpdate({ forced: true });
            }
        } catch {
            /* socket will deliver phase_update */
        }
    }

    function tickIfActive() {
        if (!window.PCCS4?.isSystemTabActive) return;
        tick();
    }

    function init() {
        render(resolveAutomaticPhase());
        bindControls();
        setInterval(tickIfActive, TICK_INTERVAL_MS);
    }

    init();

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.phases = {
        onPhaseUpdate,
        onPhaseDiagUpdate,
        forcePhase,
        clearForce,
        refresh: loadPhases,
        getState: () => ({ ...state, phase: activePhase() }),
    };

    window.phasesTile = window.PCCS4.phases;
})();