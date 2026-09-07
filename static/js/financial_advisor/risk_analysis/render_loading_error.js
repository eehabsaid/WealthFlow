"use strict";
window.RA = window.RA || {};

window.RA.renderRiskAnalysisLoading = function() {
  const pane = document.getElementById("fa-pane-risk-analysis");
  if (!pane) return;
  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="risk_analysis_loading"></div>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

window.RA.renderRiskAnalysisError = function() {
  const pane = document.getElementById("fa-pane-risk-analysis");
  if (!pane) return;
  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="risk_analysis_error"></span>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

