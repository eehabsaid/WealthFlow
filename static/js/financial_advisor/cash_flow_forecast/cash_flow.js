"use strict";
// Cash flow forecast tab rendering and load handlers
// This file is part of the financial_advisor module. Do not edit directly.
// Siblings: states.js (loading/error/cards/warnings builders), timeline.js
// (month-by-month timeline builder). This file composes them plus the
// summary section and owns loadCashFlowForecast().

function _buildCashFlowSummaryHtml(summary) {
  const largestEvent = summary.largest_cash_event || {};
  const largestExpense = summary.largest_planned_expense || {};
  const nearestMaturity = summary.nearest_certificate_maturity || {};

  return `
    <div class="card border-0" id="cash_flow_summary_section" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:20px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="cash_flow_summary_title"></div>
        <div class="row g-3">
          <div class="col-12 col-md-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_expected_increase"></div>
              <div class="asset-summary-value">${_money(summary.expected_increase || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_expected_decrease"></div>
              <div class="asset-summary-value">${_money(summary.expected_decrease || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_net_change"></div>
              <div class="asset-summary-value">${_money(summary.net_cash_change || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_largest_cash_event"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;" data-i18n="${_eventTranslationKey(largestEvent.type)}"></div>
              <div class="asset-summary-value">${_money(Math.abs(largestEvent.amount || 0))}</div>
            </div>
          </div>
          <div class="col-12 col-md-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_nearest_maturity"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;">${formatDate(nearestMaturity.date) || "-"}</div>
              <div class="asset-summary-value">${_money(nearestMaturity.amount || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-primary);">
              <div class="asset-summary-label" data-i18n="cash_flow_largest_planned_expense"></div>
              <div style="color:var(--text-secondary); margin-bottom:6px;" data-i18n="${_eventTranslationKey(largestExpense.type)}"></div>
              <div class="asset-summary-value">${_money(largestExpense.amount || 0)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function _renderCashFlowForecast(payload) {
  const pane = document.getElementById(_cashFlowPaneId());
  if (!pane) return;

  if (payload?.is_empty) {
    renderFinancialAdvisorEmptyState(_cashFlowPaneId());
    return;
  }

  const cp = payload?.checkpoints || {};
  const timeline = payload?.timeline || [];
  const summary = payload?.summary || {};
  const warnings = payload?.warnings || [];

  const cardsHtml = _buildCashFlowCardsHtml(cp);
  const warningHtml = _buildCashFlowWarningsHtml(warnings);
  const timelineSectionHtml = _buildCashFlowTimelineHtml(timeline);
  const summaryHtml = _buildCashFlowSummaryHtml(summary);
  const statusPanelHtml =
    typeof _buildCashFlowStatusPanelHtml === "function"
      ? _buildCashFlowStatusPanelHtml(payload)
      : "";

  pane.innerHTML = `
    <div class="row g-3 mb-4">
      ${cardsHtml}
    </div>

    <div class="mb-4">
      ${warningHtml}
    </div>

    <div class="row g-3 mb-4">
      <div class="col-12 col-xl-8">
        <div class="card border-0 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
          <div class="card-body" style="padding:20px;">
            <div style="color:var(--text-primary); font-weight:700; margin-bottom:4px;" data-i18n="cash_flow_chart_title"></div>
            <div style="color:var(--text-secondary); font-size:12px; margin-bottom:12px;" data-i18n="cash_flow_chart_subtitle"></div>
            <div class="cash-flow-chart-wrap">
              <canvas id="cash_flow_chart_canvas"></canvas>
            </div>
          </div>
        </div>
      </div>
      <div class="col-12 col-xl-4">
        ${statusPanelHtml}
      </div>
    </div>

    <div class="row g-3">
      <div class="col-12 col-xl-7" id="cash_flow_timeline_container">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="cash_flow_timeline_title"></div>
        ${timelineSectionHtml}
      </div>
      <div class="col-12 col-xl-5">
        <div id="cash_flow_custom_projection_container" class="mb-4"></div>
        ${summaryHtml}
      </div>
    </div>
  `;

  applyTranslations();

  if (typeof _renderCashFlowChart === "function") {
    _renderCashFlowChart(timeline, cp.current);
  }

  if (typeof _renderCashFlowCustomProjectionCard === "function") {
    _renderCashFlowCustomProjectionCard();
  }
}

async function loadCashFlowForecast(force = false) {
  if (_cashFlowForecastData && !force) {
    _renderCashFlowForecast(_cashFlowForecastData);
    _cashFlowForecastLoaded = true;
    return;
  }

  _renderCashFlowLoading();
  try {
    const response = await fetch("/api/financial-advisor/cash-flow-forecast/");
    if (!response.ok) {
      throw new Error("cash_flow_fetch_failed");
    }
    const payload = await response.json();
    _cashFlowForecastData = payload;
    _renderCashFlowForecast(payload);
    _cashFlowForecastLoaded = true;
  } catch (error) {
    _renderCashFlowError();
  }
}
