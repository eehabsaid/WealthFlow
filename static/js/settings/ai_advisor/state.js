"use strict";
// AI Financial Advisor settings panel logic (Phase 4 Multi-Provider & Security Hardening)
// Split from the former monolithic ai_advisor.js (200-line rule).

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

window.AIA = window.AIA || {};
window.AIA.state = {
  currentAISettings: null,
  currentProviderSchemas: [],
};

// Re-arms the app's shared "Show all N rows / Show less" toggle (app/utils/collapsible.js, same as Expenses)
// for a table whose rows were re-rendered: drops the stale toggle, then lets initCollapsibleTables() rebuild it.
window.AIA.resetCollapsible = function (table) {
  if (!table) return;
  table.removeAttribute("data-collapsible-init");
  const host = table.closest(".table-container") || table.parentElement;
  const toggle = host && host.nextElementSibling;
  if (toggle && toggle.classList.contains("wf-table-toggle-btn")) toggle.remove();
};
