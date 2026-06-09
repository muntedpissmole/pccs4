/**
 * PCCS4 Theme Manager
 * Applies visual themes and syncs selection across clients via Socket.IO.
 */
(function () {
    'use strict';

    const THEME_PATH = '/static/css/themes/';
    const STORAGE_KEY = 'pccs4-theme';
    const DEFAULT_THEME = 'neuglass';

    let themes = [
        { id: 'neuglass', label: 'Neuglass' },
        { id: 'minimal', label: 'Minimal' },
    ];

    function getSocket() {
        return window.PCCS4?.socket ?? null;
    }

    function themeIds() {
        return themes.map((theme) => theme.id);
    }

    function getStoredTheme() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored && themeIds().includes(stored)) {
                return stored;
            }
            return DEFAULT_THEME;
        } catch {
            return DEFAULT_THEME;
        }
    }

    function populateSelects(selectedTheme) {
        document.querySelectorAll('[data-theme-select]').forEach((select) => {
            const currentValue = select.value;
            select.innerHTML = '';
            themes.forEach((theme) => {
                const option = document.createElement('option');
                option.value = theme.id;
                option.textContent = theme.label;
                select.appendChild(option);
            });
            select.value = themeIds().includes(selectedTheme)
                ? selectedTheme
                : (themeIds().includes(currentValue) ? currentValue : DEFAULT_THEME);
        });
    }

    function applyTheme(themeName, { persist = true, broadcast = false } = {}) {
        const name = themeIds().includes(themeName) ? themeName : DEFAULT_THEME;

        document.documentElement.setAttribute('data-theme', name);
        document.querySelectorAll('link[data-theme-link]').forEach((link) => link.remove());

        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `${THEME_PATH}${name}.css`;
        link.dataset.themeLink = 'true';
        document.head.appendChild(link);

        populateSelects(name);

        if (persist) {
            try {
                localStorage.setItem(STORAGE_KEY, name);
            } catch {
                /* ignore quota / private browsing */
            }
        }

        if (broadcast) {
            const socket = getSocket();
            if (socket?.connected) {
                socket.emit('set_global_theme', { theme: name });
            }
        }
    }

    function applyFromServer(data) {
        if (!data?.theme) return;
        applyTheme(data.theme, { persist: true, broadcast: false });
    }

    async function loadThemes() {
        try {
            const res = await fetch('/api/themes', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            if (!Array.isArray(data.themes) || !data.themes.length) return;
            themes = data.themes.map((theme) => ({
                id: theme.file,
                label: theme.name || theme.file,
            }));
        } catch {
            /* keep built-in fallback list */
        }
    }

    async function loadCurrentTheme() {
        try {
            const res = await fetch('/api/current-theme', { cache: 'no-store' });
            if (!res.ok) return getStoredTheme();
            const data = await res.json();
            return data.theme || getStoredTheme();
        } catch {
            return getStoredTheme();
        }
    }

    function bindThemeSelects() {
        document.querySelectorAll('[data-theme-select]').forEach((select) => {
            select.addEventListener('change', () => {
                applyTheme(select.value, { persist: true, broadcast: true });
            });
        });
    }

    function registerSocket(socket) {
        if (!socket) return;
        socket.on('global_theme_update', applyFromServer);
    }

    async function init() {
        await loadThemes();
        const theme = await loadCurrentTheme();
        populateSelects(theme);
        applyTheme(theme, { persist: true, broadcast: false });
        bindThemeSelects();

        const socket = getSocket();
        if (socket) {
            registerSocket(socket);
        } else {
            document.addEventListener('pccs4:socket-ready', (event) => {
                registerSocket(event.detail?.socket);
            }, { once: true });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.themeManager = {
        applyTheme,
        getStoredTheme,
        loadCurrentTheme,
        applyFromServer,
        registerSocket,
        themes: () => themes.slice(),
    };
})();