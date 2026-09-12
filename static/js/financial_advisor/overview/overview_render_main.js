"use strict";

// Overview tab — main render orchestrator. Computes derived values, calls
// the list/section builders, and assembles the final markup. Split out of
// overview_render.js into sibling files (200-line backlog):
// overview_render_helpers.js, overview_render_lists.js,
// overview_render_row1.js. This file is the orchestrator.
// ════════════════════════════════════════════════════════════════════════════

function _renderOverview(payload) {
  const container = document.getElementById("fa-overview-content");
  if (!container) return;

  const kpis = payload.kpis || {};
  const totalNetWorth = Number(kpis.total_net_worth || 0);

  // 1. Graceful Empty State check
  if (totalNetWorth <= 10.0) {
    container.innerHTML = `
      <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
        <div class="card-body" style="padding:48px; text-align:center;">
          <div style="font-size:42px; color:var(--text-secondary); opacity:0.3; margin-bottom:16px;">
            <i class="bi bi-wallet2"></i>
          </div>
          <h4 style="color:var(--text-primary); margin-bottom:12px;" data-i18n="overview_empty_state_title">No financial data available yet.</h4>
          <p style="color:var(--text-secondary); max-width:520px; margin:0 auto 24px auto; line-height:1.6;" data-i18n="overview_empty_state_desc">Start by adding bank accounts, fixed assets, or monthly expenses to receive structured AI financial insights and overview metrics.</p>
          <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
            <a href="#balance" onclick="sessionStorage.setItem('wf_balance_active_tab', 'accounts');" class="btn btn-sm btn-outline-primary px-3 py-2" style="border-radius:6px; font-weight:600;"><i class="bi bi-bank me-1"></i> <span data-i18n="balance_tab_accounts">Accounts</span></a>
            <a href="#fixed-assets" class="btn btn-sm btn-outline-primary px-3 py-2" style="border-radius:6px; font-weight:600;"><i class="bi bi-house me-1"></i> <span data-i18n="nav_fixed_assets">Assets</span></a>
            <a href="#expenses" class="btn btn-sm btn-outline-primary px-3 py-2" style="border-radius:6px; font-weight:600;"><i class="bi bi-cart me-1"></i> <span data-i18n="nav_expenses_reports">Expenses</span></a>
          </div>
        </div>
      </div>
    `;
    applyTranslations();
    return;
  }

  const cashFlow = payload.cash_flow || {};
  const wealthGrowth = payload.wealth_growth || {};
  const portfolio = payload.portfolio || {};
  const goals = payload.goals || {};
  const risk = payload.risk || payload.risk_profile || {};
  const asOf = payload.as_of || { day: "", month_key: "", year: "", time: "" };

  const healthScore = Number(payload.health_score || 0);

  // Health Score Color Indicator (Standardized Theme Colors)
  let healthColor = "var(--accent-green)";
  if (healthScore < 60) healthColor = "var(--accent-red)";
  else if (healthScore < 75) healthColor = "var(--accent-yellow)";
  else if (healthScore < 90) healthColor = "#2d7fff"; // Good (standard blue)

  const healthRing = `conic-gradient(${healthColor} ${healthScore}%, rgba(123,147,201,0.12) 0)`;

  // Legend highlight calculation
  const rangeExcellentActive = healthScore >= 90;
  const rangeGoodActive = healthScore >= 75 && healthScore < 90;
  const rangeAverageActive = healthScore >= 60 && healthScore < 75;
  const rangeNeedsActive = healthScore < 60;

  // Recommendation Paragraphs (Limited to 3 items)
  const recParagraphsHtml = _formatOverviewAiSummary(payload.executive_summary);

  // Alerts list with severity badge and empty state fallback
  const alertsHtml = buildOverviewAlertsHtml(payload);

  // Net Worth trend calculations
  const nwTrendIsUp = Number(kpis.net_worth_growth_yoy || 0) >= 0;
  const nwTrendText = nwTrendIsUp
    ? t("overview_kpi_yoy_trend_up", `↑ {pct}% vs last year`).replace(
        "{pct}",
        fmt(Math.abs(kpis.net_worth_growth_yoy))
      )
    : t("overview_kpi_yoy_trend_down", `↓ {pct}% vs last year`).replace(
        "{pct}",
        fmt(Math.abs(kpis.net_worth_growth_yoy))
      );

  // Cash Flow expected change
  const cfChangeVal = Number(cashFlow.expected_change_30d || 0);
  const cfChangeSign = cfChangeVal >= 0 ? "+" : "";
  const cfChangeClass = cfChangeVal >= 0 ? "up" : "down";

  // Wealth Growth expected growth
  const wgGrowthVal = Number(wealthGrowth.expected_growth_pct || 0);
  const wgGrowthSign = wgGrowthVal >= 0 ? "+" : "";

  // Dynamic Opportunities list with colored severity badge and empty state fallback
  const opportunitiesHtml = buildOverviewOpportunitiesHtml(payload);

  // Portfolio allocation list rows (vertical alignment right)
  const allocationRowsHtml = buildOverviewAllocationRowsHtml(portfolio);

  const goalProgressPct = Math.round(goals.progress_pct || 0);
  const goalRing = `conic-gradient(var(--accent-primary) ${goalProgressPct}%, rgba(123,147,201,0.12) 0)`;

  // Localized date formatting
  const monthName = t(asOf.month_key, asOf.month_key);

  const row1Ctx = {
    payload,
    kpis,
    goals,
    healthScore,
    healthColor,
    healthRing,
    rangeExcellentActive,
    rangeGoodActive,
    rangeAverageActive,
    rangeNeedsActive,
    recParagraphsHtml,
    alertsHtml,
    nwTrendIsUp,
    nwTrendText,
  };

  // Build the complete layout
  container.innerHTML = `
${buildOverviewRow1Html(row1Ctx)}
    <!-- ROW 2: Four KPI Cards (Lift-on-Hover Effect) -->
    ${typeof buildOverviewKpiCardsHtml === "function" ? buildOverviewKpiCardsHtml(payload, kpis) : ""}

    <!-- ROW 3 & ROW 4: Summary cards and footer -->
    ${typeof buildOverviewSummaryRowsHtml === "function" ? buildOverviewSummaryRowsHtml({ cashFlow, cfChangeClass, cfChangeSign, cfChangeVal, wealthGrowth, wgGrowthSign, wgGrowthVal, opportunitiesHtml, allocationRowsHtml, portfolio, risk, goals, goalRing, goalProgressPct, asOf, monthName }) : ""}
  `;

  applyTranslations();

  // Initialize tooltips
  const tooltipTriggerList = [].slice.call(
    container.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  _drawOverviewCharts(payload);
}

window._renderOverview = _renderOverview;
