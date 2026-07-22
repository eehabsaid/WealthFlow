"use strict";
// Opportunity detection module
// This file is part of the financial_advisor module. Do not edit directly.

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

function _renderOpportunityDetection(payload) {
  const pane = document.getElementById("fa-pane-opportunity-detection");
  if (!pane) return;

  const count = Number(payload?.count || 0);
  const opportunities = payload?.opportunities || [];

  let html = `
    <style>
      .opp-card-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 20px;
      }
      @media (min-width: 1000px) {
        .opp-card-grid {
          grid-template-columns: repeat(2, 1fr);
        }
      }
      .opp-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 24px;
        display: flex;
        flex-direction: column;
        height: 100%;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
      }
      .opp-card:hover {
        transform: translateY(-2px);
        border-color: var(--accent-primary);
      }
      .opp-signals-table {
        width: 100%;
        margin: 16px 0;
        font-size: 13px;
      }
      .opp-signals-table td {
        padding: 6px 0;
      }
      .opp-signals-table tr:not(:last-child) td {
        border-bottom: 1px solid rgba(148, 163, 184, 0.1);
      }
      .opp-signal-label {
        color: var(--text-secondary);
      }
      .opp-signal-val {
        color: var(--text-primary);
        font-weight: 700;
        text-align: right;
      }
      [dir="rtl"] .opp-signal-val {
        text-align: left;
      }
      .opp-action-box {
        background: rgba(14, 165, 233, 0.08);
        border: 1px solid rgba(14, 165, 233, 0.25);
        border-radius: 8px;
        padding: 16px;
        font-size: 13px;
        line-height: 1.6;
        color: var(--text-primary);
        margin-top: auto;
      }
    </style>

    <!-- Hero Card -->
    <div class="card border-0 mb-4 fade-in-up" style="background:var(--bg-secondary); border:1px solid var(--border-color) !important; border-radius:12px;">
      <div class="card-body" style="padding:32px; text-align:center;">
        <div style="font-size:42px; font-weight:800; color:var(--accent-primary); line-height:1; margin-bottom:8px;">${count}</div>
        <div style="font-size:12px; font-weight:700; color:var(--text-secondary); letter-spacing:1px; text-transform:uppercase;" data-i18n="opportunities_found_label"></div>
      </div>
    </div>

    <!-- Section Title -->
    <h5 style="color:var(--text-primary); font-weight:700; margin-bottom:20px;" data-i18n="opportunities_list_title"></h5>
  `;

  if (opportunities.length === 0) {
    html += `
      <div class="card border-0 fade-in-up" style="background:var(--bg-secondary); border:1px solid var(--border-color) !important; border-radius:12px; padding:48px 24px; text-align:center;">
        <i class="bi bi-check-circle-fill" style="font-size:48px; color:var(--accent-green); margin-bottom:16px;"></i>
        <h5 style="color:var(--text-primary); font-weight:700; margin-bottom:8px;" data-i18n="opportunities_empty_state"></h5>
      </div>
    `;
  } else {
    html += `<div class="opp-card-grid">`;
    opportunities.forEach((item) => {
      const iconClass = _getOpportunityIconClass(item.key);
      const severityClass = typeof _portfolioSeverityClass === "function"
        ? _portfolioSeverityClass(item.severity)
        : (item.severity === "high" ? "portfolio-badge-high" : (item.severity === "medium" ? "portfolio-badge-medium" : "portfolio-badge-low"));

      let signalsHtml = "";
      if (item.signals) {
        if ("idle_cash" in item.signals) {
          // Gold opportunity signals
          const s = item.signals;
          const trend7Color = s.gold_trend_7d >= 0 ? "var(--accent-green)" : "var(--accent-red)";
          const trend30Color = s.gold_trend_30d >= 0 ? "var(--accent-green)" : "var(--accent-red)";
          signalsHtml = `
            <table class="opp-signals-table">
              <tr>
                <td class="opp-signal-label" data-i18n="signal_idle_cash"></td>
                <td class="opp-signal-val">${_fmtIntValue(s.idle_cash)} EGP</td>
              </tr>
              <tr>
                <td class="opp-signal-label" data-i18n="signal_gold_trend_7d"></td>
                <td class="opp-signal-val" style="color:${trend7Color};">${_fmtTrendPct(s.gold_trend_7d)}</td>
              </tr>
              <tr>
                <td class="opp-signal-label" data-i18n="signal_gold_trend_30d"></td>
                <td class="opp-signal-val" style="color:${trend30Color};">${_fmtTrendPct(s.gold_trend_30d)}</td>
              </tr>
              <tr>
                <td class="opp-signal-label" data-i18n="signal_current_allocation"></td>
                <td class="opp-signal-val">${s.current_gold_allocation_pct}% <span style="font-weight:400; color:var(--text-secondary);">(target &ge;${s.target_gold_min_pct}%)</span></td>
              </tr>
            </table>
          `;
        } else if ("maturity_date" in item.signals) {
          // Certificate maturity opportunity signals
          const s = item.signals;
          signalsHtml = `
            <table class="opp-signals-table">
              <tr>
                <td class="opp-signal-label" data-i18n="signal_maturity_date"></td>
                <td class="opp-signal-val">${s.maturity_date || "-"}</td>
              </tr>
              <tr>
                <td class="opp-signal-label" data-i18n="signal_days_left"></td>
                <td class="opp-signal-val">${s.days_left}</td>
              </tr>
              <tr>
                <td class="opp-signal-label" data-i18n="signal_maturity_amount"></td>
                <td class="opp-signal-val">${_fmtMoneyValue(s.maturity_value)} EGP</td>
              </tr>
              <tr>
                <td class="opp-signal-label" data-i18n="signal_bank"></td>
                <td class="opp-signal-val">${s.bank || "-"}</td>
              </tr>
            </table>
          `;
        }
      }

      let highlightedHtml = "";
      if (item.highlighted_amount != null && item.highlighted_amount > 0) {
        highlightedHtml = `
          <div style="font-size:28px; font-weight:800; color:var(--accent-primary); margin:12px 0 16px 0; letter-spacing:-0.5px;">
            ${_fmtIntValue(item.highlighted_amount)} <span style="font-size:16px; font-weight:600; color:var(--text-secondary);">EGP</span>
          </div>
        `;
      }

      let actionBoxHtml = "";
      if (item.action_template_key) {
        const paramsCopy = { ...(item.action_params || {}) };
        if ("amount" in paramsCopy) {
          paramsCopy.amount = _fmtIntValue(paramsCopy.amount);
        }
        const paramsStr = JSON.stringify(paramsCopy).replace(/'/g, "&apos;").replace(/"/g, "&quot;");
        actionBoxHtml = `
          <div class="opp-action-box">
            <span data-i18n-key="${item.action_template_key}" data-i18n-params="${paramsStr}"></span>
          </div>
        `;
      } else if (item.impact_key) {
        actionBoxHtml = `
          <div class="opp-action-box">
            <span data-i18n="${item.impact_key}"></span>
          </div>
        `;
      }

      html += `
        <div class="opp-card fade-in-up">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <div class="d-flex align-items-center gap-2" style="color:var(--text-primary);">
              <i class="bi ${iconClass}" style="font-size:22px; color:var(--accent-yellow);"></i>
              <h6 style="margin:0; font-weight:700; color:var(--text-primary);" data-i18n="${item.title_key}"></h6>
            </div>
            <div>
              <span class="portfolio-severity-badge ${severityClass}" data-i18n="${item.severity_key}"></span>
            </div>
          </div>
          ${signalsHtml}
          ${highlightedHtml}
          ${actionBoxHtml}
        </div>
      `;
    });
    html += `</div>`;
  }

  pane.innerHTML = html;
  if (typeof applyTranslations === "function") applyTranslations();
}

async function loadOpportunityDetection(force = false) {
  if (_opportunityDetectionData && !force) {
    _renderOpportunityDetection(_opportunityDetectionData);
    _opportunityDetectionLoaded = true;
    return;
  }

  _renderOpportunityDetectionLoading();
  try {
    const response = await fetch("/api/financial-advisor/opportunity-detection/");
    if (!response.ok) {
      throw new Error("opportunity_detection_fetch_failed");
    }
    const payload = await response.json();
    _opportunityDetectionData = payload;
    _renderOpportunityDetection(payload);
    _opportunityDetectionLoaded = true;
  } catch (error) {
    console.error(error);
    _renderOpportunityDetectionError();
  }
}

window.loadOpportunityDetection = loadOpportunityDetection;
