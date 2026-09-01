/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Calendar Popup Builder
   ───────────────────────────────────────────────────────────────
   Builds and updates the calendar popup: header (prev/next + clickable
   month/year label), body (day grid or month grid, per picker._view),
   delegating to sibling modules to stay under the 200-line convention:
     • calendar_days.js    — weekday row + day-of-month grid
     • calendar_months.js  — 12-month grid ("months" view)
     • calendar_footer.js  — Clear/Today/Cancel/Set footer

   View state (picker._view):
     • "days"   — default. Shows the day-of-month grid.
     • "months" — shown after the month/year label is clicked. Shows a
       12-month grid for _viewYear. While in this view the header's
       prev/next arrows step by whole years instead of months, so a
       distant year (e.g. 3 years ahead) is reachable in a few clicks.
       Picking a month returns to "days".

   Dependencies : localization.js (_t, _isRtl, _monthName),
                  calendar_days.js, calendar_months.js, calendar_footer.js
   Exposes      : window._WF_DP.calendar
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  const { _t, _isRtl, _monthName } = window._WF_DP.loc;

  /**
   * Build the complete popup element: header, body, and footer.
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

    const body = document.createElement("div");
    body.className = "wf-dp-body";
    _fillBody(body, picker);

    popup.append(_buildHeader(picker), body, window._WF_DP.calendarFooter.buildFooter(picker));

    return popup;
  }

  /**
   * Build the popup header row: prev/next nav buttons and the
   * month/year label. Chevron direction flips in RTL layouts so the
   * visual left-arrow always means "go back". In the "days" view the
   * label is clickable and switches to the "months" view; in the
   * "months" view the label just shows the year (nav arrows there
   * step by year, so no further click target is needed).
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @returns {HTMLElement}
   */
  function _buildHeader(picker) {
    const header = document.createElement("div");
    header.className = "wf-dp-header";
    const rtl = _isRtl();
    const isMonthsView = picker._view === "months";

    const prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.className = "wf-dp-nav-btn";
    prevBtn.setAttribute(
      "aria-label",
      isMonthsView ? _t("dp_prev_year", "Previous year") : _t("dp_prev_month", "Previous month")
    );
    prevBtn.innerHTML = rtl
      ? '<i class="bi bi-chevron-right" aria-hidden="true"></i>'
      : '<i class="bi bi-chevron-left" aria-hidden="true"></i>';
    prevBtn.addEventListener("click", () => _navigate(picker, -1));

    const nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.className = "wf-dp-nav-btn";
    nextBtn.setAttribute(
      "aria-label",
      isMonthsView ? _t("dp_next_year", "Next year") : _t("dp_next_month", "Next month")
    );
    nextBtn.innerHTML = rtl
      ? '<i class="bi bi-chevron-left" aria-hidden="true"></i>'
      : '<i class="bi bi-chevron-right" aria-hidden="true"></i>';
    nextBtn.addEventListener("click", () => _navigate(picker, 1));

    const monthYear = document.createElement("button");
    monthYear.type = "button";
    monthYear.className = "wf-dp-month-year";
    monthYear.textContent = isMonthsView ? String(picker._viewYear) : _monthYearLabel(picker);

    if (isMonthsView) {
      monthYear.disabled = true;
    } else {
      monthYear.setAttribute("aria-label", _t("dp_choose_month_year", "Choose month and year"));
      monthYear.addEventListener("click", () => {
        picker._view = "months";
        picker._rebuildGrid();
      });
    }

    if (rtl) {
      header.append(nextBtn, monthYear, prevBtn);
    } else {
      header.append(prevBtn, monthYear, nextBtn);
    }

    return header;
  }

  /**
   * Step the calendar view forward/backward. In the "months" view this
   * steps by a whole year (letting users reach a distant year quickly);
   * in the "days" view it steps by a single month as before.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @param {number} dir     -1 for previous, +1 for next
   */
  function _navigate(picker, dir) {
    if (picker._view === "months") {
      picker._viewYear += dir;
    } else {
      picker._viewMonth += dir;
      if (picker._viewMonth > 11) {
        picker._viewMonth = 0;
        picker._viewYear++;
      } else if (picker._viewMonth < 0) {
        picker._viewMonth = 11;
        picker._viewYear--;
      }
    }
    picker._rebuildGrid();
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
    return `${_monthName(picker._viewMonth)} ${picker._viewYear}`;
  }

  /**
   * Fill (or re-fill) the popup body according to the picker's current
   * view: the day grid ("days") or the month grid ("months").
   *
   * @param {HTMLElement} body    The `.wf-dp-body` container to fill
   * @param {object}      picker  WealthFlowDatePicker instance
   */
  function _fillBody(body, picker) {
    body.innerHTML = "";
    if (picker._view === "months") {
      body.appendChild(window._WF_DP.calendarMonths.buildMonths(picker));
    } else {
      const { buildWeekdays, buildDays } = window._WF_DP.calendarDays;
      body.append(buildWeekdays(), buildDays(picker));
    }
  }

  /**
   * Update an open popup's header and body to reflect the picker's
   * current view/year/month state. Called after navigation, view
   * switches (day grid <-> month grid), and the "Today" button.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   */
  function _rebuildGrid(picker) {
    if (!picker._popup) return;
    const oldHeader = picker._popup.querySelector(".wf-dp-header");
    if (oldHeader) oldHeader.replaceWith(_buildHeader(picker));
    const body = picker._popup.querySelector(".wf-dp-body");
    if (body) _fillBody(body, picker);
  }

  window._WF_DP.calendar = {
    buildPopup: _buildPopup,
    buildHeader: _buildHeader,
    monthYearLabel: _monthYearLabel,
    rebuildGrid: _rebuildGrid,
  };
})();
