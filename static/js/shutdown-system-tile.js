/**
 * PCCS4 Shutdown tile — power off the host Pi and configured touchscreens.
 */
(function () {
    'use strict';

    const tile = document.getElementById('tile-shutdown-system');
    const headlineEl = document.getElementById('shutdown-summary-headline');
    const detailEl = document.getElementById('shutdown-summary-detail');
    const targetsEl = document.getElementById('shutdown-targets');
    const startBtn = document.getElementById('shutdown-start-btn');

    const dialogEl = document.getElementById('shutdown-confirm-dialog');
    const dialogTargetsEl = document.getElementById('shutdown-confirm-targets');
    const dialogTitleEl = document.getElementById('shutdown-confirm-title');
    const dialogMessageEl = document.getElementById('shutdown-confirm-message');
    const cancelBtn = document.getElementById('shutdown-confirm-cancel');
    const confirmBtn = document.getElementById('shutdown-confirm-confirm');

    if (
        !tile || !headlineEl || !detailEl || !targetsEl || !startBtn ||
        !dialogEl || !dialogTargetsEl || !dialogTitleEl || !dialogMessageEl || !cancelBtn || !confirmBtn
    ) {
        return;
    }

    const state = {
        hostname: 'PCCS Core',
        screens: [],
        shuttingDown: false,
    };

    let lastFocusedEl = null;

    function getTargetItems() {
        return [
            {
                label: state.hostname,
                detail: 'This Raspberry Pi',
                icon: 'fa-server',
            },
            ...state.screens.map((screen) => ({
                label: screen.label || screen.name,
                detail: screen.online === false ? 'May be unreachable' : 'Touchscreen',
                icon: screen.icon || 'fa-display',
                offline: screen.online === false,
            })),
        ];
    }

    function renderTargetList(container, items) {
        if (!items.length) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = items.map((item) => `
            <li class="${container === dialogTargetsEl ? 'confirm-dialog__target' : 'shutdown-system-tile__target'}${item.offline ? ' is-offline' : ''}">
                <i class="fa-solid ${item.icon} ${container === dialogTargetsEl ? 'confirm-dialog__target-icon' : 'shutdown-system-tile__target-icon'}" aria-hidden="true"></i>
                <div class="${container === dialogTargetsEl ? 'confirm-dialog__target-copy' : 'shutdown-system-tile__target-copy'}">
                    <span class="${container === dialogTargetsEl ? 'confirm-dialog__target-label' : 'shutdown-system-tile__target-label'}">${item.label}</span>
                    <span class="${container === dialogTargetsEl ? 'confirm-dialog__target-detail' : 'shutdown-system-tile__target-detail'}">${item.detail}</span>
                </div>
            </li>`).join('');
    }

    function renderTargets() {
        renderTargetList(targetsEl, getTargetItems());
    }

    function renderSummary() {
        const screenCount = state.screens.length;
        headlineEl.textContent = screenCount
            ? `Power off ${screenCount + 1} devices`
            : 'Power off PCCS Core';

        if (state.shuttingDown) {
            detailEl.textContent = 'Shutdown in progress…';
            detailEl.classList.remove('is-warning');
            return;
        }

        detailEl.textContent = screenCount
            ? 'Shuts down this Pi and all configured touchscreens.'
            : 'Shuts down this Raspberry Pi.';
        detailEl.classList.remove('is-warning');
    }

    function updateDialogCopy() {
        const screenCount = state.screens.length;
        dialogTitleEl.textContent = screenCount
            ? `Shut down ${screenCount + 1} devices?`
            : 'Shut down PCCS Core?';
        dialogMessageEl.textContent = screenCount
            ? 'This will power off the PCCS Pi and all configured touchscreens. This cannot be undone.'
            : 'This will power off this Raspberry Pi. This cannot be undone.';
        renderTargetList(dialogTargetsEl, getTargetItems());
    }

    function openDialog() {
        if (state.shuttingDown) return;

        lastFocusedEl = document.activeElement;
        updateDialogCopy();

        dialogEl.classList.remove('is-hidden');
        dialogEl.classList.add('is-visible');
        dialogEl.removeAttribute('hidden');
        dialogEl.setAttribute('aria-hidden', 'false');
        document.body.classList.add('has-confirm-dialog');

        confirmBtn.focus();
    }

    function closeDialog({ restoreFocus = true } = {}) {
        dialogEl.classList.remove('is-visible');
        dialogEl.classList.add('is-hidden');
        dialogEl.setAttribute('hidden', '');
        dialogEl.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('has-confirm-dialog');

        if (restoreFocus && lastFocusedEl && typeof lastFocusedEl.focus === 'function') {
            lastFocusedEl.focus();
        }
    }

    function setDialogBusy(busy) {
        cancelBtn.disabled = busy;
        confirmBtn.disabled = busy;
        startBtn.disabled = busy;
        tile.classList.toggle('is-shutting-down', busy);
    }

    async function loadTargets() {
        if (!window.PCCS4?.isSystemTabActive) return;

        try {
            const [coreRes, screensRes] = await Promise.all([
                fetch('/api/system', { cache: 'no-store' }),
                fetch('/api/screens', { cache: 'no-store' }),
            ]);

            if (coreRes.ok) {
                const core = await coreRes.json();
                state.hostname = core?.core?.hostname || core?.host?.hostname || state.hostname;
            }

            if (screensRes.ok) {
                const data = await screensRes.json();
                state.screens = (data.screens || []).map((screen) => ({ ...screen }));
            }
        } catch (err) {
            console.warn('[PCCS4] shutdown tile load failed', err);
        }

        renderSummary();
        renderTargets();
    }

    async function shutdownAll() {
        if (state.shuttingDown) return;

        state.shuttingDown = true;
        setDialogBusy(true);
        closeDialog({ restoreFocus: false });
        renderSummary();

        window.pccs4Toasts?.create?.({
            type: 'warning',
            title: 'Shutting down',
            message: 'Powering off all devices…',
            duration: 8000,
        });

        try {
            const res = await fetch('/api/system/shutdown', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
        } catch (err) {
            console.warn('[PCCS4] shutdown request failed', err);
            state.shuttingDown = false;
            setDialogBusy(false);
            renderSummary();
            window.pccs4Toasts?.create?.({
                type: 'error',
                title: 'Shutdown failed',
                message: 'Could not start shutdown. Check server logs.',
                duration: 6000,
            });
        }
    }

    startBtn.addEventListener('click', openDialog);
    cancelBtn.addEventListener('click', () => closeDialog());
    confirmBtn.addEventListener('click', shutdownAll);

    dialogEl.addEventListener('click', (event) => {
        if (event.target === dialogEl) {
            closeDialog();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (!dialogEl.classList.contains('is-visible')) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            closeDialog();
        }
    });

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.shutdownSystem = {
        loadTargets,
    };
})();