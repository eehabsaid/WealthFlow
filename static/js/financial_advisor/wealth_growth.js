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

  const current = payload?.current_net_worth || 0;
  const checkpoints = payload?.checkpoints || {};
  const breakdown = payload?.breakdown || {};
  const summary = payload?.summary || {};
  const scenarioCards = payload?.scenario_cards || {};

  const periodCards = [
    { key: "wealth_growth_current_net_worth", value: checkpoints.current || 0 },
    { key: "wealth_growth_end_next_month", value: checkpoints.next_month || 0 },
    { key: "wealth_growth_end_third_month", value: checkpoints.month_3 || 0 },
    { key: "wealth_growth_end_sixth_month", value: checkpoints.month_6 || 0 },
    { key: "wealth_growth_end_twelfth_month", value: checkpoints.month_12 || 0 },
  ];

  const scenarioCardKeys = ["conservative", "expected", "optimistic"];

  const scenarioCardsHtml = scenarioCardKeys
    .map((key) => {
      const card = scenarioCards[key] || {};
      return `
      <div class="col-12 col-md-4">
        <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.25); box-shadow:0 0 0 1px rgba(255,255,255,0.02) inset;">
          <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="${_scenarioTitle(key)}"></div>
          <div style="color:var(--text-primary); font-size:12px; margin-bottom:8px; opacity:0.9;" data-i18n="wealth_growth_scenario_label"></div>
          <div class="asset-summary-value" style="font-size:1.5rem; color:var(--text-primary);">${_money(card.forecast || 0)}</div>
          <div style="margin-top:8px; color:var(--text-primary); font-size:12px;">
            <span data-i18n="wealth_growth_difference"></span>: ${_money(card.difference || 0)}
          </div>
          <div style="color:var(--text-primary); font-size:12px;">
            <span data-i18n="wealth_growth_growth_pct"></span>: ${fmtpresent(card.growth_pct || 0)}%
          </div>
        </div>
      </div>
    `;
    })
    .join("");

  const breakdownKeys = ["liquid_cash", "fixed_assets", "gold", "certificates"];
  const breakdownHtml = breakdownKeys
    .map((key) => {
      const item = breakdown[key] || {};
      return `
      <div class="col-12 col-md-6 col-xl-3">
        <div class="asset-summary-card h-100" style="background:var(--bg-tertiary); border-color:rgba(26,110,245,0.18); box-shadow:0 0 0 1px rgba(255,255,255,0.02) inset;">
          <div class="asset-summary-label" style="color:var(--text-primary); font-weight:700;" data-i18n="${_wealthComponentTitle(key)}"></div>
          <div style="display:grid;gap:6px;">
            <div style="color:var(--text-primary);"><span style="font-weight:600;" data-i18n="wealth_growth_current"></span>: ${_money(item.current || 0)}</div>
            <div style="color:var(--text-primary);"><span style="font-weight:600;" data-i18n="wealth_growth_forecast"></span>: ${_money(item.forecast || 0)}</div>
            <div style="color:var(--text-primary);"><span style="font-weight:600;" data-i18n="wealth_growth_difference"></span>: ${_money(item.difference || 0)}</div>
            <div style="color:var(--text-primary); display:flex; align-items:center; margin-top:2px;">
              <span style="font-weight:600;" data-i18n="wealth_growth_growth_pct"></span><span style="margin-inline-start:2px;margin-inline-end:8px;">:</span>
              ${(() => {
                const pct = item.growth_pct || 0;
                if (pct > 0) {
                  return (
                    '<span style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;background:rgba(32,201,151,0.15);color:#20c997;font-size:12px;font-weight:600;"><i class="bi bi-arrow-up-short" style="margin-inline-end:2px;font-size:14px;"></i>+' +
                    fmtpresent(pct) +
                    "%</span>"
                  );
                } else if (pct < 0) {
                  return (
                    '<span style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;background:rgba(220,53,69,0.15);color:#dc3545;font-size:12px;font-weight:600;"><i class="bi bi-arrow-down-short" style="margin-inline-end:2px;font-size:14px;"></i>' +
                    fmtpresent(pct) +
                    "%</span>"
                  );
                } else {
                  return (
                    '<span style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;background:rgba(108,117,125,0.15);color:#adb5bd;font-size:12px;font-weight:600;"><i class="bi bi-dash" style="margin-inline-end:2px;font-size:14px;"></i>' +
                    fmtpresent(pct) +
                    "%</span>"
                  );
                }
              })()}
            </div>
          </div>
        </div>
      </div>
    `;
    })
    .join("");

  const insightKey = summary.insight_key || "wealth_growth_insight_balanced";

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
