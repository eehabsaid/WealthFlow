/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Day Grid Builder
   ───────────────────────────────────────────────────────────────
   NOTE: Extracted from calendar.js to keep both files under the
   project's 200-line-per-file convention. When this file needs to
   grow further, promote it to its own package folder (calendar/)
   following the pattern documented in core/views/settings/__init__.py.

   Builds the weekday abbreviation row and the day-of-month grid used
   by the "days" view of the calendar popup.

   Dependencies : localization.js (_t, _displayDate, _isoFromDate, _today)
   Exposes      : window._WF_DP.calendarDays
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  const { _t, _displayDate, _isoFromDate, _today } = window._WF_DP.loc;

  /**
   * Build the weekday header row (Su Mo Tu … Sa).
   * Labels are translated via i18n keys dp_day_sun … dp_day_sat.
   *
   * @returns {HTMLElement}
   */
  function _buildWeekdays() {
    const row = document.createElement("div");
    row.className = "wf-dp-weekdays";
    const keys = ["dp_day_sun", "dp_day_mon", "dp_day_tue", "dp_day_wed", "dp_day_thu", "dp_day_fri", "dp_day_sat"];
    const fallbacks = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
    keys.forEach((k, i) => {
      const cell = document.createElement("div");
      cell.className = "wf-dp-weekday";
      cell.textContent = _t(k, fallbacks[i]);
      row.appendChild(cell);
    });
    return row;
  }

  /**
   * Build the day grid container and populate it via _fillDays().
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @returns {HTMLElement}
   */
  function _buildDays(picker) {
    const grid = document.createElement("div");
    grid.className = "wf-dp-days";
    grid.setAttribute("role", "grid");
    _fillDays(grid, picker);
    return grid;
  }

  /**
   * Populate (or re-populate) a day grid element for the picker's current
   * view month/year. Renders empty spacer cells before the first day of the
   * month, then one button per calendar day.
   *
   * @param {HTMLElement} grid    The `.wf-dp-days` container to fill
   * @param {object}      picker  WealthFlowDatePicker instance
   */
  function _fillDays(grid, picker) {
    grid.innerHTML = "";
    const y = picker._viewYear;
    const m = picker._viewMonth;
    const firstDay = new Date(y, m, 1).getDay(); // 0=Sun
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    const todayIso = _isoFromDate(_today());

    // Empty cells before first day
    for (let i = 0; i < firstDay; i++) {
      const empty = document.createElement("button");
      empty.type = "button";
      empty.className = "wf-dp-day wf-dp-day-empty";
      empty.setAttribute("aria-hidden", "true");
      empty.tabIndex = -1;
      grid.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const iso = `${y}-${String(m + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "wf-dp-day";
      btn.textContent = String(day);
      btn.dataset.iso = iso;
      btn.setAttribute("role", "gridcell");
      btn.setAttribute("aria-label", _displayDate(iso));
      btn.setAttribute("aria-selected", String(iso === picker._pendingIso));

      if (iso === todayIso) btn.classList.add("wf-dp-day-today");
      if (iso === picker._pendingIso) btn.classList.add("wf-dp-day-selected");

      btn.addEventListener("click", () => picker._selectDay(iso));
      btn.addEventListener("keydown", (e) => picker._onDayKey(e, btn));

      grid.appendChild(btn);
    }
  }

  window._WF_DP.calendarDays = {
    buildWeekdays: _buildWeekdays,
    buildDays: _buildDays,
    fillDays: _fillDays,
  };
})();
