"use strict";

// Overview tab — pure render helpers (loading/error states, formatters,
// badges). Split out of overview_render.js (200-line backlog). Bare globals
// — called directly by overview.js and overview_cards.js.
// ════════════════════════════════════════════════════════════════════════════

"use strict";

function _renderOverviewLoading() {
  const container = document.getElementById("fa-overview-content");
  if (!container) return;

  container.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary); text-align:center;">
        <div class="spinner-border spinner-border-sm me-2" role="status" style="color:var(--accent-primary);"></div>
        <span data-i18n="cash_flow_loading">Loading...</span>
      </div>
    </div>
  `;
  applyTranslations();
}

function _renderOverviewError() {
  const container = document.getElementById("fa-overview-content");
  if (!container) return;

  container.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="cash_flow_error">Unable to load overview dashboard.</span>
    </div>
  `;
  applyTranslations();
}

function _categoryColor(key) {
  const colors = {
    cash: "var(--accent-green)",
    certificates: "#8c7cf0",
    gold: "var(--accent-yellow)",
    real_estate: "#3ddc84",
    vehicles: "#5da9ff",
    other_assets: "#b178ff",
  };
  return colors[key] || "var(--accent-primary)";
}

function _formatOverviewAiSummary(execSummary) {
  if (!execSummary || !execSummary.recommendation_paragraphs) return "";

  // Render list of paragraphs with spacing
  return execSummary.recommendation_paragraphs
    .map((p) => {
      let text = t(p.key, p.fallback);
      if (p.params) {
        for (const [k, v] of Object.entries(p.params)) {
          if (k === "asset_class_key") {
            text = text.replace("{asset_class}", t(v, v));
          } else if (k === "amount") {
            text = text.replace(`{${k}}`, _money(v));
          } else {
            text = text.replace(`{${k}}`, fmt(v));
          }
        }
      }
      return `<p class="mb-2" style="margin-bottom:8px !important; line-height: 1.6; color: var(--text-secondary);">${_escapeHtml(text)}</p>`;
    })
    .join("");
}

function _formatGoalDate(dateStr) {
  if (!dateStr) return "";
  return formatDate(dateStr);
}

function _alertBadge(severity) {
  const badgeClasses = {
    danger: "bg-danger text-white",
    warning: "bg-warning text-dark",
    info: "bg-info text-dark",
    success: "bg-success text-white",
  };
  const labelKey = `portfolio_optimizer_severity_${severity}`;
  const fallback = severity.toUpperCase();
  return `<span class="badge ${badgeClasses[severity] || "bg-secondary"} ms-2" style="font-size:8px; padding: 4px 6px; letter-spacing: 0.5px; vertical-align: middle; flex-shrink: 0;">${t(labelKey, fallback)}</span>`;
}

window._renderOverviewLoading = _renderOverviewLoading;
window._renderOverviewError = _renderOverviewError;
window._categoryColor = _categoryColor;
window._formatOverviewAiSummary = _formatOverviewAiSummary;
window._formatGoalDate = _formatGoalDate;
window._alertBadge = _alertBadge;
