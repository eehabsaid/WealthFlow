"use strict";
// Cash flow forecast tab — loading/error states + small HTML fragment builders.
// Split from cash_flow.js. This file is part of the financial_advisor module.
// Siblings: timeline.js (timeline fragment builder), cash_flow.js (composition + load).

function _renderCashFlowLoading() {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="cash_flow_loading"></div>
    </div>
  `;
  applyTranslations();
}

function _renderCashFlowError() {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="cash_flow_error"></span>
    </div>
  `;
  applyTranslations();
}

function _buildCashFlowCardsHtml(cp) {
  const cards = [
    { key: "cash_flow_card_current", value: cp.current || 0 },
    { key: "cash_flow_card_next_month", value: cp.next_month || 0 },
    { key: "cash_flow_card_month_3", value: cp.month_3 || 0 },
    { key: "cash_flow_card_month_6", value: cp.month_6 || 0 },
    { key: "cash_flow_card_month_12", value: cp.month_12 || 0 },
  ];

  return cards
    .map(
      (card) => `
    <div class="col-12 col-sm-6 col-xl">
      <div class="asset-summary-card h-100" style="background:var(--bg-secondary);">
        <div class="asset-summary-label" data-i18n="${card.key}"></div>
        <div class="asset-summary-value">${_money(card.value)}</div>
      </div>
    </div>
  `
    )
    .join("");
}

function _buildCashFlowWarningsHtml(warnings) {
  return warnings
    .map(
      (warning) => `
    <div class="alert alert-${warning.level || "secondary"}" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary); margin-bottom:10px;">
      <span data-i18n="${warning.key}"></span>
    </div>
  `
    )
    .join("");
}
