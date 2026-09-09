"use strict";
// Overview tab — KPI cards row builder (Net Worth, Liquid Assets, Fixed
// Assets, Portfolio Health). Split out of overview_cards.js (200-line
// backlog). Bare global.
// ════════════════════════════════════════════════════════════════════════════

function buildOverviewKpiCardsHtml(payload, kpis) {
  const nwTrendIsUp = Number(kpis.net_worth_growth_yoy || 0) >= 0;
  const nwTrendClass = nwTrendIsUp ? "up" : "down";
  const nwTrendText = nwTrendIsUp
    ? t("overview_kpi_yoy_trend_up", `↑ {pct}% vs last year`).replace(
        "{pct}",
        fmt(Math.abs(kpis.net_worth_growth_yoy))
      )
    : t("overview_kpi_yoy_trend_down", `↓ {pct}% vs last year`).replace(
        "{pct}",
        fmt(Math.abs(kpis.net_worth_growth_yoy))
      );

  const healthScore = Number(payload.health_score || 0);
  let healthColor = "var(--accent-green)";
  if (healthScore < 60) healthColor = "var(--accent-red)";
  else if (healthScore < 75) healthColor = "var(--accent-yellow)";
  else if (healthScore < 90) healthColor = "#2d7fff";

  return `
    <div class="row g-3 mb-3">
      <!-- KPI 1: Net Worth -->
      <div class="col-12 col-sm-6 col-xl-3" style="cursor:pointer;" onclick="sessionStorage.setItem('wf_balance_active_tab', 'overview'); window.location.hash='#balance'">
        <div class="overview-card overview-kpi-card h-100">
          <div class="overview-kpi-icon-wrap" style="background:rgba(123, 147, 201, 0.12); color:#a07cf0; width: 52px; height: 52px; font-size: 28px;">
            <i class="bi bi-wallet2"></i>
          </div>
          <div class="overview-kpi-details">
            <div class="overview-kpi-label" data-i18n="overview_kpi_total_net_worth">Total Net Worth</div>
            <div class="overview-kpi-value">${_money(kpis.total_net_worth)}</div>
            <div class="overview-kpi-trend ${nwTrendClass}">${nwTrendText}</div>
          </div>
        </div>
      </div>

      <!-- KPI 2: Liquid Assets -->
      <div class="col-12 col-sm-6 col-xl-3" style="cursor:pointer;" onclick="sessionStorage.setItem('wf_balance_active_tab', 'overview'); window.location.hash='#balance'">
        <div class="overview-card overview-kpi-card h-100">
          <div class="overview-kpi-icon-wrap" style="background:rgba(79, 143, 247, 0.12); color:#4f8ff7; width: 52px; height: 52px; font-size: 28px;">
            <i class="bi bi-droplet-fill"></i>
          </div>
          <div class="overview-kpi-details">
            <div class="overview-kpi-label" data-i18n="overview_kpi_liquid_assets">Liquid Assets</div>
            <div class="overview-kpi-value">${_money(kpis.liquid_assets)}</div>
            <div class="overview-kpi-trend neutral">
              ${t("overview_kpi_months_expenses", "{months} months of expenses").replace("{months}", fmt(Math.round(kpis.emergency_months * 10) / 10))}
            </div>
          </div>
        </div>
      </div>

      <!-- KPI 3: Fixed Assets -->
      <div class="col-12 col-sm-6 col-xl-3" style="cursor:pointer;" onclick="window.location.hash='#fixed-assets'">
        <div class="overview-card overview-kpi-card h-100">
          <div class="overview-kpi-icon-wrap" style="background:rgba(243, 200, 70, 0.12); color:#f3c846; width: 52px; height: 52px; font-size: 28px;">
            <i class="bi bi-house-fill"></i>
          </div>
          <div class="overview-kpi-details">
            <div class="overview-kpi-label" data-i18n="overview_kpi_fixed_assets">Fixed Assets</div>
            <div class="overview-kpi-value">${_money(kpis.fixed_assets)}</div>
            <div class="overview-kpi-trend neutral">
              ${t("overview_kpi_pct_net_worth", "{pct}% of net worth").replace("{pct}", fmt(kpis.fixed_assets_pct))}
            </div>
          </div>
        </div>
      </div>

      <!-- KPI 4: Portfolio Health -->
      <div class="col-12 col-sm-6 col-xl-3" style="cursor:pointer;" onclick="switchFinancialAdvisorTab('portfolio-optimizer')">
        <div class="overview-card overview-kpi-card h-100">
          <div class="overview-kpi-icon-wrap" style="background:rgba(80, 216, 144, 0.12); color:#50d890; width: 52px; height: 52px; font-size: 28px;">
            <i class="bi bi-pie-chart-fill"></i>
          </div>
          <div class="overview-kpi-details">
            <div class="overview-kpi-label" data-i18n="overview_kpi_portfolio_health">Portfolio Health</div>
            <div class="overview-kpi-value">${Math.round(kpis.portfolio_health)}/100</div>
            <div class="overview-kpi-trend" style="color:${healthColor};">${t(kpis.portfolio_health_status_key, "Good")}</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

window.buildOverviewKpiCardsHtml = buildOverviewKpiCardsHtml;
