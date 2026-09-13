"use strict";
// Portfolio optimizer HTML fragment builder
// This file is part of the financial_advisor module. Do not edit directly.

function _buildPortfolioOptimizerFragments(payload) {
  const health = payload?.health || {};
  const allocation = payload?.allocation || {};
  const diversification = payload?.diversification || {};
  const recommendations = payload?.recommendations || [];
  const breakdown = payload?.asset_breakdown || [];
  const concentration = payload?.concentration || {};
  const opportunities = payload?.opportunities || [];
  const expenseBaseline = payload?.expense_baseline || {};
  const cards = (allocation.cards || []).filter((card) => card.key !== "banks");

  const scoreValue = Number(health.score || 0);
  const scoreRing = `conic-gradient(#34c759 ${Math.max(0, Math.min(100, scoreValue))}%, rgba(123,147,201,0.20) 0)`;

  const allocationCardsHtml = cards
    .map(
      (card) => `
    <div class="portfolio-allocation-card ${_portfolioStatusClass(card.status)}">
      <div class="portfolio-allocation-title" data-i18n="${card.label_key}"></div>
      <div class="portfolio-allocation-value">${fmt(Number(card.value || 0))}</div>
      <div class="portfolio-allocation-pct">${fmtpresent(Number(card.percentage || 0))}%</div>
      <div class="portfolio-allocation-range">
        <span data-i18n="portfolio_optimizer_recommended"></span>
        <span>${fmtpresent(Number(card.recommended_min || 0))}% - ${fmtpresent(Number(card.recommended_max || 0))}%</span>
      </div>
      <div class="portfolio-allocation-status ${_portfolioStatusClass(card.status)}" data-i18n="${card.status_key}"></div>
    </div>
  `
    )
    .join("");

  const recommendationsHtml = recommendations
    .map(
      (item) => `
    <div class="portfolio-rec-item">
      <div class="portfolio-rec-text" data-i18n="${item.key}"></div>
      <span class="portfolio-severity-badge ${_portfolioSeverityClass(item.severity)}" data-i18n="${item.severity_key}"></span>
    </div>
  `
    )
    .join("");

  const breakdownRows = breakdown.length
    ? breakdown
        .map(
          (item) => `
      <tr>
        <td>${item.asset || t("portfolio_optimizer_no_data", "No data available")}</td>
        <td>${item.type || "-"}</td>
        <td>${fmt(Number(item.value || 0))}</td>
        <td>${fmtpresent(Number(item.portfolio_pct || 0))}%</td>
        <td class="${Number(item.gain || 0) >= 0 ? "portfolio-gain-up" : "portfolio-gain-down"}">${Number(item.gain || 0) >= 0 ? "+" : ""}${fmt(Number(item.gain || 0))}</td>
      </tr>
    `
        )
        .join("")
    : `<tr><td colspan="5" class="text-center" data-i18n="portfolio_optimizer_empty_assets"></td></tr>`;

  const opportunitiesHtml = opportunities.length
    ? opportunities
        .map(
          (item) => `
      <div class="portfolio-opp-item">
        <div>
          <div class="portfolio-opp-title" data-i18n="${item.key}"></div>
          <div class="portfolio-opp-impact" data-i18n="${item.impact_key}"></div>
        </div>
        <span class="portfolio-severity-badge ${_portfolioSeverityClass(item.severity)}" data-i18n="${item.severity_key}"></span>
      </div>
    `
        )
        .join("")
    : `<div class="portfolio-empty-state" data-i18n="portfolio_optimizer_no_opportunities"></div>`;

  return {
    health,
    diversification,
    concentration,
    expenseBaseline,
    scoreValue,
    scoreRing,
    allocationCardsHtml,
    recommendationsHtml,
    breakdownRows,
    opportunitiesHtml,
  };
}
