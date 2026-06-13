/**
 * PCCS4 System tab — Wi-Fi scanner and connector.
 */
(function () {
    'use strict';

    const POLL_INTERVAL_MS = 15000;

    const listEl = document.getElementById('wifi-network-list');
    const headlineEl = document.getElementById('wifi-summary-headline');
    const detailEl = document.getElementById('wifi-summary-detail');
    const scanBtn = document.getElementById('wifi-scan-btn');
    const connectForm = document.getElementById('wifi-connect-form');
    const connectTargetEl = document.getElementById('wifi-connect-target');
    const passwordField = document.getElementById('wifi-password-field');
    const passwordInput = document.getElementById('wifi-connect-password');
    const connectCancelBtn = document.getElementById('wifi-connect-cancel');
    const connectSubmitBtn = document.getElementById('wifi-connect-submit');

    if (!listEl || !headlineEl || !detailEl || !scanBtn) return;

    const state = {
        status: null,
        networks: [],
        selected: null,
        scanning: false,
        connecting: false,
    };

    function notifyToast(type, title, message, duration = 5500) {
        window.pccs4Toasts?.create?.({ type, title, message, duration });
    }

    function signalClass(signal) {
        if (signal >= 75) return 'is-strong';
        if (signal >= 55) return 'is-good';
        if (signal >= 35) return 'is-fair';
        return 'is-weak';
    }

    function signalBars(signal) {
        const bars = signal >= 75 ? 4 : signal >= 55 ? 3 : signal >= 35 ? 2 : signal > 0 ? 1 : 0;
        return [1, 2, 3, 4].map((bar) => (
            `<span class="${bar <= bars ? 'is-on' : ''}"></span>`
        )).join('');
    }

    function networkMeta(network) {
        const parts = [];
        if (network.security) parts.push(network.security);
        if (network.band) parts.push(network.band);
        if (network.saved) parts.push('Saved');
        return parts.join(' · ') || 'Unknown security';
    }

    function renderSummary() {
        const status = state.status;
        if (!status) {
            headlineEl.textContent = 'Checking Wi‑Fi…';
            detailEl.textContent = '';
            detailEl.classList.remove('is-warning');
            return;
        }

        if (!status.available) {
            headlineEl.textContent = 'Wi‑Fi unavailable';
            detailEl.textContent = status.error || 'No wireless interface detected';
            detailEl.classList.add('is-warning');
            return;
        }

        if (status.connected && status.ssid) {
            const signal = status.signal != null ? `${status.signal}%` : '—';
            const ip = status.ip || 'No IP';
            headlineEl.textContent = `Connected to ${status.ssid}`;
            detailEl.textContent = `${signal} · ${ip} · ${status.iface || 'wlan0'}`;
            detailEl.classList.toggle('is-warning', false);
            return;
        }

        headlineEl.textContent = 'Not connected';
        detailEl.textContent = `${state.networks.length} network${state.networks.length === 1 ? '' : 's'} nearby · ${status.iface || 'wlan0'}`;
        detailEl.classList.toggle('is-warning', state.networks.length === 0);
    }

    function renderNetworks() {
        if (!state.networks.length) {
            listEl.innerHTML = '<p class="wifi-system-tile__empty">No networks found. Tap Scan to refresh.</p>';
            return;
        }

        listEl.innerHTML = state.networks.map((network) => {
            const modifiers = [
                signalClass(network.signal),
                network.in_use ? 'is-connected' : '',
                state.selected?.ssid === network.ssid ? 'is-active' : '',
            ].filter(Boolean).join(' ');

            const icon = network.in_use ? 'fa-circle-check' : network.secured ? 'fa-lock' : 'fa-wifi';

            const isSelected = state.selected?.ssid === network.ssid;

            return `
                <button type="button"
                        class="wifi-system-tile__network ${modifiers}"
                        data-wifi-ssid="${encodeURIComponent(network.ssid)}"
                        ${state.connecting ? 'disabled' : ''}
                        role="listitem"
                        aria-pressed="${isSelected ? 'true' : 'false'}"
                        aria-label="${network.ssid}, ${network.signal} percent">
                    <div class="wifi-system-tile__network-main">
                        <i class="fa-solid ${icon} wifi-system-tile__network-icon" aria-hidden="true"></i>
                        <div>
                            <p class="wifi-system-tile__network-name">${network.ssid}</p>
                            <p class="wifi-system-tile__network-meta">${networkMeta(network)}</p>
                        </div>
                    </div>
                    <div class="wifi-system-tile__signal">
                        <span class="wifi-system-tile__signal-bars" aria-hidden="true">${signalBars(network.signal)}</span>
                        <span>${network.signal}%</span>
                    </div>
                </button>
            `;
        }).join('');
    }

    function hideConnectForm() {
        state.selected = null;
        if (!connectForm) return;
        connectForm.hidden = true;
        if (passwordInput) passwordInput.value = '';
        renderNetworks();
    }

    function showConnectForm(network) {
        if (!connectForm || !connectTargetEl) return false;

        state.selected = network;
        connectForm.hidden = false;
        connectTargetEl.textContent = network.in_use
            ? `Reconnect to ${network.ssid}`
            : `Connect to ${network.ssid}`;

        const needsPassword = network.secured && !network.saved && !network.in_use;
        if (passwordField) {
            passwordField.hidden = !needsPassword;
        }
        if (passwordInput) {
            passwordInput.required = needsPassword;
            passwordInput.value = '';
            passwordInput.placeholder = needsPassword ? 'Network password' : 'Optional for saved/open networks';
        }

        renderNetworks();
        return needsPassword;
    }

    function applyStatus(payload) {
        state.status = payload;
        state.networks = Array.isArray(payload.networks) ? payload.networks : [];
        renderSummary();
        renderNetworks();
    }

    async function fetchStatus() {
        const response = await fetch('/api/wifi');
        if (!response.ok) throw new Error('Wi-Fi status unavailable');
        return response.json();
    }

    async function refresh({ quiet = false } = {}) {
        if (!window.PCCS4?.isSystemTabActive) return;
        try {
            const payload = await fetchStatus();
            applyStatus(payload);
            if (!quiet && payload.scan_warning) {
                notifyToast('warning', 'Wi-Fi scan', payload.scan_warning, 5000);
            }
        } catch (error) {
            headlineEl.textContent = 'Wi‑Fi unavailable';
            detailEl.textContent = error.message || 'Could not load Wi-Fi status';
            detailEl.classList.add('is-warning');
        }
    }

    async function scanNetworks() {
        if (state.scanning) return;

        state.scanning = true;
        scanBtn.disabled = true;
        scanBtn.classList.add('is-spinning');

        try {
            const response = await fetch('/api/wifi/scan', { method: 'POST' });
            const payload = await response.json();
            if (Array.isArray(payload.networks)) {
                state.networks = payload.networks;
                if (state.status) {
                    state.status = { ...state.status, networks: payload.networks };
                }
            }

            renderSummary();
            renderNetworks();

            if (!payload.ok) {
                notifyToast('warning', 'Wi-Fi scan', payload.error || 'Scan did not find any networks', 5000);
            } else if (payload.warning) {
                notifyToast('info', 'Wi-Fi scan', payload.warning, 4500);
            }
        } catch (error) {
            notifyToast('error', 'Wi-Fi scan', error.message || 'Scan failed');
        } finally {
            state.scanning = false;
            scanBtn.disabled = false;
            scanBtn.classList.remove('is-spinning');
        }
    }

    async function connectToSelected(password) {
        if (!state.selected || state.connecting) return;

        state.connecting = true;
        if (connectSubmitBtn) connectSubmitBtn.disabled = true;
        if (connectCancelBtn) connectCancelBtn.disabled = true;
        renderNetworks();

        try {
            const response = await fetch('/api/wifi/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ssid: state.selected.ssid,
                    password: password || null,
                }),
            });
            const payload = await response.json();

            if (payload.status) {
                applyStatus(payload.status);
            } else {
                await refresh({ quiet: true });
            }

            if (payload.ok) {
                const ssid = state.selected?.ssid || payload.status?.ssid || 'network';
                hideConnectForm();
                notifyToast('success', 'Wi-Fi', payload.message || `Connected to ${ssid}`);
            } else {
                notifyToast('error', 'Wi-Fi', payload.error || 'Connection failed');
            }
        } catch (error) {
            notifyToast('error', 'Wi-Fi', error.message || 'Connection failed');
        } finally {
            state.connecting = false;
            if (connectSubmitBtn) connectSubmitBtn.disabled = false;
            if (connectCancelBtn) connectCancelBtn.disabled = false;
            renderNetworks();
        }
    }

    function getNetworkFromButton(button) {
        const encoded = button.dataset.wifiSsid;
        if (!encoded) return null;
        const ssid = decodeURIComponent(encoded);
        return state.networks.find((network) => network.ssid === ssid) || null;
    }

    listEl.addEventListener('click', (event) => {
        const button = event.target.closest('[data-wifi-ssid]');
        if (!button) return;

        const network = getNetworkFromButton(button);
        if (!network) return;

        const needsPassword = showConnectForm(network);
        if (needsPassword && passwordInput) {
            passwordInput.focus();
        } else {
            connectSubmitBtn?.focus();
        }
    });

    scanBtn.addEventListener('click', () => {
        scanNetworks();
    });

    connectCancelBtn?.addEventListener('click', () => {
        hideConnectForm();
    });

    connectForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        connectToSelected(passwordInput?.value || '');
    });

    window.setInterval(() => {
        if (!window.PCCS4?.isSystemTabActive) return;
        refresh({ quiet: true });
    }, POLL_INTERVAL_MS);

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.wifi = { refresh };
})();