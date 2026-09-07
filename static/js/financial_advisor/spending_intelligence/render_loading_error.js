"use strict";
// Loading/error placeholder renderers.
// Part of the financial_advisor module (split from the former monolithic
// spending_intelligence.js, 200-line rule). Do not edit directly.

function _renderSpendingIntelligenceLoading() {
  const pane = document.getElementById("fa-pane-spending-intelligence");
  if (!pane) return;
  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="spending_intelligence_loading"></div>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

function _renderSpendingIntelligenceError() {
  const pane = document.getElementById("fa-pane-spending-intelligence");
  if (!pane) return;
  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="spending_intelligence_error"></span>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

