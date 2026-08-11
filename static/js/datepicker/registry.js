/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Registry & Observer
   ───────────────────────────────────────────────────────────────
   Manages the instance Map registry, automatic element upgrading,
   document scanning, MutationObserver for dynamic inputs, and DOM
   readiness event handling.

   Dependencies : core.js (WealthFlowDatePicker class)
   Exposes      : window._WF_DP.registry
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  /** @type {Map<HTMLInputElement, object>} */
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
    const WealthFlowDatePicker = window._WF_DP.WealthFlowDatePicker;
    if (!WealthFlowDatePicker) return;
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

  function _getInstance(input) {
    return _registry.get(input);
  }

  window._WF_DP.registry = {
    registry: _registry,
    closeAll: _closeAll,
    upgrade: _upgrade,
    scanAndUpgrade: _scanAndUpgrade,
    getInstance: _getInstance,
    init: _init,
  };
})();
