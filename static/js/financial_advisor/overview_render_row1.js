"use strict";

// Overview tab — ROW 1 markup builder (Financial Health, AI Executive
// Summary, Alerts cards). Split out of overview_render.js (200-line
// backlog). Bare global; takes a pre-computed context object built by
// _renderOverview.
// ════════════════════════════════════════════════════════════════════════════

function buildOverviewRow1Html(ctx) {
  const {
    payload, kpis, goals, healthScore, healthColor, healthRing,
    rangeExcellentActive, rangeGoodActive, rangeAverageActive, rangeNeedsActive,
    recParagraphsHtml, alertsHtml, nwTrendIsUp, nwTrendText,
  } = ctx;
  return `    <!-- ROW 1: Financial Health, AI Executive Summary, Alerts (Bottom Margin mb-4 for Spacing Rhythm) -->
    <div class="row g-3 mb-4">
      <!-- Financial Health Card -->
      <div class="col-12 col-lg-3">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title mb-2">
              <span data-i18n="overview_kpi_portfolio_health">Portfolio Health</span>
              <i class="bi bi-info-circle ms-2" style="color: var(--text-secondary); cursor: pointer;" data-bs-toggle="tooltip" data-bs-placement="top" data-i18n="[title]overview_health_score_tooltip"></i>
            </div>
            <div class="overview-score-ring" style="background:${healthRing};">
              <div class="overview-score-center">
                <div class="overview-score-value" style="font-size: 46px;">${healthScore}</div>
                <div class="overview-score-total" style="color: var(--text-secondary);">/100</div>
              </div>
            </div>
            <!-- Score Range Legends with Dynamic Highlight Range -->
            <div style="font-size: 11px; margin-top: 14px; border-top: 1px solid var(--border-color); padding-top: 10px;">
              <div class="d-flex align-items-center mb-1" style="opacity: ${rangeExcellentActive ? "1" : "0.45"}; font-weight: ${rangeExcellentActive ? "700" : "normal"};">
                <span class="d-inline-block rounded-circle me-2" style="width:8px; height:8px; background:var(--accent-green); flex-shrink:0;"></span>
                <span style="color:var(--text-primary);">${rangeExcellentActive ? "✔ " : ""}<span data-i18n="overview_legend_excellent">Excellent (90-100)</span></span>
              </div>
              <div class="d-flex align-items-center mb-1" style="opacity: ${rangeGoodActive ? "1" : "0.45"}; font-weight: ${rangeGoodActive ? "700" : "normal"};">
                <span class="d-inline-block rounded-circle me-2" style="width:8px; height:8px; background:#2d7fff; flex-shrink:0;"></span>
                <span style="color:var(--text-primary);">${rangeGoodActive ? "✔ " : ""}<span data-i18n="overview_legend_good">Good (75-89)</span></span>
              </div>
              <div class="d-flex align-items-center mb-1" style="opacity: ${rangeAverageActive ? "1" : "0.45"}; font-weight: ${rangeAverageActive ? "700" : "normal"};">
                <span class="d-inline-block rounded-circle me-2" style="width:8px; height:8px; background:var(--accent-yellow); flex-shrink:0;"></span>
                <span style="color:var(--text-primary);">${rangeAverageActive ? "✔ " : ""}<span data-i18n="overview_legend_average">Average (60-74)</span></span>
              </div>
              <div class="d-flex align-items-center" style="opacity: ${rangeNeedsActive ? "1" : "0.45"}; font-weight: ${rangeNeedsActive ? "700" : "normal"};">
                <span class="d-inline-block rounded-circle me-2" style="width:8px; height:8px; background:var(--accent-red); flex-shrink:0;"></span>
                <span style="color:var(--text-primary);">${rangeNeedsActive ? "✔ " : ""}<span data-i18n="overview_legend_needs_attention">Needs Attention (&lt;60)</span></span>
              </div>
            </div>
          </div>
          <div>
            <div class="overview-health-label" style="color:${healthColor};">${t(payload.health_status_key, "Good")}</div>
            <div class="overview-health-desc" style="color: var(--text-secondary);">${t(payload.health_desc_key, "")}</div>
          </div>
        </div>
      </div>

      <!-- AI Executive Summary Card (Structured summary dotted leaders & text-primary contrast values) -->
      <div class="col-12 col-lg-6">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div class="overview-card-title">
            <span>
              <i class="bi bi-brilliance text-primary me-2"></i>
              <span data-i18n="overview_executive_summary_title">AI Executive Summary</span>
            </span>
          </div>
          <div class="overview-ai-card-content flex-row align-items-start gap-4" style="height: calc(100% - 75px);">
            <!-- Left Grid with dotted leaders and recommendation paragraphs -->
            <div style="flex:1.25; width:0; height:100%; display:flex; flex-direction:column; justify-content:space-between;">
              <div class="mb-3 pb-2 border-bottom" style="border-color:var(--border-color) !important;">
                
                <!-- Row 1: Portfolio Health -->
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="overview_kpi_portfolio_health" style="flex-shrink:0;">Portfolio Health</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:${healthColor}; flex-shrink:0;">${t(payload.executive_summary.health_status_key, payload.executive_summary.health_status_fallback)}</span>
                </div>

                <!-- Row 2: Net Worth -->
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="overview_kpi_total_net_worth" style="flex-shrink:0;">Net Worth</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:var(--text-primary); flex-shrink:0; display:inline-flex; align-items:center;">
                    ${_money(kpis.total_net_worth)} 
                    <span class="ms-2" style="font-size:11px; font-weight:600; color:${nwTrendIsUp ? "var(--accent-green)" : "var(--accent-red)"}; margin-left:6px;">${nwTrendText}</span>
                  </span>
                </div>

                <!-- Row 3: Liquidity -->
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="portfolio_optimizer_liquidity" style="flex-shrink:0;">Liquidity</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:var(--text-primary); flex-shrink:0;">
                    ${fmt(payload.executive_summary.emergency_months)} <span data-i18n="portfolio_optimizer_months_short">mo</span> 
                    <span style="color: var(--text-secondary); font-size:11px; font-weight:normal;">(${t(payload.executive_summary.liquidity_status_key, payload.executive_summary.liquidity_status_fallback)})</span>
                  </span>
                </div>

                <!-- Row 4: Diversification -->
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="portfolio_optimizer_diversification_rating" style="flex-shrink:0;">Diversification</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:var(--text-primary); flex-shrink:0;">${t(payload.executive_summary.diversification_status_key, payload.executive_summary.diversification_status_fallback)}</span>
                </div>

                <!-- Row 5: Goals -->
                <div class="d-flex align-items-center justify-content-between" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="goal_planning_goal_progress" style="flex-shrink:0;">Goals</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:var(--text-primary); flex-shrink:0;">
                    <span style="color: var(--accent-green);">${goals.completed || 0}</span> / 
                    <span style="color: var(--accent-primary);">${goals.on_track || 0}</span> / 
                    <span style="color: var(--accent-red);">${goals.delayed || 0}</span>
                  </span>
                </div>

              </div>
              <div class="overview-rec-paragraphs">
                ${recParagraphsHtml}
              </div>
            </div>
            <img class="overview-ai-graphic d-none d-sm-block animate__animated animate__fadeIn" src="/static/images/financial_advisor_overview_hero.svg" alt="AI illustration" style="align-self: flex-start; margin-top: 6px;">
          </div>
          <div class="overview-ai-footer">
            <span>
              <i class="bi bi-calendar3 me-1"></i>
              <span data-i18n="overview_last_updated">Last Updated</span>
            </span>
            <button onclick="switchFinancialAdvisorTab('portfolio-optimizer')">
              <span data-i18n="overview_view_details">View Details</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Alerts Card -->
      <div class="col-12 col-lg-3">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-bell-fill text-warning me-2"></i>
                <span data-i18n="overview_alert_title">Alerts</span>
              </span>
              <a href="javascript:void(0);" onclick="switchFinancialAdvisorTab('opportunity-detection')" style="font-size:12px; font-weight:600; text-decoration:none; color:var(--accent-primary);" data-i18n="overview_view_all">View All</a>
            </div>
            <div class="overview-alerts-list">
              ${alertsHtml}
            </div>
          </div>
        </div>
      </div>
    </div>
`;
}
