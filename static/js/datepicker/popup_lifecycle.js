/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Popup Lifecycle
   ───────────────────────────────────────────────────────────────
   Adds _open, _close, and _position to WealthFlowDatePicker.prototype.
   Split out of core.js; see core.js header for the full file map.
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  const { _nativeValueDescriptor, _isFocusable, _focusBody } = window._WF_DP.dom;
  const { _today } = window._WF_DP.loc;
  const { positionPopup } = window._WF_DP.positioning;
  const { buildPopup } = window._WF_DP.calendar;
  const Cls = window._WF_DP.WealthFlowDatePicker;

  Cls.prototype._open = function () {
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
  };

  /**
   * Close the picker popup.
   *
   * @param {boolean} [returnFocus=true] - When true, attempt to return focus
   *   to the trigger button. Pass false when the modal itself is closing and
   *   Bootstrap will manage its own focus restoration.
   */
  Cls.prototype._close = function (returnFocus = true) {
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
  };

  /* ── Position popup ───────────────────────────────────── */

  Cls.prototype._position = function () {
    if (!this._popup) return;
    positionPopup(this._popup, this._trigger);
  };
})();
