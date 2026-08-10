/* ═══════════════════════════════════════════════════════════════
   WealthFlow Custom Date Picker
   ───────────────────────────────────────────────────────────────
   Architecture: AUGMENT (never replaces) native input[type="date"].
   The original element stays in the DOM so that:
     • All existing event listeners remain attached.
     • getElementById() returns the same element reference.
     • FormData(form) includes the field (uses visibility:hidden, not
       display:none / disabled — both of which exclude from FormData).
     • Direct .value reads/writes work unchanged via a property intercept.
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  /* ── helpers ─────────────────────────────────────────────── */

  /** @returns {string} translation string via i18n.js t() if available */
  function _t(key, fallback) {
    return typeof t === "function" ? t(key, fallback) : fallback;
  }

  /** @param {string} iso  YYYY-MM-DD or empty string
   *  @returns {string}  "dd-mmm-yyyy" using existing formatDate(), or "" */
  function _displayDate(iso) {
    if (!iso) return "";
    if (typeof formatDate === "function") return formatDate(iso);
    // Minimal fallback – should never be needed since dateFormatter.js loads first.
    const [y, m, d] = iso.split("-");
    if (!y || !m || !d) return iso;
    const abbr = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    return `${d}-${abbr[parseInt(m, 10) - 1] || m}-${y}`;
  }

  /** @param {Date} d @returns {string} YYYY-MM-DD */
  function _isoFromDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${dd}`;
  }

  /** Today's date at midnight local. @returns {Date} */
  function _today() {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }

  /** @returns {boolean} true when the page is RTL */
  function _isRtl() {
    return (
      document.documentElement.dir === "rtl" ||
      document.body.dir === "rtl" ||
      document.documentElement.lang === "ar" ||
      (typeof currentLang === "function" && currentLang() === "ar")
    );
  }

  /**
   * Read the HTMLInputElement.prototype value descriptor so we can call the
   * original getter/setter safely inside our own property override.
   */
  const _nativeValueDescriptor = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value"
  );

  /**
   * Returns true if the element can safely receive focus — i.e. none of its
   * ancestors have aria-hidden="true" and the element itself is not hidden.
   * Focusing an element inside an aria-hidden subtree triggers an
   * accessibility violation (WAI-ARIA spec §6.6.3).
   *
   * @param {Element} el
   * @returns {boolean}
   */
  function _isFocusable(el) {
    if (!el || !document.body.contains(el)) return false;
    let node = el;
    while (node && node !== document.body) {
      if (node.getAttribute("aria-hidden") === "true") return false;
      if (node.hasAttribute("inert")) return false;
      node = node.parentElement;
    }
    return true;
  }

  /* ── WealthFlowDatePicker ─────────────────────────────────── */

  class WealthFlowDatePicker {
    /**
     * @param {HTMLInputElement} nativeInput  The original input[type="date"]
     */
    constructor(nativeInput) {
      this._native = nativeInput;
      this._popup = null;
      this._viewYear = 0;
      this._viewMonth = 0;
      this._pendingIso = ""; // highlighted but not yet committed (modal mode)
      this._isFilter = false; // filter inputs: immediate commit, no Set/Cancel
      this._isReadonly = false;
      this._isRequired = nativeInput.hasAttribute("required");
      this._wrap = null;
      this._trigger = null;
      this._closeHandler = null;
      this._keyHandler = null;
      this._modalHideHandler = null;
      this._focusTrap = null;

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

      // Create wrapper
      const wrap = document.createElement("div");
      wrap.className = "wf-dp-wrap";
      // Transfer any explicit style width/height from native to wrap
      if (native.style.cssText) {
        wrap.setAttribute("style", native.style.cssText);
        native.style.cssText = "";
      }

      // Insert wrapper before native input, move native inside
      native.parentNode.insertBefore(wrap, native);
      wrap.appendChild(native);
      this._wrap = wrap;

      // Add CSS class to native to apply our hiding rules
      native.classList.add("wf-dp-native");

      // Intercept .value property so programmatic `el.value = 'YYYY-MM-DD'`
      // updates the trigger display automatically.
      const self = this;
      Object.defineProperty(native, "value", {
        get() {
          return _nativeValueDescriptor.get.call(this);
        },
        set(v) {
          _nativeValueDescriptor.set.call(this, v);
          self._syncDisplay();
        },
        configurable: true,
      });

      // Create trigger button — copy CSS classes from native (form-control, form-control-sm, etc.)
      const trigger = document.createElement("button");
      trigger.type = "button";
      trigger.className = "wf-dp-trigger";
      // Replicate sizing classes
      if (native.classList.contains("form-control-sm")) {
        trigger.classList.add("form-control-sm");
      }
      if (native.classList.contains("form-control")) {
        trigger.classList.add("form-control");
      }

      if (this._isReadonly) {
        trigger.classList.add("wf-dp-readonly");
        trigger.setAttribute("aria-disabled", "true");
        trigger.setAttribute("tabindex", "-1");
      }

      trigger.setAttribute("aria-haspopup", "dialog");
      trigger.setAttribute("aria-expanded", "false");

      // Build trigger inner HTML
      this._trigger = trigger;
      this._syncDisplay();

      // Insert trigger as first child of wrap (before native input)
      wrap.insertBefore(trigger, native);

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
      _closeAll(this);

      const iso = _nativeValueDescriptor.get.call(this._native);
      const date = iso ? new Date(iso + "T00:00:00") : _today();
      this._viewYear = date.getFullYear();
      this._viewMonth = date.getMonth();
      this._pendingIso = iso || "";

      this._popup = this._buildPopup();
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

      // Keyboard handler — note: do NOT stopPropagation on Escape.
      // Letting it propagate allows Bootstrap (or other modal managers) to
      // run their own close logic in the correct sequence.
      this._keyHandler = (e) => {
        if (!this._popup) return;
        if (e.key === "Escape") {
          this._close();
          // Only restore focus to the trigger if it is still safely focusable
          // (i.e. not inside an aria-hidden ancestor — e.g. a closing modal).
          if (_isFocusable(this._trigger)) {
            this._trigger.focus();
          }
        }
      };
      document.addEventListener("keydown", this._keyHandler, true);

      // Close the picker automatically if its host Bootstrap modal hides.
      // Bootstrap dispatches "hide.bs.modal" before setting aria-hidden.
      const hostModal = this._trigger.closest(".modal");
      if (hostModal) {
        this._modalHideHandler = () => this._close();
        hostModal.addEventListener("hide.bs.modal", this._modalHideHandler);
      }

      // Focus first focusable element in popup
      const firstFocusable = this._popup.querySelector(
        "button:not(:disabled), [tabindex]:not([tabindex='-1'])"
      );
      if (firstFocusable) firstFocusable.focus();
    }

    _close() {
      if (this._popup) {
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
      // Remove Bootstrap modal hide listener if one was registered
      if (this._modalHideHandler) {
        const hostModal = this._trigger.closest(".modal");
        if (hostModal) {
          hostModal.removeEventListener("hide.bs.modal", this._modalHideHandler);
        }
        this._modalHideHandler = null;
      }
      this._trigger.classList.remove("wf-dp-open");
      this._trigger.setAttribute("aria-expanded", "false");
    }

    /* ── Position popup ───────────────────────────────────── */

    _position() {
      if (!this._popup) return;

      const rect = this._trigger.getBoundingClientRect();
      const popW = 300;
      const popH = this._popup.offsetHeight || 360;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const margin = 8;
      const gap = 8;

      const spaceBelow = vh - rect.bottom - margin;
      const spaceAbove = rect.top - margin;

      let top;
      let left = rect.left;
      let openUp = false;

      // Prefer below when there is enough room.
      if (spaceBelow >= popH + gap) {
        top = rect.bottom + gap;
      }
      // Otherwise open above when there is enough room.
      else if (spaceAbove >= popH + gap) {
        top = rect.top - popH - gap;
        openUp = true;
      }
      // If neither side has enough room, use whichever side has more space
      // and constrain the popup inside the viewport.
      else if (spaceAbove > spaceBelow) {
        openUp = true;
        top = Math.max(margin, rect.top - popH - gap);
      } else {
        top = rect.bottom + gap;
        top = Math.min(top, vh - popH - margin);
        top = Math.max(margin, top);
      }

      // Keep the popup horizontally inside the viewport.
      if (left + popW > vw - margin) {
        left = vw - popW - margin;
      }

      if (left < margin) {
        left = margin;
      }

      this._popup.classList.toggle("wf-dp-up", openUp);

      // Mobile: keep the existing full-width behavior.
      if (vw > 480) {
        this._popup.style.top = `${top}px`;
        this._popup.style.left = `${left}px`;
        this._popup.style.right = "";
        this._popup.style.width = `${popW}px`;
      } else {
        this._popup.style.top = `${Math.max(margin, top)}px`;
        this._popup.style.left = "16px";
        this._popup.style.right = "16px";
        this._popup.style.width = "auto";
      }
    }

    /* ── Build popup ──────────────────────────────────────── */

    _buildPopup() {
      const popup = document.createElement("div");
      popup.className = "wf-dp-popup";
      popup.setAttribute("role", "dialog");
      popup.setAttribute("aria-modal", "true");
      popup.setAttribute("aria-label", _t("dp_prev_month", "Date picker calendar"));

      popup.appendChild(this._buildHeader());
      popup.appendChild(this._buildWeekdays());
      popup.appendChild(this._buildDays());
      popup.appendChild(this._buildFooter());

      return popup;
    }

    _buildHeader() {
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
        this._viewMonth--;
        if (this._viewMonth < 0) {
          this._viewMonth = 11;
          this._viewYear--;
        }
        this._rebuildGrid();
      });

      const nextBtn = document.createElement("button");
      nextBtn.type = "button";
      nextBtn.className = "wf-dp-nav-btn";
      nextBtn.setAttribute("aria-label", _t("dp_next_month", "Next month"));
      nextBtn.innerHTML = rtl
        ? '<i class="bi bi-chevron-left" aria-hidden="true"></i>'
        : '<i class="bi bi-chevron-right" aria-hidden="true"></i>';
      nextBtn.addEventListener("click", () => {
        this._viewMonth++;
        if (this._viewMonth > 11) {
          this._viewMonth = 0;
          this._viewYear++;
        }
        this._rebuildGrid();
      });

      const monthYear = document.createElement("div");
      monthYear.className = "wf-dp-month-year";
      monthYear.textContent = this._monthYearLabel();

      if (rtl) {
        header.appendChild(nextBtn);
        header.appendChild(monthYear);
        header.appendChild(prevBtn);
      } else {
        header.appendChild(prevBtn);
        header.appendChild(monthYear);
        header.appendChild(nextBtn);
      }

      return header;
    }

    _monthYearLabel() {
      // Reuse existing project-wide keys: month_january ... month_december
      const monthKeys = [
        "month_january",
        "month_february",
        "month_march",
        "month_april",
        "month_may",
        "month_june",
        "month_july",
        "month_august",
        "month_september",
        "month_october",
        "month_november",
        "month_december",
      ];
      const fallbacks = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
      ];
      const fullMonth = _t(monthKeys[this._viewMonth], fallbacks[this._viewMonth]);
      return `${fullMonth} ${this._viewYear}`;
    }

    _buildWeekdays() {
      const row = document.createElement("div");
      row.className = "wf-dp-weekdays";
      const keys = [
        "dp_day_sun",
        "dp_day_mon",
        "dp_day_tue",
        "dp_day_wed",
        "dp_day_thu",
        "dp_day_fri",
        "dp_day_sat",
      ];
      const fallbacks = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
      keys.forEach((k, i) => {
        const cell = document.createElement("div");
        cell.className = "wf-dp-weekday";
        cell.textContent = _t(k, fallbacks[i]);
        row.appendChild(cell);
      });
      return row;
    }

    _buildDays() {
      const grid = document.createElement("div");
      grid.className = "wf-dp-days";
      grid.setAttribute("role", "grid");
      this._fillDays(grid);
      return grid;
    }

    _fillDays(grid) {
      grid.innerHTML = "";
      const y = this._viewYear;
      const m = this._viewMonth;
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
        btn.setAttribute("aria-selected", String(iso === this._pendingIso));

        if (iso === todayIso) btn.classList.add("wf-dp-day-today");
        if (iso === this._pendingIso) btn.classList.add("wf-dp-day-selected");

        btn.addEventListener("click", () => this._selectDay(iso));
        btn.addEventListener("keydown", (e) => this._onDayKey(e, btn));

        grid.appendChild(btn);
      }
    }

    _buildFooter() {
      const footer = document.createElement("div");
      footer.className = "wf-dp-footer";

      if (this._isFilter) {
        // Filter mode: no footer buttons — selection is immediate in _selectDay()
        return footer;
      }

      const leftGroup = document.createElement("div");
      leftGroup.className = "wf-dp-footer-left";

      // Clear button only for optional (non-required) fields
      if (!this._isRequired) {
        const clearBtn = document.createElement("button");
        clearBtn.type = "button";
        clearBtn.className = "wf-dp-btn wf-dp-btn-clear";
        clearBtn.textContent = _t("dp_clear", "Clear");
        clearBtn.setAttribute("aria-label", _t("dp_clear", "Clear date"));
        clearBtn.addEventListener("click", () => {
          this._commit("");
          this._close();
        });
        leftGroup.appendChild(clearBtn);
      }

      const todayBtn = document.createElement("button");
      todayBtn.type = "button";
      todayBtn.className = "wf-dp-btn wf-dp-btn-today";
      todayBtn.textContent = _t("dp_today", "Today");
      todayBtn.addEventListener("click", () => {
        this._pendingIso = _isoFromDate(_today());
        this._viewYear = _today().getFullYear();
        this._viewMonth = _today().getMonth();
        this._rebuildGrid();
      });

      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.className = "wf-dp-btn wf-dp-btn-cancel";
      cancelBtn.textContent = _t("dp_cancel", "Cancel");
      cancelBtn.addEventListener("click", () => this._close());

      const setBtn = document.createElement("button");
      setBtn.type = "button";
      setBtn.className = "wf-dp-btn wf-dp-btn-set";
      setBtn.textContent = _t("dp_set", "Set");
      setBtn.addEventListener("click", () => {
        if (this._pendingIso) {
          this._commit(this._pendingIso);
        }
        this._close();
      });

      footer.appendChild(leftGroup);
      footer.appendChild(todayBtn);
      footer.appendChild(cancelBtn);
      footer.appendChild(setBtn);

      return footer;
    }

    /* ── Day selection & commit ───────────────────────────── */

    _selectDay(iso) {
      this._pendingIso = iso;
      if (this._isFilter) {
        // Immediate commit for filter inputs
        this._commit(iso);
        this._close();
        return;
      }
      // Highlight the selected day without committing yet
      if (this._popup) {
        this._popup.querySelectorAll(".wf-dp-day").forEach((b) => {
          b.classList.toggle("wf-dp-day-selected", b.dataset.iso === iso);
          b.setAttribute("aria-selected", String(b.dataset.iso === iso));
        });
      }
    }

    _commit(iso) {
      // Update native input value (this will trigger our setter → _syncDisplay)
      this._native.value = iso;
      // Dispatch events on the native input so existing handlers fire
      this._native.dispatchEvent(new Event("input", { bubbles: true }));
      this._native.dispatchEvent(new Event("change", { bubbles: true }));
    }

    /* ── Grid rebuild (after month nav or language change) ── */

    _rebuildGrid() {
      if (!this._popup) return;
      // Update month/year label
      const label = this._popup.querySelector(".wf-dp-month-year");
      if (label) label.textContent = this._monthYearLabel();
      // Rebuild day grid
      const grid = this._popup.querySelector(".wf-dp-days");
      if (grid) this._fillDays(grid);
    }

    /* ── Keyboard navigation inside the day grid ─────────── */

    _onDayKey(e, btn) {
      const allDays = Array.from(
        this._popup ? this._popup.querySelectorAll(".wf-dp-day:not(.wf-dp-day-empty)") : []
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
        this._selectDay(btn.dataset.iso);
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

    /* ── Language / theme change ─────────────────────────── */

    onLanguageChanged() {
      this._syncDisplay();
      if (this._isOpen()) {
        // Rebuild popup with new translations
        const wasOpen = true;
        this._close();
        if (wasOpen) this._open();
      }
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

  /* ── Registry & MutationObserver ─────────────────────────── */

  /** @type {Map<HTMLInputElement, WealthFlowDatePicker>} */
  const _registry = new Map();

  /** Close all open pickers except `except`. */
  function _closeAll(except) {
    _registry.forEach((picker) => {
      if (picker !== except && picker._isOpen()) picker._close();
    });
  }

  /**
   * Upgrade a single input[type="date"] element.
   * Idempotent — skips already-upgraded inputs.
   */
  function _upgrade(input) {
    if (_registry.has(input)) return;
    if (input.closest(".wf-dp-wrap")) return; // already wrapped
    const picker = new WealthFlowDatePicker(input);
    _registry.set(input, picker);
  }

  /** Scan a container for date inputs and upgrade them. */
  function _scanAndUpgrade(root) {
    const inputs = root.querySelectorAll ? root.querySelectorAll('input[type="date"]') : [];
    inputs.forEach(_upgrade);
    // Also handle the root itself if it is a date input
    if (root instanceof HTMLInputElement && root.type === "date") {
      _upgrade(root);
    }
  }

  /** MutationObserver watches the whole document for new date inputs. */
  const _observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType !== 1) return; // element nodes only
        _scanAndUpgrade(node);
      });
    });
  });

  /* ── Initialization ───────────────────────────────────────── */

  function _init() {
    // Upgrade all existing date inputs
    _scanAndUpgrade(document);

    // Watch for dynamically added inputs (modals, dynamic rows, etc.)
    _observer.observe(document.body, { childList: true, subtree: true });

    // Rebuild pickers on language change so month names / day labels update.
    window.addEventListener("languageChanged", () => {
      _registry.forEach((picker) => picker.onLanguageChanged());
    });

    // Theme changes are handled automatically by CSS variable inheritance —
    // no JS action required.
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _init);
  } else {
    _init();
  }

  /* ── Public API (optional, for testing / external control) ── */
  window.WealthFlowDatePicker = {
    /**
     * Manually upgrade all date inputs in the document.
     * Useful if inputs were added outside of MutationObserver coverage.
     */
    initAll() {
      _scanAndUpgrade(document);
    },
    /**
     * Get the WealthFlowDatePicker instance for a native input.
     * @param {HTMLInputElement} input
     * @returns {WealthFlowDatePicker|undefined}
     */
    getInstance(input) {
      return _registry.get(input);
    },
    /**
     * Close all open date picker popups.
     */
    closeAll() {
      _closeAll(null);
    },
  };
})();
