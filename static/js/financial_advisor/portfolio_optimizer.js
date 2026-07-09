"use strict";
// Portfolio optimizer tab rendering and load handlers
// This file is part of the financial_advisor module. Do not edit directly.

function _renderPortfolioOptimizerLoading() {
  const pane = document.getElementById("fa-pane-portfolio-optimizer");
  if (!pane) return;
  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="portfolio_optimizer_loading"></div>
    </div>
  `;
  applyTranslations();
}

function _renderPortfolioOptimizerError() {
  const pane = document.getElementById("fa-pane-portfolio-optimizer");
  if (!pane) return;
  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="portfolio_optimizer_error"></span>
    </div>
  `;
  applyTranslations();
}

function _renderPortfolioOptimizer(payload) {
  const pane = document.getElementById("fa-pane-portfolio-optimizer");
  if (!pane) return;

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

  const allocationCardsHtml = cards.map((card) => `
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
  `).join("");

  const recommendationsHtml = recommendations.map((item) => `
    <div class="portfolio-rec-item">
      <div class="portfolio-rec-text" data-i18n="${item.key}"></div>
      <span class="portfolio-severity-badge ${_portfolioSeverityClass(item.severity)}" data-i18n="${item.severity_key}"></span>
    </div>
  `).join("");

  const breakdownRows = breakdown.length
    ? breakdown.map((item) => `
      <tr>
        <td>${item.asset || t("portfolio_optimizer_no_data", "No data available")}</td>
        <td>${item.type || "-"}</td>
        <td>${fmt(Number(item.value || 0))}</td>
        <td>${fmtpresent(Number(item.portfolio_pct || 0))}%</td>
        <td class="${Number(item.gain || 0) >= 0 ? "portfolio-gain-up" : "portfolio-gain-down"}">${Number(item.gain || 0) >= 0 ? "+" : ""}${fmt(Number(item.gain || 0))}</td>
      </tr>
    `).join("")
    : `<tr><td colspan="5" class="text-center" data-i18n="portfolio_optimizer_empty_assets"></td></tr>`;

  const opportunitiesHtml = opportunities.length
    ? opportunities.map((item) => `
      <div class="portfolio-opp-item">
        <div>
          <div class="portfolio-opp-title" data-i18n="${item.key}"></div>
          <div class="portfolio-opp-impact" data-i18n="${item.impact_key}"></div>
        </div>
        <span class="portfolio-severity-badge ${_portfolioSeverityClass(item.severity)}" data-i18n="${item.severity_key}"></span>
      </div>
    `).join("")
    : `<div class="portfolio-empty-state" data-i18n="portfolio_optimizer_no_opportunities"></div>`;

  pane.innerHTML = `
    <div class="portfolio-optimizer-wrap">
      <div class="portfolio-optimizer-header">
        <div>
          <h4 data-i18n="financial_advisor_tab_portfolio_optimizer"></h4>
          <p data-i18n="portfolio_optimizer_subtitle"></p>
        </div>
        <div class="portfolio-optimizer-date">
          <span data-i18n="portfolio_optimizer_as_of"></span>
          <strong>${payload?.as_of || "-"}</strong>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-3">
          <div class="portfolio-card portfolio-health-card h-100">
            <div class="portfolio-card-title" data-i18n="portfolio_optimizer_health_score"></div>
            <div class="portfolio-score-ring" style="background:${scoreRing};">
              <div class="portfolio-score-center">${Math.round(scoreValue)}</div>
            </div>
            <div class="portfolio-score-label" data-i18n="${health.label_key || "portfolio_optimizer_health_attention"}"></div>
            <div class="portfolio-score-footnote" data-i18n="${health.explanation_key || "portfolio_optimizer_health_note"}"></div>
          </div>
        </div>

        <div class="col-12 col-xl-9">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="portfolio_optimizer_allocation"></div>
            <div class="portfolio-allocation-grid">${allocationCardsHtml}</div>
          </div>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-lg-4">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="portfolio_optimizer_diversification_analysis"></div>
            <div class="portfolio-kv-list">
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_asset_classes_owned"></span><strong>${Number(diversification.asset_classes_owned || 0)}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_bank_accounts_used"></span><strong>${Number(diversification.bank_accounts_used || 0)}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_largest_asset_concentration"></span><strong>${fmtpresent(Number(diversification?.largest_asset_concentration?.percentage || 0))}%</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_largest_bank_concentration"></span><strong>${diversification?.largest_bank_concentration?.bank_name || t("portfolio_optimizer_no_data", "No data available")}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_largest_portfolio_allocation"></span><strong data-i18n="${diversification?.largest_portfolio_allocation?.label_key || diversification?.largest_asset_type || "portfolio_optimizer_asset_cash"}"></strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_largest_currency_exposure"></span><strong>${diversification?.largest_currency_exposure?.code || t("portfolio_optimizer_no_data", "No data available")}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_diversification_rating"></span><strong data-i18n="${diversification?.portfolio_diversification_rating || "portfolio_optimizer_diversification_moderate"}"></strong></div>
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-4">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="portfolio_optimizer_ai_recommendations"></div>
            <div class="portfolio-rec-list">${recommendationsHtml}</div>
          </div>
        </div>

        <div class="col-12 col-lg-4">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="portfolio_optimizer_concentration_analysis"></div>
            <div class="portfolio-kv-list">
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_largest_asset"></span><strong>${concentration?.largest_asset?.asset || t("portfolio_optimizer_no_data", "No data available")}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_largest_bank"></span><strong>${concentration?.largest_bank?.bank_name || t("portfolio_optimizer_no_data", "No data available")}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_largest_balance"></span><strong>${concentration?.largest_balance?.title || t("portfolio_optimizer_no_data", "No data available")}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_highest_appreciating_asset"></span><strong>${concentration?.highest_appreciating_asset?.asset || t("portfolio_optimizer_no_data", "No data available")}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_gain_amount"></span><strong>${fmt(Number(concentration?.highest_appreciating_asset?.gain || 0))}</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_appreciation_pct"></span><strong>${Number(concentration?.highest_appreciating_asset?.gain_pct || 0) >= 0 ? "+" : ""}${fmtpresent(Number(concentration?.highest_appreciating_asset?.gain_pct || 0))}%</strong></div>
              <div class="portfolio-kv-row"><span data-i18n="portfolio_optimizer_largest_concentration_pct"></span><strong>${fmtpresent(Number(concentration?.largest_concentration_pct || 0))}%</strong></div>
            </div>
            ${concentration?.warning ? `<div class="portfolio-warning" data-i18n="portfolio_optimizer_concentration_warning"></div>` : `<div class="portfolio-healthy" data-i18n="portfolio_optimizer_concentration_ok"></div>`}
          </div>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-lg-7">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="portfolio_optimizer_asset_breakdown"></div>
            <div class="table-responsive">
              <table class="table table-sm portfolio-table">
                <thead>
                  <tr>
                    <th data-i18n="portfolio_optimizer_col_asset"></th>
                    <th data-i18n="portfolio_optimizer_col_type"></th>
                    <th data-i18n="portfolio_optimizer_col_value"></th>
                    <th data-i18n="portfolio_optimizer_col_portfolio_pct"></th>
                    <th data-i18n="portfolio_optimizer_col_gain"></th>
                  </tr>
                </thead>
                <tbody>${breakdownRows}</tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-5">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="portfolio_optimizer_allocation_chart"></div>
            <div class="portfolio-chart-wrap">
              <canvas id="portfolioAllocationChart"></canvas>
            </div>
            <div class="portfolio-chart-footnote" data-i18n="portfolio_optimizer_chart_note"></div>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-12">
          <div class="portfolio-card">
            <div class="portfolio-card-title" data-i18n="portfolio_optimizer_opportunities"></div>
            <div class="portfolio-opp-list">${opportunitiesHtml}</div>
            <div class="portfolio-baseline-row">
              <span><span data-i18n="portfolio_optimizer_avg_monthly_expenses"></span>: <strong>${fmt(Number(expenseBaseline.avg_monthly_expenses || 0))}</strong></span>
              <span><span data-i18n="portfolio_optimizer_emergency_months"></span>: <strong>${fmtpresent(Number(expenseBaseline.emergency_fund_months || 0))}</strong></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  applyTranslations();
  _drawPortfolioAllocationChart(payload);
}

async function loadPortfolioOptimizer(force = false) {
  if (_portfolioOptimizerData && !force) {
    _renderPortfolioOptimizer(_portfolioOptimizerData);
    _portfolioOptimizerLoaded = true;
    return;
  }

  _renderPortfolioOptimizerLoading();
  try {
    const response = await fetch("/api/financial-advisor/portfolio-optimizer/");
    if (!response.ok) {
      throw new Error("portfolio_optimizer_fetch_failed");
    }
    const payload = await response.json();
    _portfolioOptimizerData = payload;
    _renderPortfolioOptimizer(payload);
    _portfolioOptimizerLoaded = true;
  } catch (error) {
    _renderPortfolioOptimizerError();
  }
}

