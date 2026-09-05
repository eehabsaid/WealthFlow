"use strict";

/**
 * AI Workspace — Application Modules chip source.
 *
 * Derives the "Application Modules" chip list directly from the live
 * sidebar (#sidebar .nav-item) instead of a hardcoded array. Any module
 * added to, removed from, or hidden (permission-gated) in the sidebar is
 * reflected here automatically — no changes needed in this file or in
 * ai_context_panel.js when the app's navigation changes.
 *
 * Depends on: sidebar.js (renderSidebar must have run at least once).
 */
function _getApplicationModuleChips() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return [];

  const chips = [];
  const seen = new Set();

  sidebar.querySelectorAll(".nav-item").forEach((item) => {
    // "welcome" is the logged-out/onboarding entry, not an app module.
    if (item.dataset.route === "welcome") return;

    const label = item.querySelector("[data-i18n]");
    if (!label) return;

    const i18nKey = label.getAttribute("data-i18n");
    if (seen.has(i18nKey)) return;
    seen.add(i18nKey);

    chips.push({ i18nKey, text: label.textContent.trim() });
  });

  return chips;
}

window._getApplicationModuleChips = _getApplicationModuleChips;
