/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Month Grid Builder ("months" view)
   ───────────────────────────────────────────────────────────────
   NOTE: Sibling of calendar.js / calendar_days.js, split out to keep
   each file under the project's 200-line-per-file convention. When
   this file needs to grow further, promote it to its own package
   folder following the pattern documented in core/views/settings/__init__.py.

   Builds the 12-month grid shown when the user taps the month/year
   label in the popup header. Selecting a month returns the picker to
   the "days" view for that month/year. The header's prev/next arrows
   step by whole years while this view is active (see calendar.js
   _navigate), which lets the user reach a distant year — e.g. three
   years ahead — in a handful of clicks instead of walking forward
   one month at a time.

   Dependencies : localization.js (_t, _today, _monthName)
   Exposes      : window._WF_DP.calendarMonths
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  const { _today, _monthName } = window._WF_DP.loc;

  /**
   * Build the 12-month selection grid for the picker's current _viewYear.
   * Clicking a month sets picker._viewMonth, switches the view back to
   * "days", and rebuilds the popup.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @returns {HTMLElement}
   */
  function _buildMonths(picker) {
    const grid = document.createElement("div");
    grid.className = "wf-dp-months";
    grid.setAttribute("role", "grid");

    const todayD = _today();

    for (let m = 0; m < 12; m++) {
      const label = _monthName(m);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "wf-dp-month";
      btn.textContent = label;
      btn.setAttribute("role", "gridcell");
      btn.setAttribute("aria-label", `${label} ${picker._viewYear}`);

      if (todayD.getFullYear() === picker._viewYear && todayD.getMonth() === m) {
        btn.classList.add("wf-dp-month-today");
      }
      if (m === picker._viewMonth) {
        btn.classList.add("wf-dp-month-selected");
        btn.setAttribute("aria-selected", "true");
      }

      btn.addEventListener("click", () => {
        picker._viewMonth = m;
        picker._view = "days";
        picker._rebuildGrid();
      });

      grid.appendChild(btn);
    }

    return grid;
  }

  window._WF_DP.calendarMonths = {
    buildMonths: _buildMonths,
  };
})();
