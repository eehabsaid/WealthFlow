"use strict";

function buildOverviewKpiCardsHtml(payload, kpis) {
  const nwTrendIsUp = Number(kpis.net_worth_growth_yoy || 0) >= 0;
  const nwTrendClass = nwTrendIsUp ? "up" : "down";
  const nwTrendText = nwTrendIsUp
    ? t("overview_kpi_yoy_trend_up", `↑ {pct}% vs last year`).replace("{pct}", fmt(Math.abs(kpis.net_worth_growth_yoy)))
    : t("overview_kpi_yoy_trend_down", `↓ {pct}% vs last year`).replace("{pct}", fmt(Math.abs(kpis.net_worth_growth_yoy)));

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

function buildOverviewSummaryRowsHtml(params) {
  const { cashFlow, cfChangeClass, cfChangeSign, cfChangeVal, wealthGrowth, wgGrowthSign, wgGrowthVal, opportunitiesHtml, allocationRowsHtml, portfolio, risk, goals, goalRing, goalProgressPct, asOf, monthName } = params;

  return `
    <!-- ROW 3: Cash Flow, Wealth Growth, Top Opportunities -->
    <div class="row g-3 mb-3">
      <!-- Cash Flow Summary -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-arrow-down-up text-primary me-2"></i>
                <span data-i18n="overview_cash_flow_title">Cash Flow Summary</span>
              </span>
            </div>
            <div class="overview-summary-body">
              <div class="overview-summary-stats">
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_cash_flow_current">Current Cash Balance</div>
                  <div class="overview-stat-value">${_money(cashFlow.current_cash)}</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_cash_flow_change">Expected Change (Next 30 Days)</div>
                  <div class="overview-stat-value ${cfChangeClass}">${cfChangeSign}${_money(cfChangeVal)}</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_cash_flow_next_event">Next Financial Event</div>
                  <div class="overview-stat-value" style="color: var(--text-primary); font-size:12px; font-weight:700;">
                    ${cashFlow.largest_event ? `${t('cash_flow_event_' + cashFlow.largest_event.type, cashFlow.largest_event.type)}: +${_money(cashFlow.largest_event.amount)}` : "-"}
                  </div>
                </div>
              </div>
              <div class="overview-sparkline-wrap">
                <canvas id="overviewCashFlowChart"></canvas>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${cashFlow.target_tab || 'cash-flow-forecast'}')">
              <span data-i18n="overview_cash_flow_view">View Cash Flow Forecast</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Wealth Growth Summary -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-graph-up-arrow text-success me-2"></i>
                <span data-i18n="overview_wealth_growth_title">Wealth Growth Summary</span>
              </span>
            </div>
            <div class="overview-summary-body">
              <div class="overview-summary-stats">
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_wealth_growth_1y">Projected 1-Year Net Worth</div>
                  <div class="overview-stat-value">${_money(wealthGrowth.projected_1y_net_worth)}</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_wealth_growth_expected">Expected Growth</div>
                  <div class="overview-stat-value text-success">${wgGrowthSign}${fmt(wgGrowthVal)}%</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_wealth_growth_highest">Highest Appreciating Asset</div>
                  <div class="overview-stat-value" style="color: var(--text-primary); font-size:12px; font-weight:700;">
                    ${wealthGrowth.top_appreciating_asset ? `${t(wealthGrowth.top_appreciating_asset.name_key, wealthGrowth.top_appreciating_asset.name_key)} (+${fmt(wealthGrowth.top_appreciating_asset.growth_pct)}%)` : "-"}
                  </div>
                </div>
              </div>
              <div class="overview-sparkline-wrap">
                <canvas id="overviewWealthGrowthChart"></canvas>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${wealthGrowth.target_tab || 'wealth-growth-forecast'}')">
              <span data-i18n="overview_wealth_growth_view">View Wealth Growth Forecast</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Top Optimization Opportunities -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-lightbulb-fill text-warning me-2"></i>
                <span data-i18n="overview_opportunities_title">Top Optimization Opportunities</span>
              </span>
            </div>
            <div class="overview-opp-list">
              ${opportunitiesHtml}
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('opportunity-detection')">
              <span data-i18n="overview_opportunities_view">View All Opportunities</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ROW 4: Portfolio Allocation, Risk Profile, Goal Planning -->
    <div class="row g-3 mb-3">
      <!-- Portfolio Allocation -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-pie-chart-fill text-primary me-2"></i>
                <span data-i18n="overview_portfolio_title">Portfolio Allocation</span>
              </span>
            </div>
            <div class="overview-summary-body" style="padding-bottom: 0;">
              <div class="d-flex align-items-center justify-content-between gap-2" style="margin-bottom: 8px;">
                <div class="overview-donut-wrap" style="width: 110px; height: 110px; flex-shrink:0;">
                  <canvas id="overviewPortfolioDonutChart"></canvas>
                </div>
                <div style="flex: 1; min-width: 0;">
                  ${allocationRowsHtml}
                </div>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer" style="margin-top: 8px;">
            <button onclick="switchFinancialAdvisorTab('${portfolio.target_tab || 'portfolio-optimizer'}')">
              <span data-i18n="overview_portfolio_view">View Portfolio Optimizer</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Risk Profile -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-shield-fill-check text-info me-2"></i>
                <span data-i18n="overview_risk_title">Risk Profile</span>
              </span>
            </div>
            <div class="overview-summary-body" style="min-height: auto;">
              <div class="overview-summary-stats mb-2">
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_risk_level">Overall Risk Level</div>
                  <div class="overview-stat-value text-info fw-bold">${t(risk.overall_level_key || "overview_risk_level_moderate", "Moderate")}</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_risk_highest">Highest Risk Category</div>
                  <div class="overview-stat-value text-warning fw-bold">${t(risk.highest_risk_category_key || "-", "-")}</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_risk_score">Risk Score</div>
                  <div class="overview-stat-value fw-bold" style="color: var(--text-primary);">${risk.score ?? 50}/100</div>
                </div>
              </div>
              <!-- Score Bar -->
              <div style="background:rgba(123,147,201,0.12); height:6px; border-radius:3px; overflow:hidden; margin: 8px 0 12px 0;">
                <div style="width:${risk.score ?? 50}%; height:100%; background:var(--accent-primary); border-radius:3px;"></div>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${risk.target_tab || 'risk-analysis'}')">
              <span data-i18n="overview_risk_view">View Risk Analysis</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Goal Planning -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-bullseye text-primary me-2"></i>
                <span data-i18n="overview_goal_title">Goal Planning</span>
              </span>
            </div>
            <div class="overview-summary-body d-flex align-items-center justify-content-between gap-3" style="min-height: auto;">
              <div style="flex:1;">
                <div class="overview-summary-stats mb-0">
                  <div class="overview-stat-row">
                    <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_goal_active">Active Financial Goals</div>
                    <div class="overview-stat-value fw-bold" style="color: var(--text-primary);">${goals.total || 0}</div>
                  </div>
                  <div class="overview-stat-row">
                    <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_goal_ontrack">On-Track Goals</div>
                    <div class="overview-stat-value text-success fw-bold">${goals.on_track || 0}</div>
                  </div>
                  <div class="overview-stat-row">
                    <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_goal_next_target">Next Goal Target Date</div>
                    <div class="overview-stat-value fw-bold" style="color: var(--text-primary); font-size:12px;">${_formatGoalDate(goals.next_target_date || (goals.next_goal_due && goals.next_goal_due.target_date)) || "-"}</div>
                  </div>
                </div>
              </div>
              <div style="flex-shrink:0; text-align:center">
                <div class="overview-score-ring" style="background:${goalRing}; margin:0;">
                  <div class="overview-score-center" style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <div class="overview-score-value" style="font-size:24px;">${goalProgressPct}%</div>
                    <div style="font-size:10px; color:var(--text-secondary); margin-top:2px;" data-i18n="goal_planning_on_track_goals">On Track</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${goals.target_tab || 'goal-planning'}')">
              <span data-i18n="overview_goal_view">View Goal Planning</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Note with localized server Last Updated time -->
    <div style="font-size:11px; color:var(--text-secondary); text-align:center; padding:16px 0;">
      <div style="margin-bottom: 6px;">All data is based on your transactions and accounts. Please keep your data updated for accurate insights.</div>
      <div style="font-size:10px; opacity:0.85;">
        <span data-i18n="overview_last_updated">Last Updated</span>
        <div style="margin-top: 4px; font-weight: 700; color: var(--text-primary);">${asOf.day || ''} ${monthName} ${asOf.year || ''} &bull; ${asOf.time || ''}</div>
      </div>
    </div>
  `;
}

window.buildOverviewKpiCardsHtml = buildOverviewKpiCardsHtml;
window.buildOverviewSummaryRowsHtml = buildOverviewSummaryRowsHtml;
