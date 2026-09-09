"use strict";
// Overview tab — ROW 4 builder (Portfolio Allocation, Risk Profile, Goal
// Planning). Split out of overview_cards.js (200-line backlog). Bare
// global; takes the same params object as buildOverviewSummaryRowsHtml.
// ════════════════════════════════════════════════════════════════════════════

function buildOverviewRow4Html(params) {
  const { allocationRowsHtml, portfolio, risk, goals, goalRing, goalProgressPct } = params;
  return `    <!-- ROW 4: Portfolio Allocation, Risk Profile, Goal Planning -->
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
            <button onclick="switchFinancialAdvisorTab('${portfolio.target_tab || "portfolio-optimizer"}')">
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
            <button onclick="switchFinancialAdvisorTab('${risk.target_tab || "risk-analysis"}')">
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
            <button onclick="switchFinancialAdvisorTab('${goals.target_tab || "goal-planning"}')">
              <span data-i18n="overview_goal_view">View Goal Planning</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
`;
}
