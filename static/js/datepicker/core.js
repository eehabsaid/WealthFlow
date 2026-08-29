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
  const { positionPopup } = window._WF_DP.positioning;
  const { buildPopup, rebuildGrid } = window._WF_DP.calendar;
  const { selectDay, commit, onDayKey, onLanguageChanged } = window._WF_DP.events;

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

    _open() {
      if (this._isReadonly) return;
      // Close any other open pickers first
      if (window._WF_DP.registry && window._WF_DP.registry.closeAll) {
        window._WF_DP.registry.closeAll(this);
      }

      const iso = _nativeValueDescriptor.get.call(this._native);
      const date = iso ? new Date(iso + "T00:00:00") : _today();
      this._viewYear = date.getFullYear();
      this._viewMonth = date.getMonth();
      this._view = "days";
      this._pendingIso = iso || "";

      this._popup = buildPopup(this);
      document.body.appendChild(this._popup);
      this._position();

      this._trigger.classList.add("wf-dp-open");
      this._trigger.setAttribute("aria-expanded", "true");

      // Outside-click handler
      this._closeHandler = (e) => {
        if (!this._popup) return;
        if (!this._popup.contains(e.target) && e.target !== this._trigger) {
          this._close();
        }
      };
      // Use capture so it fires before any inner stopPropagation
      setTimeout(() => {
        document.addEventListener("click", this._closeHandler, true);
      }, 0);

      // Keyboard handler — do NOT stopPropagation on Escape.
      // Letting it propagate allows Bootstrap modal to run its own handler too.
      this._keyHandler = (e) => {
        if (!this._popup) return;
        if (e.key === "Escape") {
          // _close() now handles all focus management internally.
          this._close(true);
        }
      };
      document.addEventListener("keydown", this._keyHandler, true);

      // Close the picker automatically if its host Bootstrap modal hides.
      // Bootstrap dispatches "hide.bs.modal" at the START of the hide animation,
      // before aria-hidden is set — giving us the correct window to close cleanly.
      // Also listen for "hidden.bs.modal" as a belt-and-suspenders fallback.
      const hostModal = this._trigger.closest(".modal");
      if (hostModal) {
        this._modalHideHandler = () => this._close(false);
        hostModal.addEventListener("hide.bs.modal", this._modalHideHandler);
        hostModal.addEventListener("hidden.bs.modal", this._modalHideHandler);
      }

      // Focus first focusable element in popup
      const firstFocusable = this._popup.querySelector(
        "button:not(:disabled), [tabindex]:not([tabindex='-1'])"
      );
      if (firstFocusable) firstFocusable.focus();
    }

    /**
     * Close the picker popup.
     *
     * @param {boolean} [returnFocus=true] - When true, attempt to return focus
     *   to the trigger button. Pass false when the modal itself is closing and
     *   Bootstrap will manage its own focus restoration.
     */
    _close(returnFocus = true) {
      if (this._popup) {
        // ── FOCUS SAFETY FIRST ──────────────────────────────────────────────
        // We must explicitly move focus BEFORE removing the popup from the DOM.
        // If we don't, the browser's natural focus-restoration picks the last
        // focused element in document order — which may be a button inside a
        // now-aria-hidden modal. That violates WAI-ARIA §6.6.3 and generates
        // a browser warning.
        if (returnFocus) {
          if (_isFocusable(this._trigger)) {
            this._trigger.focus();
          } else {
            _focusBody();
          }
        } else {
          // Modal is handling its own focus. Only intervene if the current
          // active element is already inside an unsafe container.
          const active = document.activeElement;
          if (active && !_isFocusable(active)) {
            _focusBody();
          }
        }

        this._popup.remove();
        this._popup = null;
      }
      if (this._closeHandler) {
        document.removeEventListener("click", this._closeHandler, true);
        this._closeHandler = null;
      }
      if (this._keyHandler) {
        document.removeEventListener("keydown", this._keyHandler, true);
        this._keyHandler = null;
      }
      // Remove Bootstrap modal hide listeners
      if (this._modalHideHandler) {
        const hostModal = this._trigger.closest(".modal");
        if (hostModal) {
          hostModal.removeEventListener("hide.bs.modal", this._modalHideHandler);
          hostModal.removeEventListener("hidden.bs.modal", this._modalHideHandler);
        }
        this._modalHideHandler = null;
      }
      this._trigger.classList.remove("wf-dp-open");
      this._trigger.setAttribute("aria-expanded", "false");
    }

    /* ── Position popup ───────────────────────────────────── */

    _position() {
      if (!this._popup) return;
      positionPopup(this._popup, this._trigger);
    }

    /* ── Delegates to events & calendar modules ───────────── */

    _selectDay(iso) {
      selectDay(this, iso);
    }

    _commit(iso) {
      commit(this, iso);
    }

    _rebuildGrid() {
      rebuildGrid(this);
    }

    _onDayKey(e, btn) {
      onDayKey(this, e, btn);
    }

    onLanguageChanged() {
      onLanguageChanged(this);
    }

    /* ── Destroy ─────────────────────────────────────────── */

    destroy() {
      this._close();
      if (this._native && this._wrap) {
        // Restore native input to its original position
        this._wrap.parentNode.insertBefore(this._native, this._wrap);
        this._wrap.remove();
        this._native.classList.remove("wf-dp-native");
        // Remove value property override
        delete this._native.value;
      }
    }
  }

  window._WF_DP.WealthFlowDatePicker = WealthFlowDatePicker;
})();
