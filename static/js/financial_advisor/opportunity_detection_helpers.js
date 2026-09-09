"use strict";
// Opportunity detection tab — shared state, loading/error states, and
// formatting helpers. Split out of opportunity_detection.js (200-line
// backlog). Bare globals.
// ════════════════════════════════════════════════════════════════════════════

let _opportunityDetectionLoaded = false;
let _opportunityDetectionData = null;

function _renderOpportunityDetectionLoading() {
  const pane = document.getElementById("fa-pane-opportunity-detection");
  if (!pane) return;
  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="spending_intelligence_loading"></div>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

function _renderOpportunityDetectionError() {
  const pane = document.getElementById("fa-pane-opportunity-detection");
  if (!pane) return;
  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary); border-radius:12px;">
      <span data-i18n="risk_analysis_error"></span>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

function _fmtMoneyValue(val) {
  const num = Number(val || 0);
  if (typeof fmt === "function") {
    return fmt(num.toFixed(2));
  }
  return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function _fmtIntValue(val) {
  const num = Math.round(Number(val || 0));
  if (typeof fmt === "function") {
    return fmt(num);
  }
  return num.toLocaleString("en-US");
}

function _fmtTrendPct(val) {
  const num = Number(val || 0);
  const sign = num > 0 ? "+" : "";
  return `${sign}${num.toFixed(2)}%`;
}

function _getOpportunityIconClass(key) {
  const k = String(key || "").toLowerCase();
  if (k.includes("gold")) return "bi-award-fill";
  if (k.includes("maturity") || k.includes("maturities") || k.includes("cert")) return "bi-bank2";
  if (k.includes("cash") || k.includes("idle")) return "bi-cash-stack";
  if (k.includes("vehicle")) return "bi-car-front";
  if (k.includes("emergency") || k.includes("liquidity")) return "bi-shield-check";
  return "bi-lightbulb-fill";
}
