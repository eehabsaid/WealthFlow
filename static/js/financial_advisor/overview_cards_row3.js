"use strict";
// Overview tab — ROW 3 builder (Cash Flow, Wealth Growth, Top
// Opportunities). Split out of overview_cards.js (200-line backlog). Bare
// global; takes the same params object as buildOverviewSummaryRowsHtml.
// ════════════════════════════════════════════════════════════════════════════

function buildOverviewRow3Html(params) {
  const { cashFlow, cfChangeClass, cfChangeSign, cfChangeVal, wealthGrowth, wgGrowthSign, wgGrowthVal, opportunitiesHtml } = params;
  return `    <!-- ROW 3: Cash Flow, Wealth Growth, Top Opportunities -->
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
                    ${cashFlow.largest_event ? `${t("cash_flow_event_" + cashFlow.largest_event.type, cashFlow.largest_event.type)}: +${_money(cashFlow.largest_event.amount)}` : "-"}
                  </div>
                </div>
              </div>
              <div class="overview-sparkline-wrap">
                <canvas id="overviewCashFlowChart"></canvas>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${cashFlow.target_tab || "cash-flow-forecast"}')">
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
            <button onclick="switchFinancialAdvisorTab('${wealthGrowth.target_tab || "wealth-growth-forecast"}')">
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
`;
}
