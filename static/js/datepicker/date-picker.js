/* ═══════════════════════════════════════════════════════════════
   WealthFlow Custom Date Picker — Public Entry Point
   ───────────────────────────────────────────────────────────────
   Architecture: AUGMENT (never replaces) native input[type="date"].
   The original element stays in the DOM so that:
     • All existing event listeners remain attached.
     • getElementById() returns the same element reference.
     • FormData(form) includes the field (uses visibility:hidden, not
       display:none / disabled — both of which exclude from FormData).
     • Direct .value reads/writes work unchanged via a property intercept.

   This file serves as the public entry point. It loads all submodules
   from window._WF_DP, initializes the registry on DOMContentLoaded,
   and exposes the public window.WealthFlowDatePicker API.
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  const dp = window._WF_DP;

  if (!dp || !dp.registry) {
    return;
  }

  const { init, scanAndUpgrade, getInstance, closeAll } = dp.registry;

  /* ── Auto-initialization ───────────────────────────────────── */

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  /* ── Public API (for testing / external control) ───────────── */

  window.WealthFlowDatePicker = {
    /**
     * Manually upgrade all date inputs in the document.
     * Useful if inputs were added outside of MutationObserver coverage.
     */
    initAll() {
      scanAndUpgrade(document);
    },

    /**
     * Get the WealthFlowDatePicker instance for a native input.
     * @param {HTMLInputElement} input
     * @returns {object|undefined}
     */
    getInstance(input) {
      return getInstance(input);
    },

    /**
     * Close all open date picker popups.
     */
    closeAll() {
      closeAll(null);
    },
  };
})();
