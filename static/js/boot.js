/**
 * PCCS4 boot — reveal page after theme/CSS/fonts are ready (prevents FOUC).
 */
(function () {
    'use strict';

    const MAX_WAIT_MS = 1200;
    const FONT_WAIT_MS = 320;
    let revealed = false;

    function reveal() {
        if (revealed) return;
        revealed = true;
        document.documentElement.classList.add('theme-ready');
    }

    function whenPaintReady() {
        const fontWait =
            document.fonts && typeof document.fonts.ready !== 'undefined'
                ? document.fonts.ready
                : Promise.resolve();

        return Promise.race([
            fontWait,
            new Promise((resolve) => setTimeout(resolve, FONT_WAIT_MS)),
        ]);
    }

    function init() {
        whenPaintReady().then(() => {
            requestAnimationFrame(() => {
                requestAnimationFrame(reveal);
            });
        });
    }

    if (document.readyState === 'complete') {
        init();
    } else {
        window.addEventListener('load', init, { once: true });
    }

    setTimeout(reveal, MAX_WAIT_MS);

    window.pccs4Boot = { reveal };
})();