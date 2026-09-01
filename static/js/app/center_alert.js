"use strict";

// ════════════════════════════════════════════════════════════════════════════
// CENTER ALERT — centered, responsive overlay for blocking validation errors
// (e.g. certificate balance-deduction failures). Visually matches the
// existing corner toast (same colors/border) but is centered on screen and
// scales down on small viewports via css/center_alert.css. Does not replace
// or modify showToast()/#toast-container, which are used elsewhere.
// ════════════════════════════════════════════════════════════════════════════

function showCenterAlert(msg, type = "error") {
  const container = document.getElementById("center-alert-container");
  if (!container) {
    // Fall back to the corner toast if the mount point is missing.
    if (typeof showToast === "function") showToast(msg, type);
    return;
  }

  const id = "center-alert-" + Date.now();
  const color = type === "success" ? "var(--accent-green)" : "var(--accent-red)";

  container.insertAdjacentHTML(
    "beforeend",
    `
        <div id="${id}" class="center-alert-overlay">
            <div class="center-alert-card" style="border-left:3px solid ${color}">
                <div class="center-alert-body">${msg}</div>
                <button type="button" class="center-alert-close btn-close btn-close-white"
                        aria-label="Close"></button>
            </div>
        </div>`
  );

  const overlay = document.getElementById(id);
  const dismiss = () => overlay?.remove();

  overlay.querySelector(".center-alert-close").addEventListener("click", dismiss);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) dismiss();
  });
  // No auto-dismiss: this alert blocks a required user action (fix the
  // bank/currency mapping or the balance), so it stays until the user
  // closes it themselves.
}
