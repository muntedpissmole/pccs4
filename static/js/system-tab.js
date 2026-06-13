/**
 * PCCS4 System tab — lazy load and refresh when the section becomes active.
 */
(function () {
    'use strict';

    const SECTION_ID = 'system';

    window.PCCS4 = window.PCCS4 || {};
    window.PCCS4.isSystemTabActive = false;

    function isSystemSectionActive() {
        const section = document.getElementById(SECTION_ID);
        return Boolean(
            section &&
            !section.hidden &&
            section.classList.contains('active')
        );
    }

    function refreshSystemTiles() {
        window.pccsCoreTile?.refresh?.();
        window.PCCS4.phases?.refresh?.();
        window.PCCS4.gpsStatus?.refresh?.();
        window.PCCS4.explain?.refresh?.();
        window.PCCS4.reedsSystem?.refresh?.();
        window.PCCS4.screensSystem?.loadScreens?.();
        window.PCCS4.shutdownSystem?.loadTargets?.();
        window.PCCS4.wifi?.refresh?.({ quiet: true });
        window.sonosSystemTile?.fetchStatus?.();
    }

    function onSectionChange(sectionId) {
        const active = sectionId === SECTION_ID;
        window.PCCS4.isSystemTabActive = active;
        if (active) {
            refreshSystemTiles();
        }
    }

    document.addEventListener('pccs4:section-change', (event) => {
        onSectionChange(event.detail?.sectionId);
    });

    if (isSystemSectionActive()) {
        onSectionChange(SECTION_ID);
    }
})();