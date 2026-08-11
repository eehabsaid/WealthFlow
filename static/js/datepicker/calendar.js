/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Calendar Popup Builder
   ───────────────────────────────────────────────────────────────
   Builds and updates all DOM elements that make up the calendar
   popup: the outer dialog, header (prev/next + month label),
   weekday abbreviation row, day grid, and action footer.

   All builder functions receive the picker instance as their first
   argument so they can read current view state (_viewYear,
   _viewMonth, _pendingIso, _isFilter, _isRequired) and call back
   into picker methods for navigation and selection.

   Design notes:
     • _buildWeekdays() is stateless — no picker argument needed.
     • Footer button callbacks call picker._commit() and picker._close()
       which are thin wrappers on the class that delegate to events.js.
     • Day button callbacks call picker._selectDay() and picker._onDayKey()
       which are also thin class wrappers.
     • _rebuildGrid() is called after month navigation (prev/next) and
       after the "Today" button is clicked.

   Dependencies : localization.js (_t, _displayDate, _isoFromDate, _today, _isRtl)
   Exposes      : window._WF_DP.calendar
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  const { _t, _displayDate, _isoFromDate, _today, _isRtl } = window._WF_DP.loc;

  /** Helper to construct a footer button concisely. */
  function _createBtn(className, text, ariaLabel, onClick) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `wf-dp-btn ${className}`;
    btn.textContent = text;
    if (ariaLabel) btn.setAttribute("aria-label", ariaLabel);
    btn.addEventListener("click", onClick);
    return btn;
  }

  /**
   * Build the complete popup element containing the header, weekday row,
   * day grid, and footer.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @returns {HTMLElement}  The `.wf-dp-popup` element ready to append to body
   */
  function _buildPopup(picker) {
    const popup = document.createElement("div");
    popup.className = "wf-dp-popup";
    popup.setAttribute("role", "dialog");
    popup.setAttribute("aria-modal", "true");
    popup.setAttribute("aria-label", _t("dp_prev_month", "Date picker calendar"));

    popup.append(
      _buildHeader(picker),
      _buildWeekdays(),
      _buildDays(picker),
      _buildFooter(picker)
    );

    return popup;
  }

  /**
   * Build the popup header row: prev-month button, month/year label,
   * and next-month button. Chevron direction flips in RTL layouts so
   * the visual left-arrow always means "previous month".
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @returns {HTMLElement}
   */
  function _buildHeader(picker) {
    const header = document.createElement("div");
    header.className = "wf-dp-header";
    const rtl = _isRtl();

    const prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.className = "wf-dp-nav-btn";
    prevBtn.setAttribute("aria-label", _t("dp_prev_month", "Previous month"));
    prevBtn.innerHTML = rtl
      ? '<i class="bi bi-chevron-right" aria-hidden="true"></i>'
      : '<i class="bi bi-chevron-left" aria-hidden="true"></i>';
    prevBtn.addEventListener("click", () => {
      picker._viewMonth--;
      if (picker._viewMonth < 0) {
        picker._viewMonth = 11;
        picker._viewYear--;
      }
      picker._rebuildGrid();
    });

    const nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.className = "wf-dp-nav-btn";
    nextBtn.setAttribute("aria-label", _t("dp_next_month", "Next month"));
    nextBtn.innerHTML = rtl
      ? '<i class="bi bi-chevron-left" aria-hidden="true"></i>'
      : '<i class="bi bi-chevron-right" aria-hidden="true"></i>';
    nextBtn.addEventListener("click", () => {
      picker._viewMonth++;
      if (picker._viewMonth > 11) {
        picker._viewMonth = 0;
        picker._viewYear++;
      }
      picker._rebuildGrid();
    });

    const monthYear = document.createElement("div");
    monthYear.className = "wf-dp-month-year";
    monthYear.textContent = _monthYearLabel(picker);

    if (rtl) {
      header.append(nextBtn, monthYear, prevBtn);
    } else {
      header.append(prevBtn, monthYear, nextBtn);
    }

    return header;
  }

  /**
   * Return the human-readable "Month YYYY" label for the current view.
   * Uses the shared month_january … month_december i18n keys so the
   * label updates automatically on language change.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @returns {string}
   */
  function _monthYearLabel(picker) {
    const monthKeys = ["month_january", "month_february", "month_march", "month_april", "month_may", "month_june", "month_july", "month_august", "month_september", "month_october", "month_november", "month_december"];
    const fallbacks = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const fullMonth = _t(monthKeys[picker._viewMonth], fallbacks[picker._viewMonth]);
    return `${fullMonth} ${picker._viewYear}`;
  }

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

  /**
   * Build the popup footer with Clear, Today, Cancel, and Set buttons.
   * In filter-mode pickers the footer is returned empty (selection is
   * committed immediately in _selectDay, so no confirmation is needed).
   * The Clear button is omitted for required fields.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @returns {HTMLElement}
   */
  function _buildFooter(picker) {
    const footer = document.createElement("div");
    footer.className = "wf-dp-footer";

    if (picker._isFilter) return footer;

    const leftGroup = document.createElement("div");
    leftGroup.className = "wf-dp-footer-left";

    // Clear button only for optional (non-required) fields
    if (!picker._isRequired) {
      leftGroup.appendChild(
        _createBtn("wf-dp-btn-clear", _t("dp_clear", "Clear"), _t("dp_clear", "Clear date"), () => {
          picker._commit("");
          picker._close();
        })
      );
    }

    const todayBtn = _createBtn("wf-dp-btn-today", _t("dp_today", "Today"), null, () => {
      picker._pendingIso = _isoFromDate(_today());
      picker._viewYear = _today().getFullYear();
      picker._viewMonth = _today().getMonth();
      picker._rebuildGrid();
    });

    const cancelBtn = _createBtn("wf-dp-btn-cancel", _t("dp_cancel", "Cancel"), null, () => picker._close());

    const setBtn = _createBtn("wf-dp-btn-set", _t("dp_set", "Set"), null, () => {
      if (picker._pendingIso) picker._commit(picker._pendingIso);
      picker._close();
    });

    footer.append(leftGroup, todayBtn, cancelBtn, setBtn);
    return footer;
  }

  /**
   * Update an open popup's month/year label and day grid to reflect a
   * change in the picker's `_viewYear` / `_viewMonth` state.
   * Called after month navigation (prev/next) and after Today is clicked.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   */
  function _rebuildGrid(picker) {
    if (!picker._popup) return;
    const label = picker._popup.querySelector(".wf-dp-month-year");
    if (label) label.textContent = _monthYearLabel(picker);
    const grid = picker._popup.querySelector(".wf-dp-days");
    if (grid) _fillDays(grid, picker);
  }

  window._WF_DP.calendar = {
    buildPopup: _buildPopup,
    buildHeader: _buildHeader,
    monthYearLabel: _monthYearLabel,
    buildWeekdays: _buildWeekdays,
    buildDays: _buildDays,
    fillDays: _fillDays,
    buildFooter: _buildFooter,
    rebuildGrid: _rebuildGrid,
  };
})();
