"use strict";
// Risk analysis pane HTML template (main portfolio-optimizer-wrap markup).

window.RA = window.RA || {};

window.RA.buildRiskAnalysisPaneHtml = function (ctx) {
  const {
    payload,
    health,
    score,
    healthScore,
    healthRing,
    riskScore,
    riskRing,
    riskColor,
    breakdownHtml,
    findingsHtml,
    stressHtml,
    sensitivitiesHtml,
    actionsHtml,
    incomeHtml,
    incomeStability,
  } = ctx;
  return `
    <div class="portfolio-optimizer-wrap">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div style="color:var(--text-secondary);" data-i18n="risk_analysis_subtitle"></div>
        <div class="portfolio-optimizer-date">
          <span data-i18n="portfolio_optimizer_as_of"></span>
          <strong>${payload?.as_of || "-"}</strong>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-md-6">
          <div class="portfolio-card portfolio-health-card h-100">
            <div class="portfolio-card-title d-flex justify-content-center align-items-center">
              <i class="bi bi-shield-check me-2" style="color:var(--text-secondary);"></i>
              <span data-i18n="portfolio_optimizer_health_score"></span>
            </div>
            <div class="portfolio-score-ring" style="background:${healthRing};">
              <div class="portfolio-score-center">${Math.round(healthScore)}</div>
            </div>
            <div class="portfolio-score-label" style="color:#34c759;" data-i18n="${health.label_key || "portfolio_optimizer_health_attention"}"></div>
            <div class="portfolio-score-footnote mt-2" data-i18n="risk_analysis_health_note"></div>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="portfolio-card portfolio-health-card h-100">
            <div class="portfolio-card-title d-flex justify-content-center align-items-center">
              <i class="bi bi-shield-exclamation me-2" style="color:var(--text-secondary);"></i>
              <span data-i18n="risk_analysis_risk_score"></span>
            </div>
            <div class="portfolio-score-ring" style="background:${riskRing};">
              <div class="portfolio-score-center">${Math.round(riskScore)}</div>
            </div>
            <div class="portfolio-score-label" style="color:${riskColor};" data-i18n="${score.level_key || "risk_analysis_level_moderate"}"></div>
            <div class="portfolio-score-footnote mt-2" data-i18n="risk_analysis_score_note"></div>
          </div>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-6">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="risk_analysis_breakdown_title"></div>
            <div class="p-2">${breakdownHtml}</div>
          </div>
        </div>
        <div class="col-12 col-xl-6">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="risk_analysis_radar_title"></div>
            <div class="portfolio-chart-wrap d-flex justify-content-center align-items-center h-100" style="min-height:300px;">
              <canvas id="riskRadarChart" style="max-height:300px;"></canvas>
            </div>
          </div>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-5">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="risk_analysis_findings_title"></div>
            <div class="p-2">${findingsHtml}</div>
          </div>
        </div>
        <div class="col-12 col-xl-7">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title d-flex justify-content-between">
              <span data-i18n="risk_analysis_stress_title"></span>
              <span style="font-size:0.8em;font-weight:normal;color:var(--text-secondary);" data-i18n="risk_analysis_stress_col_impact"></span>
            </div>
            <div class="p-2">${stressHtml}</div>
          </div>
        </div>
      </div>

      <div class="portfolio-card mb-3">
        <div class="portfolio-card-title" data-i18n="risk_analysis_whatif_title"></div>
        <div class="row g-3 p-2">${sensitivitiesHtml}</div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-8">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title d-flex justify-content-between align-items-center">
              <div data-i18n="risk_analysis_actions_title"></div>
            </div>
            <div class="p-2">${actionsHtml}</div>
          </div>
        </div>
        <div class="col-12 col-xl-4">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="risk_analysis_income_title"></div>
            <div class="d-flex justify-content-center align-items-center mb-4 mt-3">
              <div style="position:relative; width:180px; height:180px;">
                <canvas id="incomeStabilityChart"></canvas>
                <div style="position:absolute;top:0;left:0;right:0;bottom:0;display:flex;align-items:center;justify-content:center;">
                  <i class="bi bi-briefcase text-secondary fs-1"></i>
                </div>
              </div>
            </div>
            <div class="p-2 mb-3 mt-4">${incomeHtml}</div>
            <div class="d-flex justify-content-between align-items-center pt-3 border-top" style="border-color:var(--border-color) !important;">
              <span style="color:var(--text-secondary);" data-i18n="risk_analysis_income_score_label"></span>
              <div class="d-flex align-items-center">
                <span class="fs-4 fw-bold me-3" style="color:#34c759;">${Math.round(incomeStability.score)} <span style="font-size:0.5em;color:var(--text-secondary);">/100</span></span>
                <span class="portfolio-severity-badge ${incomeStability.score >= 60 ? "portfolio-badge-low" : incomeStability.score >= 40 ? "portfolio-badge-medium" : "portfolio-badge-high"}" data-i18n="${incomeStability.level_key}"></span>
              </div>
            </div>
            <div class="text-center mt-2" style="font-size:0.85em;color:var(--text-secondary);" data-i18n="risk_analysis_income_footer"></div>
          </div>
        </div>
      </div>

      <!-- Overall Recommendation Card -->
      <div class="portfolio-card mb-3" style="border-left: 4px solid var(--accent-primary);">
        <div class="p-3">
          <h4 style="color:var(--text-primary); margin-bottom: 15px;" data-i18n="risk_analysis_overall_rec_title"></h4>
          <p style="color:var(--text-secondary); font-size: 1.05em; line-height: 1.6; margin-bottom: 20px;" data-i18n="${payload?.overall_recommendation?.score_desc_key}"></p>
          
          <div class="p-3 rounded" style="background:var(--bg-secondary);">
            <div style="font-size: 0.85em; color: var(--accent-primary); font-weight: bold; text-transform: uppercase; margin-bottom: 8px;" data-i18n="risk_analysis_overall_top_action"></div>
            <div class="d-flex align-items-center mb-2">
              <i class="bi bi-star-fill me-2" style="color: #ff9500;"></i>
              <strong style="color:var(--text-primary); font-size: 1.1em;" data-i18n="${payload?.overall_recommendation?.top_action_title_key}"></strong>
            </div>
            <div style="color:var(--text-secondary); padding-left: 28px;" data-i18n="${payload?.overall_recommendation?.top_action_desc_key}"></div>
          </div>
        </div>
      </div>
    </div>
`;
};
