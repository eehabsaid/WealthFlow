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

