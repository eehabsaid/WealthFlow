/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Interaction & Commit Logic
   ───────────────────────────────────────────────────────────────
   Handles day-cell selection, value commit (writes native input +
   dispatches events), keyboard navigation inside the day grid,
   and language-change popup rebuilds.

   All functions receive the picker instance as their first argument
   to access state without coupling to the core class file.

   Design contract:
     • _commit() writes via the native .value setter, which triggers
       the property intercept installed in dom.js → _syncDisplay().
     • _commit() dispatches both "input" and "change" (bubbles:true)
       on the native element — all existing addEventListener handlers
       and inline oninput/onchange attributes continue to fire.
     • _selectDay() in filter mode commits immediately; in normal mode
       it only highlights the pending date without committing.

   Dependencies : dom.js (_nativeValueDescriptor)
   Exposes      : window._WF_DP.events
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  /**
   * Handle day cell selection. In filter-mode pickers the value is committed
   * immediately and the popup is closed. In normal mode the day is highlighted
   * as pending until the user confirms with the Set button.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @param {string} iso     YYYY-MM-DD of the clicked day
   */
  function _selectDay(picker, iso) {
    picker._pendingIso = iso;
    if (picker._isFilter) {
      // Immediate commit for filter inputs
      _commit(picker, iso);
      picker._close();
      return;
    }
    // Highlight the selected day without committing yet
    if (picker._popup) {
      picker._popup.querySelectorAll(".wf-dp-day").forEach((b) => {
        b.classList.toggle("wf-dp-day-selected", b.dataset.iso === iso);
        b.setAttribute("aria-selected", String(b.dataset.iso === iso));
      });
    }
  }

  /**
   * Write the chosen ISO date to the native input and fire both `input`
   * and `change` events so every existing listener continues to work.
   *
   * Setting picker._native.value goes through our property intercept
   * (installed in dom.js) which calls _syncDisplay() automatically.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   * @param {string} iso     YYYY-MM-DD string, or "" to clear
   */
  function _commit(picker, iso) {
    // Update native input value (this will trigger our setter → _syncDisplay)
    picker._native.value = iso;
    // Dispatch events on the native input so existing handlers fire
    picker._native.dispatchEvent(new Event("input", { bubbles: true }));
    picker._native.dispatchEvent(new Event("change", { bubbles: true }));
  }

  /**
   * Keyboard navigation within the day grid.
   *
   * Arrow keys move focus between day cells (left/right ±1, up/down ±7).
   * Enter/Space selects the focused day. Tab moves naturally to footer
   * buttons. All other keys are ignored.
   *
   * @param {object}          picker  WealthFlowDatePicker instance
   * @param {KeyboardEvent}   e       The keydown event
   * @param {HTMLButtonElement} btn   The day button that received the event
   */
  function _onDayKey(picker, e, btn) {
    const allDays = Array.from(
      picker._popup ? picker._popup.querySelectorAll(".wf-dp-day:not(.wf-dp-day-empty)") : []
    );
    const idx = allDays.indexOf(btn);
    if (idx === -1) return;
    let next = null;

    if (e.key === "ArrowRight") {
      next = allDays[idx + 1] || null;
    } else if (e.key === "ArrowLeft") {
      next = allDays[idx - 1] || null;
    } else if (e.key === "ArrowDown") {
      next = allDays[idx + 7] || null;
    } else if (e.key === "ArrowUp") {
      next = allDays[idx - 7] || null;
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      picker._selectDay(btn.dataset.iso);
      return;
    } else if (e.key === "Tab") {
      // Let Tab move to footer buttons naturally
      return;
    } else {
      return;
    }

    if (next) {
      e.preventDefault();
      next.focus();
    }
  }

  /**
   * Rebuild the picker display after a language change.
   * Updates the trigger button text and, if the popup is currently open,
   * closes and re-opens it so month names and day labels refresh.
   *
   * @param {object} picker  WealthFlowDatePicker instance
   */
  function _onLanguageChanged(picker) {
    picker._syncDisplay();
    if (picker._isOpen()) {
      // Rebuild popup with new translations
      picker._close();
      picker._open();
    }
  }

  window._WF_DP.events = {
    selectDay: _selectDay,
    commit: _commit,
    onDayKey: _onDayKey,
    onLanguageChanged: _onLanguageChanged,
  };
})();
