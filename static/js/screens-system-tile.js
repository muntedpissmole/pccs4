/**
 * PCCS4 Touchscreens tile — live status via REST + manual wake/sleep via Socket.IO.
 */
(function () {
    'use strict';

    const POLL_INTERVAL_MS = 30000;

    const grid = document.getElementById('screens-system-grid');
    const headlineEl = document.getElementById('screens-summary-headline');
    const detailEl = document.getElementById('screens-summary-detail');
    if (!grid || !headlineEl || !detailEl) return;

    const state = {
        screens: [],
        testing: {},
        bootstrapped: false,
    };

    function getSocket() {
        return window.PCCS4?.socket ?? null;
    }

    function getScreen(name) {
        return state.screens.find((screen) => screen.name === name);
    }

    function isTesting(name) {
        return Boolean(state.testing[name]);
    }

    function linkLabel(screen) {
        if (isTesting(screen.name)) return 'Checking…';
        if (!screen.online) {
            return screen.ssh_error ? 'SSH error' : 'Unreachable';
        }
        if (screen.on === true) return 'Awake';
        if (screen.on === false) {
            if (screen.brightness != null) return `Asleep · blank ${screen.brightness}`;
            return 'Asleep';
        }
        if (screen.latency != null) return `${screen.latency} ms`;
        return 'Connected';
    }

    function renderSummary() {
        const total = state.screens.length;
        if (!total && !state.bootstrapped) return;
        if (!total) {
            headlineEl.textContent = 'No touchscreens configured';
            detailEl.textContent = 'Add entries under [screens] in pccs.conf';
            detailEl.classList.remove('is-warning');
            return;
        }

        const online = state.screens.filter((screen) => screen.online).length;
        const awake = state.screens.filter((screen) => screen.online && screen.on).length;
        const asleep = state.screens.filter((screen) => screen.online && screen.on === false).length;

        headlineEl.textContent = `${online} of ${total} reachable · ${awake} awake · ${asleep} asleep`;

        const sshIssues = state.screens.filter(
            (screen) => screen.online && screen.ssh_passwordless === false
        ).length;
        const sshErrors = state.screens.filter((screen) => screen.ssh_error).length;

        detailEl.classList.remove('is-warning');

        if (sshErrors > 0) {
            detailEl.textContent = `${sshErrors} screen${sshErrors === 1 ? '' : 's'} need attention`;
            detailEl.classList.add('is-warning');
            return;
        }
        if (sshIssues > 0) {
            detailEl.textContent = `Remote control unavailable on ${sshIssues} screen${sshIssues === 1 ? '' : 's'}`;
            detailEl.classList.add('is-warning');
            return;
        }

        detailEl.textContent = online === total ? 'All panels responding' : 'Some panels are offline';
        detailEl.classList.toggle('is-warning', online < total);
    }

    function renderCard(screen) {
        const testing = isTesting(screen.name);
        const awake = screen.on === true;
        const asleep = screen.on === false;
        const online = screen.online;

        const modifiers = [
            online ? 'is-online' : 'is-offline',
            awake ? 'is-awake' : '',
            asleep ? 'is-asleep' : '',
            testing ? 'is-testing' : '',
        ].filter(Boolean).join(' ');

        return `
            <article class="screens-system-tile__card ${modifiers}"
                     data-screen-name="${screen.name}"
                     role="listitem"
                     aria-label="${screen.label}">
                <div class="screens-system-tile__preview" aria-hidden="true">
                    <div class="screens-system-tile__bezel">
                        <div class="screens-system-tile__face">
                            <i class="fa-solid ${screen.icon}" aria-hidden="true"></i>
                        </div>
                    </div>
                </div>

                <h3 class="screens-system-tile__title">${screen.label}</h3>

                <div class="screens-system-tile__segmented" role="group" aria-label="${screen.label} power">
                    <button type="button"
                            class="screens-system-tile__segment${awake ? ' is-selected' : ''}"
                            data-screen-action="wake"
                            aria-pressed="${awake ? 'true' : 'false'}"
                            ${!online || testing ? 'disabled' : ''}>
                        Awake
                    </button>
                    <button type="button"
                            class="screens-system-tile__segment${asleep ? ' is-selected' : ''}"
                            data-screen-action="sleep"
                            aria-pressed="${asleep ? 'true' : 'false'}"
                            ${!online || testing ? 'disabled' : ''}>
                        Sleep
                    </button>
                </div>

                <div class="screens-system-tile__footer">
                    <span class="screens-system-tile__link${online ? ' is-up' : ' is-down'}${testing ? ' is-pending' : ''}"
                          aria-live="polite">
                        <span class="screens-system-tile__link-dot" aria-hidden="true"></span>
                        <span class="screens-system-tile__link-text">${linkLabel(screen)}</span>
                    </span>
                    <button type="button"
                            class="screens-system-tile__refresh"
                            data-screen-action="test"
                            aria-label="Refresh ${screen.label}"
                            ${testing ? 'disabled' : ''}>
                        <i class="fa-solid fa-arrows-rotate${testing ? ' fa-spin' : ''}" aria-hidden="true"></i>
                    </button>
                </div>
            </article>`;
    }

    function render() {
        renderSummary();
        if (!state.screens.length) {
            grid.innerHTML = '<p class="screens-system-tile__empty">No touchscreens configured</p>';
            return;
        }
        grid.innerHTML = state.screens.map(renderCard).join('');
    }

    function mergeScreens(incoming) {
        if (!Array.isArray(incoming)) return;
        const byName = new Map(state.screens.map((screen) => [screen.name, screen]));
        incoming.forEach((screen) => {
            const prev = byName.get(screen.name) || {};
            byName.set(screen.name, { ...prev, ...screen });
        });
        state.screens = Array.from(byName.values());
        render();
    }

    function setScreenPower(name, awake) {
        const screen = getScreen(name);
        if (!screen) return;

        const socket = getSocket();
        if (!socket?.connected) {
            console.warn('[PCCS4] screen_manual_toggle skipped — socket unavailable', name);
            return;
        }

        screen.on = awake;
        render();
        socket.emit('screen_manual_toggle', { name, on: awake });
        setTimeout(() => testScreen(name), 1000);
    }

    async function refreshAll() {
        if (!window.PCCS4?.isSystemTabActive) return;
        try {
            const res = await fetch('/api/screens/status', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            mergeScreens(data.screens || []);
        } catch (err) {
            console.warn('[PCCS4] screen status fetch failed', err);
        }
    }

    async function testScreen(name) {
        const screen = getScreen(name);
        if (!screen) return;

        state.testing[name] = true;
        render();

        try {
            const res = await fetch('/api/screens/status', { cache: 'no-store' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            const updated = (data.screens || []).find((item) => item.name === name);
            if (updated) {
                Object.assign(screen, updated);
            }
        } catch (err) {
            console.warn('[PCCS4] screen test failed', name, err);
            screen.ssh_error = 'Status check failed';
        } finally {
            delete state.testing[name];
            render();
        }
    }

    grid.addEventListener('click', (event) => {
        const button = event.target.closest('[data-screen-action]');
        if (!button || button.disabled) return;

        const card = button.closest('[data-screen-name]');
        if (!card) return;

        const name = card.dataset.screenName;
        const action = button.dataset.screenAction;

        if (action === 'wake') {
            setScreenPower(name, true);
            return;
        }
        if (action === 'sleep') {
            setScreenPower(name, false);
            return;
        }
        if (action === 'test') {
            testScreen(name);
        }
    });

    window.PCCS4 = window.PCCS4 || {};
    async function loadScreens() {
        if (!window.PCCS4?.isSystemTabActive) return;
        try {
            const res = await fetch('/api/screens', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            state.screens = (data.screens || []).map((screen) => ({ ...screen }));
            state.bootstrapped = true;
            render();
            if (state.screens.length) {
                await refreshAll();
            }
        } catch (err) {
            console.warn('[PCCS4] screen config fetch failed', err);
        }
    }

    window.PCCS4.screensSystem = {
        onScreensInit(payload) {
            state.screens = (payload?.screens || []).map((screen) => ({ ...screen }));
            state.bootstrapped = true;
            render();
            refreshAll();
        },
        refresh: refreshAll,
        loadScreens,
        testScreen,
        setScreenPower,
    };

    setInterval(refreshAll, POLL_INTERVAL_MS);
})();