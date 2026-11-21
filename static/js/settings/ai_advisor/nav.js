"use strict";
// AI Advisor settings: section navigation. The page shows one section at a time; a tab bar under the title (the app
// already has a sidebar; tabs that do not fit move into a "More" menu, see nav_overflow.js) switches between them. Every section stays in the DOM, so Save reads all fields.
// Layout only: no setting id, value or save logic is touched here.

window.AIA = window.AIA || {};

// The monthly-limits panel is not a settings group (it has its own Save buttons), so it is a nav entry of its own,
// shown only once the sysadmin panel has loaded.
window.AIA.ui.LIMITS_NAV = ["limits", "bi-speedometer2", "ai_grp_limits", "Usage limits"];

window.AIA.ui.chips = function () {
  const items = window.AIA.ui.GROUPS.concat([window.AIA.ui.LIMITS_NAV])
    .map(
      ([id, icon, key, fallback], idx) =>
        `<button type="button" class="aia-chip" role="tab" aria-selected="false" data-aia-idx="${idx}" data-aia-target="${id}"${id === "limits" ? " hidden" : ""}>
          <i class="bi ${icon}" aria-hidden="true"></i><span data-i18n="${key}">${t(key, fallback)}</span>
        </button>`
    )
    .join("");
  const more = `<div class="aia-more" hidden>
      <button type="button" class="aia-more-btn" aria-haspopup="true" aria-expanded="false">
        <span data-i18n="financial_advisor_tab_more">${t("financial_advisor_tab_more", "More")}</span><i class="bi bi-chevron-down" aria-hidden="true"></i>
      </button>
      <div class="aia-more-menu"></div>
    </div>`;
  return `<nav class="aia-chips" id="aiaChips" role="tablist" aria-label="${escapeHtml(t("ai_grp_nav", "Sections"))}">${items}${more}</nav>`;
};

// Shows one section and marks its nav entry; returns false for an unknown id.
window.AIA.ui.showGroup = function (id) {
  const target = document.querySelector(`[data-aia-group="${id}"]`);
  if (!target) return false;
  document.querySelectorAll("[data-aia-group]").forEach((pane) => {
    pane.hidden = pane !== target;
  });
  document.querySelectorAll(".aia-chip").forEach((chip) => {
    const on = chip.dataset.aiaTarget === id;
    chip.classList.toggle("active", on);
    chip.setAttribute("aria-selected", on ? "true" : "false");
  });
  window.AIA.state.activeGroup = id;
  if (window.AIA.ui.syncMoreActive) window.AIA.ui.syncMoreActive();
  return true;
};

// Reveals the "Usage limits" entry once the sysadmin panel has content; falls back to the first section otherwise.
window.AIA.ui.syncLimitsNav = function () {
  const loaded = !!document.getElementById("aiUserLimitsCard");
  const chip = document.querySelector('.aia-chip[data-aia-target="limits"]');
  if (chip) chip.hidden = !loaded;
  window.AIA.ui.layoutTabs();
  if (!loaded && window.AIA.state.activeGroup === "limits") window.AIA.ui.showGroup("provider");
};

window.AIA.ui.wireChips = function () {
  const nav = document.getElementById("aiaChips");
  if (!nav) return;
  const open = (chip) => {
    if (!window.AIA.ui.showGroup(chip.dataset.aiaTarget)) return;
    window.AIA.ui.closeMore();
    const detail = document.getElementById("aiaDetail");
    if (detail && detail.getBoundingClientRect().top < 0) detail.scrollIntoView({ block: "start" });
  };
  window.AIA.ui.wireMore(nav);
  nav.addEventListener("click", (e) => {
    const chip = e.target.closest(".aia-chip");
    if (chip) open(chip);
  });
  nav.addEventListener("keydown", (e) => {
    const rtl = getComputedStyle(nav).direction === "rtl"; // the tabs mirror in RTL, so do the arrow keys
    const step = { ArrowDown: 1, ArrowRight: rtl ? -1 : 1, ArrowUp: -1, ArrowLeft: rtl ? 1 : -1 }[
      e.key
    ];
    if (!step) return;
    const chips = [...nav.querySelectorAll(":scope > .aia-chip:not([hidden])")]; // the tabs in the bar, not the More menu
    const next = chips[chips.indexOf(document.activeElement) + step];
    if (!next) return;
    e.preventDefault();
    next.focus();
    open(next);
  });
};
