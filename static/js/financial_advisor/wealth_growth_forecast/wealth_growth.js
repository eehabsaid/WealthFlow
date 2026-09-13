"use strict";
// Wealth growth forecast tab rendering, load, and theme event listener
// This file is part of the financial_advisor module. Do not edit directly.

function _renderWealthGrowthLoading() {
  const pane = document.getElementById("fa-pane-wealth-growth-forecast");
  if (!pane) return;

  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="wealth_growth_loading"></div>
    </div>
  `;
  applyTranslations();
}

function _renderWealthGrowthError() {
  const pane = document.getElementById("fa-pane-wealth-growth-forecast");
  if (!pane) return;

  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="wealth_growth_error"></span>
    </div>
  `;
  applyTranslations();
}

function _attachWealthGrowthThemeListener() {
  if (_wealthGrowthForecastThemeListenerAttached) return;
  window.addEventListener("themeChanged", () => {
    if (_wealthGrowthForecastLoaded && _wealthGrowthForecastData) {
      _renderWealthGrowthForecast(_wealthGrowthForecastData);
    }
  });
  _wealthGrowthForecastThemeListenerAttached = true;
}

function _renderWealthGrowthForecast(payload) {
  const pane = document.getElementById("fa-pane-wealth-growth-forecast");
  if (!pane) return;

  const { summary, periodCards, scenarioCardsHtml, breakdownHtml, insightKey } =
    _buildWealthGrowthFragments(payload);

  pane.innerHTML = `
    <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:16px; height:360px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="wealth_growth_chart_title"></div>
        <div style="height:300px; position:relative;">
          <canvas id="wealthGrowthChart"></canvas>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-4">
      ${periodCards
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
        .join("")}
    </div>

    <div class="row g-3 mb-4">
      ${scenarioCardsHtml}
    </div>

    <div class="row g-3 mb-4">
      ${breakdownHtml}
    </div>

    <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:20px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="wealth_growth_summary_title"></div>
        <div class="row g-3">
          <div class="col-12 col-md-6 col-xl-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_expected_increase"></div>
              <div class="asset-summary-value" style="font-size:1.5rem; color:var(--text-primary);">${_money(summary.expected_net_worth_increase || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xl-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_expected_growth_pct"></div>
              <div class="asset-summary-value" style="font-size:1.5rem; color:var(--text-primary);">${fmtpresent(summary.expected_growth_pct || 0)}%</div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xl-4">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_monthly_increase"></div>
              <div class="asset-summary-value" style="font-size:1.5rem; color:var(--text-primary);">${_money(summary.estimated_monthly_wealth_increase || 0)}</div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xl-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_largest_appreciating_asset"></div>
              <div class="asset-summary-value" style="font-size:1.35rem; color:var(--text-primary);" data-i18n="${_wealthComponentTitle(summary.largest_appreciating_asset?.key || "none")}"></div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xl-6">
            <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18);">
              <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="wealth_growth_fastest_growing_category"></div>
              <div class="asset-summary-value" style="font-size:1.35rem; color:var(--text-primary);" data-i18n="${_wealthComponentTitle(summary.fastest_growing_asset_category?.key || "none")}"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="alert alert-info" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="${insightKey}"></span>
    </div>
  `;

  applyTranslations();
  _drawWealthGrowthChart(payload);
  _attachWealthGrowthThemeListener();
}

async function loadWealthGrowthForecast(force = false) {
  if (_wealthGrowthForecastData && !force) {
    _renderWealthGrowthForecast(_wealthGrowthForecastData);
    _wealthGrowthForecastLoaded = true;
    return;
  }

  _renderWealthGrowthLoading();
  try {
    const response = await fetch("/api/financial-advisor/wealth-growth-forecast/");
    if (!response.ok) {
      throw new Error("wealth_growth_fetch_failed");
    }
    const payload = await response.json();
    _wealthGrowthForecastData = payload;
    _renderWealthGrowthForecast(payload);
    _wealthGrowthForecastLoaded = true;
  } catch (error) {
    _renderWealthGrowthError();
  }
}
