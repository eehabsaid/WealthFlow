"use strict";

function _renderGoalPlanningChartSection(totalTarget) {
  return `
          <div class="portfolio-card mb-3">
            <div class="portfolio-card-title" data-i18n="goal_planning_distribution_title"></div>
            <div class="goal-chart-wrap">
              <canvas id="goalPlanningTypeChart"></canvas>
              <div class="goal-chart-center" aria-hidden="true">
                <span data-i18n="goal_planning_total_target"></span>
                <strong>${fmt(totalTarget)}</strong>
              </div>
            </div>
          </div>
  `;
}

function _renderGoalPlanningMilestonesSection(milestones) {
  return `
          <div class="portfolio-card">
            <div class="goal-panel-head">
              <div class="portfolio-card-title" data-i18n="goal_planning_milestones_title"></div>
              <button class="btn btn-sm btn-outline-light goal-calendar-btn" type="button" data-i18n="goal_planning_view_calendar"></button>
            </div>
            <div class="goal-milestone-list">
              ${
                milestones.length
                  ? milestones
                      .map(
                        (item) => `
                <div class="goal-milestone-item">
                  <div>
                    <div class="goal-milestone-title">${_escapeHtml(item.goal_name || t("goal_planning_not_available"))}</div>
                    <div class="goal-milestone-meta">
                      <span data-i18n="goal_planning_target_date"></span>: ${_escapeHtml(formatDate(item.target_date) || "-")}
                    </div>
                  </div>
                  <div class="goal-milestone-side">
                    <span class="portfolio-severity-badge portfolio-badge-info" data-i18n="${item.priority_key || "goal_planning_priority_medium"}"></span>
                    <small><span data-i18n="goal_planning_monthly_required"></span>: ${fmt(Number(item.monthly_required_egp || 0))} / <span data-i18n="goal_planning_months_short"></span></small>
                  </div>
                </div>
              `
                      )
                      .join("")
                  : `<div class="portfolio-empty-state" data-i18n="goal_planning_no_milestones"></div>`
              }
            </div>
          </div>
  `;
}

function _renderGoalPlanningInsightsSection(insights) {
  return `
          <div class="portfolio-card goal-insights-card h-100">
            <div class="portfolio-card-title" data-i18n="goal_planning_insights_title"></div>
            <div class="portfolio-rec-list">
              ${insights
                .map(
                  (item) => `
                <div class="portfolio-rec-item goal-insight-item">
                  <span class="goal-insight-icon" aria-hidden="true"><i class="bi bi-stars"></i></span>
                  <div class="portfolio-rec-text" data-i18n="${item.key}"></div>
                  <span class="portfolio-severity-badge ${_goalSeverityClass(item.severity)}" data-i18n="${item.severity_key}"></span>
                </div>
              `
                )
                .join("")}
            </div>
          </div>
  `;
}

function _renderGoalPlanningRecommendationsSection(recommendations) {
  return `
          <div class="portfolio-card goal-recommendations-card h-100">
            <div class="portfolio-card-title" data-i18n="goal_planning_recommendations_title"></div>
            <div class="portfolio-rec-list">
              ${recommendations
                .map(
                  (item) => `
                <div class="portfolio-rec-item goal-recommendation-item">
                  <span class="goal-rec-icon" aria-hidden="true"><i class="bi bi-lightning-charge"></i></span>
                  <div class="portfolio-rec-text" data-i18n="${item.key}"></div>
                  <span class="portfolio-severity-badge ${_goalSeverityClass(item.severity)}" data-i18n="${item.severity_key}"></span>
                </div>
              `
                )
                .join("")}
            </div>
          </div>
  `;
}

function _renderGoalPlanningLoading() {
  const pane = document.getElementById("fa-pane-goal-planning");
  if (!pane) return;
  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="goal_planning_loading"></div>
    </div>
  `;
  applyTranslations();
}

function _renderGoalPlanningError() {
  const pane = document.getElementById("fa-pane-goal-planning");
  if (!pane) return;
  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="goal_planning_error"></span>
    </div>
  `;
  applyTranslations();
}
