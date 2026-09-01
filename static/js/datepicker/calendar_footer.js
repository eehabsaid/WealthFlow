/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Popup Footer Builder
   ───────────────────────────────────────────────────────────────
   NOTE: Extracted from calendar.js to keep both files under the
   project's 200-line-per-file convention. When this file needs to
   grow further, promote it to its own package folder following the
   pattern documented in core/views/settings/__init__.py.

   Builds the popup footer: Clear, Today, Cancel, and Set buttons.
   In filter-mode pickers the footer is returned empty (selection is
   committed immediately on day click, so no confirmation is needed).
   The Clear button is omitted for required fields. "Today" always
   returns the view to "days".

   Dependencies : localization.js (_t, _isoFromDate, _today)
   Exposes      : window._WF_DP.calendarFooter
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  const { _t, _isoFromDate, _today } = window._WF_DP.loc;

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
   * Build the popup footer.
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
      picker._view = "days";
      picker._rebuildGrid();
    });

    const cancelBtn = _createBtn("wf-dp-btn-cancel", _t("dp_cancel", "Cancel"), null, () =>
      picker._close()
    );

    const setBtn = _createBtn("wf-dp-btn-set", _t("dp_set", "Set"), null, () => {
      if (picker._pendingIso) picker._commit(picker._pendingIso);
      picker._close();
    });

    footer.append(leftGroup, todayBtn, cancelBtn, setBtn);
    return footer;
  }

  window._WF_DP.calendarFooter = {
    buildFooter: _buildFooter,
  };
})();
