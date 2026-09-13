"use strict";
// Wealth growth forecast HTML fragment builder
// This file is part of the financial_advisor module. Do not edit directly.

function _buildWealthGrowthFragments(payload) {
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

  return { summary, periodCards, scenarioCardsHtml, breakdownHtml, insightKey };
}
