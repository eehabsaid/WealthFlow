"use strict";

function _renderGoalPlanningHeader(payload) {
  return `
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div style="color:var(--text-secondary);" data-i18n="goal_planning_subtitle"></div>
        <div class="goal-header-actions">
          <div class="portfolio-optimizer-date">
            <span data-i18n="goal_planning_as_of"></span>
            <strong>${payload?.as_of || "-"}</strong>
          </div>
          <button class="btn btn-primary btn-sm" id="btnAddGoal">
            <i class="bi bi-plus-lg"></i>
            <span data-i18n="goal_planning_add_goal"></span>
          </button>
        </div>
      </div>
  `;
}

function _renderGoalPlanningKPIs(summary, completedCount, onTrackCount, atRiskCount, totalTarget, totalSaved, completedPct, onTrackPct, atRiskPct, savedTargetPct) {
  return `
      <div class="goal-kpi-grid mb-3">
        <div class="goal-kpi-card">
          <div class="goal-kpi-head"><span class="goal-kpi-icon" aria-hidden="true"><i class="bi bi-bullseye"></i></span><span data-i18n="goal_planning_total_goals"></span></div>
          <strong>${Number(summary.total_goals || 0)}</strong>
          <small data-i18n="goal_planning_all_goals"></small>
        </div>
        <div class="goal-kpi-card">
          <div class="goal-kpi-head"><span class="goal-kpi-icon" aria-hidden="true"><i class="bi bi-check2-circle"></i></span><span data-i18n="goal_planning_achieved_goals"></span></div>
          <strong>${completedCount}</strong>
          <small>${fmtpresent(completedPct)}%</small>
        </div>
        <div class="goal-kpi-card">
          <div class="goal-kpi-head"><span class="goal-kpi-icon" aria-hidden="true"><i class="bi bi-graph-up-arrow"></i></span><span data-i18n="goal_planning_on_track_goals"></span></div>
          <strong>${onTrackCount}</strong>
          <small>${fmtpresent(onTrackPct)}%</small>
        </div>
        <div class="goal-kpi-card">
          <div class="goal-kpi-head"><span class="goal-kpi-icon" aria-hidden="true"><i class="bi bi-exclamation-triangle"></i></span><span data-i18n="goal_planning_at_risk_goals"></span></div>
          <strong>${atRiskCount}</strong>
          <small>${fmtpresent(atRiskPct)}%</small>
        </div>
        <div class="goal-kpi-card">
          <div class="goal-kpi-head"><span class="goal-kpi-icon" aria-hidden="true"><i class="bi bi-wallet2"></i></span><span data-i18n="goal_planning_total_target"></span></div>
          <strong>${fmt(totalTarget)}</strong>
          <small data-i18n="goal_planning_goal_value"></small>
        </div>
        <div class="goal-kpi-card">
          <div class="goal-kpi-head"><span class="goal-kpi-icon" aria-hidden="true"><i class="bi bi-piggy-bank"></i></span><span data-i18n="goal_planning_total_saved"></span></div>
          <strong>${fmt(totalSaved)}</strong>
          <small>${fmtpresent(savedTargetPct)}% <span data-i18n="goal_planning_of_target"></span></small>
        </div>
      </div>
  `;
}

function _renderGoalPlanningCardsSection(goals) {
  return `
          <div class="portfolio-card h-100">
            <div class="goal-toolbar mb-2">
              <div class="goal-toolbar-left">
                <input id="goalSearchInput" class="form-control form-control-sm" type="text" placeholder="${_escapeHtml(t("goal_planning_search_placeholder"))}">
                <select id="goalTypeFilter" class="form-select form-select-sm">
                  <option value="all">${_escapeHtml(t("goal_planning_filter_all_categories"))}</option>
                  ${Array.from(new Set(goals.map((goal) => String(goal.goal_type || "").trim()).filter(Boolean))).sort().map((goalType) => `<option value="${_escapeHtml(goalType)}">${_escapeHtml(goalType)}</option>`).join("")}
                </select>
                <select id="goalStatusFilter" class="form-select form-select-sm">
                  <option value="all">${_escapeHtml(t("goal_planning_filter_all_statuses"))}</option>
                  <option value="on_track">${_escapeHtml(t("goal_planning_status_on_track"))}</option>
                  <option value="watch">${_escapeHtml(t("goal_planning_status_needs_attention"))}</option>
                  <option value="at_risk">${_escapeHtml(t("goal_planning_status_at_risk"))}</option>
                  <option value="critical">${_escapeHtml(t("goal_planning_status_overdue"))}</option>
                  <option value="achieved">${_escapeHtml(t("goal_planning_status_achieved"))}</option>
                </select>
                <select id="goalPriorityFilter" class="form-select form-select-sm">
                  <option value="all">${_escapeHtml(t("goal_planning_filter_all_priorities"))}</option>
                  <option value="High">${_escapeHtml(t("goal_planning_priority_high"))}</option>
                  <option value="Medium">${_escapeHtml(t("goal_planning_priority_medium"))}</option>
                  <option value="Low">${_escapeHtml(t("goal_planning_priority_low"))}</option>
                </select>
                <select id="goalDueDateFilter" class="form-select form-select-sm">
                  <option value="all">${_escapeHtml(t("goal_planning_filter_all_due_dates"))}</option>
                  <option value="6">${_escapeHtml(t("goal_planning_filter_due_6"))}</option>
                  <option value="12">${_escapeHtml(t("goal_planning_filter_due_12"))}</option>
                  <option value="24">${_escapeHtml(t("goal_planning_filter_due_24"))}</option>
                </select>
                <select id="goalSortBy" class="form-select form-select-sm">
                  <option value="priority">${_escapeHtml(t("goal_planning_sort_priority"))}</option>
                  <option value="deadline">${_escapeHtml(t("goal_planning_sort_deadline"))}</option>
                  <option value="progress">${_escapeHtml(t("goal_planning_sort_progress"))}</option>
                  <option value="remaining">${_escapeHtml(t("goal_planning_sort_remaining"))}</option>
                </select>
              </div>
            </div>
            <div class="goal-section-caption" data-i18n="goal_planning_your_goals"></div>
            <div id="goalCardsContainer" class="goal-cards-grid"></div>
          </div>
  `;
}

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
              ${milestones.length ? milestones.map((item) => `
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
              `).join("") : `<div class="portfolio-empty-state" data-i18n="goal_planning_no_milestones"></div>`}
            </div>
          </div>
  `;
}

function _renderGoalPlanningInsightsSection(insights) {
  return `
          <div class="portfolio-card goal-insights-card h-100">
            <div class="portfolio-card-title" data-i18n="goal_planning_insights_title"></div>
            <div class="portfolio-rec-list">
              ${insights.map((item) => `
                <div class="portfolio-rec-item goal-insight-item">
                  <span class="goal-insight-icon" aria-hidden="true"><i class="bi bi-stars"></i></span>
                  <div class="portfolio-rec-text" data-i18n="${item.key}"></div>
                  <span class="portfolio-severity-badge ${_goalSeverityClass(item.severity)}" data-i18n="${item.severity_key}"></span>
                </div>
              `).join("")}
            </div>
          </div>
  `;
}

function _renderGoalPlanningRecommendationsSection(recommendations) {
  return `
          <div class="portfolio-card goal-recommendations-card h-100">
            <div class="portfolio-card-title" data-i18n="goal_planning_recommendations_title"></div>
            <div class="portfolio-rec-list">
              ${recommendations.map((item) => `
                <div class="portfolio-rec-item goal-recommendation-item">
                  <span class="goal-rec-icon" aria-hidden="true"><i class="bi bi-lightning-charge"></i></span>
                  <div class="portfolio-rec-text" data-i18n="${item.key}"></div>
                  <span class="portfolio-severity-badge ${_goalSeverityClass(item.severity)}" data-i18n="${item.severity_key}"></span>
                </div>
              `).join("")}
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
