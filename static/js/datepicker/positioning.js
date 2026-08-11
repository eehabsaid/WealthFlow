/* ═══════════════════════════════════════════════════════════════
   WealthFlow Date Picker — Popup Positioning
   ───────────────────────────────────────────────────────────────
   Calculates and applies the optimal fixed position for the date
   picker popup relative to its trigger button, handling viewport
   edges (top, bottom, left, right) and the mobile full-width layout.

   Opening direction:
     • Prefers below the trigger when space allows.
     • Falls back to above when there is more room.
     • If neither side fits, uses the side with more space and
       clamps the popup within the viewport margin.
   On mobile (viewport ≤ 480 px) the popup fills the full width
   with 16 px side gutters, matching the CSS animation variant.

   Dependencies : (none — pure DOM/geometry)
   Exposes      : window._WF_DP.positioning
   ═══════════════════════════════════════════════════════════════ */

"use strict";

(function () {
  window._WF_DP = window._WF_DP || {};

  /**
   * Position the popup element relative to the trigger button.
   *
   * Adds `.wf-dp-up` to the popup when opening upward so that the CSS
   * `wf-dp-appear-up` animation plays in the correct direction.
   *
   * @param {HTMLElement} popup    The `.wf-dp-popup` element
   * @param {HTMLElement} trigger  The `.wf-dp-trigger` button
   */
  function _positionPopup(popup, trigger) {
    const rect = trigger.getBoundingClientRect();
    const popW = 300;
    const popH = popup.offsetHeight || 360;
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

    popup.classList.toggle("wf-dp-up", openUp);

    // Mobile: keep the existing full-width behavior.
    if (vw > 480) {
      popup.style.top = `${top}px`;
      popup.style.left = `${left}px`;
      popup.style.right = "";
      popup.style.width = `${popW}px`;
    } else {
      popup.style.top = `${Math.max(margin, top)}px`;
      popup.style.left = "16px";
      popup.style.right = "16px";
      popup.style.width = "auto";
    }
  }

  window._WF_DP.positioning = {
    positionPopup: _positionPopup,
  };
})();
