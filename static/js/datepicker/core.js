/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Core Class
   ───────────────────────────────────────────────────────────────
   Defines the main WealthFlowDatePicker class. Coordinates DOM building,
   state tracking, popup opening/closing, display syncing, and delegates
   specialized responsibilities to helper modules in window._WF_DP:
     • dom          : wrapper/trigger building, property intercepts, focus safety
     • positioning  : popup geometry calculation
     • calendar     : popup DOM building and grid rendering
     • events       : day selection, value commit, keyboard nav, language updates
     • registry     : instance tracking and global closeAll

   Split across three files (load in this order):
     • core.js            : constructor, DOM build, display sync (this file)
     • popup_lifecycle.js : open/close/position, added to the prototype
     • delegates.js       : delegate methods + destroy, added to the prototype

   Dependencies : localization.js, dom.js, positioning.js, calendar.js, events.js
   Exposes      : window._WF_DP.WealthFlowDatePicker
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  const { _t, _displayDate, _today } = window._WF_DP.loc;
  const {
    _nativeValueDescriptor,
    _isFocusable,
    _focusBody,
    buildWrapper,
    interceptValue,
    buildTrigger,
  } = window._WF_DP.dom;

  class WealthFlowDatePicker {
    /**
     * @param {HTMLInputElement} nativeInput  The original input[type="date"]
     */
    constructor(nativeInput) {
      this._native = nativeInput;
      this._popup = null;
      this._viewYear = 0;
      this._viewMonth = 0;
      this._view = "days"; // "days" (day grid) or "months" (year-jump grid)
      this._pendingIso = ""; // highlighted but not yet committed (modal mode)
      this._isFilter = false; // filter inputs: immediate commit, no Set/Cancel
      this._isReadonly = false;
      this._isRequired = nativeInput.hasAttribute("required");
      this._wrap = null;
      this._trigger = null;
      this._closeHandler = null;
      this._keyHandler = null;
      this._modalHideHandler = null;

      this._build();
    }

    /* ── Build DOM structure ──────────────────────────────── */

    _build() {
      const native = this._native;

      // Detect readonly
      this._isReadonly = native.hasAttribute("readonly") || native.hasAttribute("disabled");

      // Detect filter mode: inputs whose change fires an immediate filter function.
      // We treat those with inline oninput/onchange handlers as filter-mode.
      this._isFilter = native.hasAttribute("oninput") || native.hasAttribute("onchange");

      // Create wrapper and insert native element inside
      this._wrap = buildWrapper(native);

      // Intercept .value property so programmatic `el.value = 'YYYY-MM-DD'`
      // updates the trigger display automatically.
      interceptValue(native, () => this._syncDisplay());

      // Create trigger button — copy CSS classes from native (form-control, form-control-sm, etc.)
      const trigger = buildTrigger(native, this._isReadonly);
      this._trigger = trigger;
      this._syncDisplay();

      // Insert trigger as first child of wrap (before native input)
      this._wrap.insertBefore(trigger, native);

      if (!this._isReadonly) {
        trigger.addEventListener("click", (e) => {
          e.stopPropagation();
          this._isOpen() ? this._close() : this._open();
        });
        trigger.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            this._isOpen() ? this._close() : this._open();
          }
        });
      }
    }

    /* ── Display sync ─────────────────────────────────────── */

    _syncDisplay() {
      if (!this._trigger) return;
      const iso = _nativeValueDescriptor.get.call(this._native);
      const display = _displayDate(iso);
      const placeholder = _t("date_placeholder", "dd-mmm-yyyy");

      this._trigger.innerHTML = "";

      const textSpan = document.createElement("span");
      if (display) {
        textSpan.className = "wf-dp-value";
        textSpan.textContent = display;
      } else {
        textSpan.className = "wf-dp-placeholder";
        textSpan.textContent = placeholder;
      }
      this._trigger.appendChild(textSpan);

      const icon = document.createElement("span");
      icon.className = "wf-dp-icon bi bi-calendar3";
      icon.setAttribute("aria-hidden", "true");
      this._trigger.appendChild(icon);
    }

    /* ── Open / Close ─────────────────────────────────────── */

    _isOpen() {
      return this._popup !== null && document.body.contains(this._popup);
    }
  }

  window._WF_DP.WealthFlowDatePicker = WealthFlowDatePicker;
})();
