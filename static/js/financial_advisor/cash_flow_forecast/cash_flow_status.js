"use strict";
// Cash flow forecast tab — Forecast status panel (shown beside the balance chart).
// Display-only: every signal is derived from existing payload fields
// (warnings[], summary). No financial logic lives here.
// This file is part of the financial_advisor module.

function _buildCashFlowStatusPanelHtml(payload) {
  const summary = payload.summary || {};
  const warnings = payload.warnings || [];
  const isHealthy = warnings.some((w) => w.key === "cash_flow_warning_healthy");
  const hasLargeEvent =
    Number((summary.largest_cash_event || {}).amount || 0) > 0 ||
    Number((summary.largest_planned_expense || {}).amount || 0) > 0;

  const rows = [];
  if (isHealthy) {
    rows.push(
      `<div class="cash-flow-status-row is-good">
        <b data-i18n="cash_flow_status_healthy"></b>
        <span data-i18n="cash_flow_status_healthy_desc"></span>
      </div>`
    );
  } else if (Number(summary.net_cash_change || 0) < 0) {
    rows.push(
      `<div class="cash-flow-status-row is-warn">
        <b data-i18n="cash_flow_status_decrease"></b>
        <span data-i18n="cash_flow_status_decrease_desc"></span>
      </div>`
    );
  }
  if (hasLargeEvent) {
    rows.push(
      `<div class="cash-flow-status-row">
        <b data-i18n="cash_flow_status_review_events"></b>
        <span data-i18n="cash_flow_status_review_events_desc"></span>
        <a href="#cash_flow_summary_section" onclick="event.preventDefault(); var el = document.getElementById('cash_flow_summary_section'); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });" data-i18n="cash_flow_status_see_summary"></a>
      </div>`
    );
  }
  rows.push(
    `<div class="cash-flow-status-row">
      <b data-i18n="cash_flow_status_assumptions"></b>
      <span data-i18n="cash_flow_status_assumptions_desc"></span>
    </div>`
  );

  return `
    <div class="card border-0 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:20px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:4px;" data-i18n="cash_flow_status_title"></div>
        <div style="color:var(--text-secondary); font-size:12px; margin-bottom:12px;" data-i18n="cash_flow_status_subtitle"></div>
        ${rows.join("")}
      </div>
    </div>
  `;
}
