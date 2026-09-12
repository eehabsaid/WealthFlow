/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Event/Calendar Delegates & Destroy
   ───────────────────────────────────────────────────────────────
   Adds _selectDay, _commit, _rebuildGrid, _onDayKey, onLanguageChanged,
   and destroy to WealthFlowDatePicker.prototype.
   Split out of core.js; see core.js header for the full file map.
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  const { rebuildGrid } = window._WF_DP.calendar;
  const { selectDay, commit, onDayKey, onLanguageChanged } = window._WF_DP.events;
  const Cls = window._WF_DP.WealthFlowDatePicker;

  /* ── Delegates to events & calendar modules ───────────── */

  Cls.prototype._selectDay = function (iso) {
    selectDay(this, iso);
  };

  Cls.prototype._commit = function (iso) {
    commit(this, iso);
  };

  Cls.prototype._rebuildGrid = function () {
    rebuildGrid(this);
  };

  Cls.prototype._onDayKey = function (e, btn) {
    onDayKey(this, e, btn);
  };

  Cls.prototype.onLanguageChanged = function () {
    onLanguageChanged(this);
  };

  /* ── Destroy ─────────────────────────────────────────── */

  Cls.prototype.destroy = function () {
    this._close();
    if (this._native && this._wrap) {
      // Restore native input to its original position
      this._wrap.parentNode.insertBefore(this._native, this._wrap);
      this._wrap.remove();
      this._native.classList.remove("wf-dp-native");
      // Remove value property override
      delete this._native.value;
    }
  };
})();
