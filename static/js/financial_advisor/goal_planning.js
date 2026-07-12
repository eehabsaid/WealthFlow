"use strict";
// Goal planning tab rendering, load, edit, save, and delete handlers
// This file is part of the financial_advisor module. Do not edit directly.

function _renderGoalPlanningHeader(payload) {
  return `
      <div class="goal-planning-header">
        <div>
          <h4 data-i18n="financial_advisor_tab_goal_planning"></h4>
          <p data-i18n="goal_planning_subtitle"></p>
        </div>
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
                      <span data-i18n="goal_planning_target_date"></span>: ${_escapeHtml(item.target_date || "-")}
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

function _renderGoalPlanningModalSection() {
  return `
      <div class="modal fade goal-editor-modal" id="goalEditorModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
          <div class="modal-content goal-editor-surface" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
            <div class="modal-header goal-editor-header" style="border-bottom:1px solid var(--border-color);">
              <h5 class="modal-title" id="goalEditorTitle" data-i18n="goal_planning_create_title"></h5>
              <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
              <form id="goalEditorForm" class="row g-3 goal-editor-form">
                <input type="hidden" id="goalIdInput">
                <div class="col-12 col-md-6 goal-field goal-field-half">
                  <label class="form-label" data-i18n="goal_planning_field_name"></label>
                  <input type="text" class="form-control" id="goalNameInput" required>
                </div>
                <div class="col-12 col-md-6 goal-field goal-field-half">
                  <label class="form-label" data-i18n="goal_planning_field_type"></label>
                  <input type="text" class="form-control" id="goalTypeInput" required>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_target_amount"></label>
                  <input type="number" min="0" step="0.01" class="form-control" id="goalTargetAmountInput" required>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_saved_amount"></label>
                  <input type="number" min="0" step="0.01" class="form-control" id="goalSavedAmountInput" required>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_target_date"></label>
                  <input type="date" class="form-control" id="goalTargetDateInput">
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_currency"></label>
                  <select class="form-select" id="goalCurrencyInput"></select>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_priority"></label>
                  <select class="form-select" id="goalPriorityInput">
                    <option value="High">${_escapeHtml(t("goal_planning_priority_high"))}</option>
                    <option value="Medium">${_escapeHtml(t("goal_planning_priority_medium"))}</option>
                    <option value="Low">${_escapeHtml(t("goal_planning_priority_low"))}</option>
                  </select>
                </div>
                <div class="col-12 col-md-4 goal-field goal-field-third">
                  <label class="form-label" data-i18n="goal_planning_field_linked_asset"></label>
                  <select class="form-select" id="goalLinkedAssetInput"></select>
                </div>
                <div class="col-12 goal-field goal-field-full">
                  <label class="form-label" data-i18n="goal_planning_field_notes"></label>
                  <textarea class="form-control" rows="3" id="goalNotesInput"></textarea>
                </div>
              </form>
            </div>
            <div class="modal-footer goal-editor-footer" style="border-top:1px solid var(--border-color);">
              <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal" data-i18n="btn_cancel"></button>
              <button type="button" class="btn btn-primary" id="btnSaveGoal" data-i18n="btn_save"></button>
            </div>
          </div>
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

function _renderGoalPlanning(payload) {
  const pane = document.getElementById("fa-pane-goal-planning");
  if (!pane) return;

  const summary = payload?.summary || {};
  const goals = payload?.goals || [];
  const milestones = payload?.milestones || [];
  const insights = payload?.insights || [];
  const recommendations = payload?.recommendations || [];
  const totalTarget = Number(summary.total_target_egp || 0);
  const totalSaved = Number(summary.total_saved_egp || 0);
  const completedCount = goals.filter((goal) => goal.status === "achieved").length;
  const onTrackCount = goals.filter((goal) => goal.status === "on_track").length;
  const atRiskCount = goals.filter((goal) => goal.status === "at_risk" || goal.status === "critical" || goal.status === "watch").length;
  const completedPct = goals.length ? (completedCount / goals.length) * 100 : 0;
  const onTrackPct = goals.length ? (onTrackCount / goals.length) * 100 : 0;
  const atRiskPct = goals.length ? (atRiskCount / goals.length) * 100 : 0;
  const savedTargetPct = totalTarget > 0 ? (totalSaved / totalTarget) * 100 : 0;

  pane.innerHTML = `
    <div class="goal-planning-wrap goal-planning-hero">
      ${_renderGoalPlanningHeader(payload)}
      ${_renderGoalPlanningKPIs(summary, completedCount, onTrackCount, atRiskCount, totalTarget, totalSaved, completedPct, onTrackPct, atRiskPct, savedTargetPct)}

      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-8">
          ${_renderGoalPlanningCardsSection(goals)}
        </div>

        <div class="col-12 col-xl-4">
          ${_renderGoalPlanningChartSection(totalTarget)}
          ${_renderGoalPlanningMilestonesSection(milestones)}
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-lg-6">
          ${_renderGoalPlanningInsightsSection(insights)}
        </div>
        <div class="col-12 col-lg-6">
          ${_renderGoalPlanningRecommendationsSection(recommendations)}
        </div>
      </div>

      ${_renderGoalPlanningModalSection()}
    </div>
  `;

  const cardsContainer = document.getElementById("goalCardsContainer");
  const searchInput = document.getElementById("goalSearchInput");
  const typeFilter = document.getElementById("goalTypeFilter");
  const priorityFilter = document.getElementById("goalPriorityFilter");
  const statusFilter = document.getElementById("goalStatusFilter");
  const dueDateFilter = document.getElementById("goalDueDateFilter");
  const sortBy = document.getElementById("goalSortBy");

  const drawGoalCards = () => {
    if (!cardsContainer) return;
    const q = (searchInput?.value || "").trim().toLowerCase();
    const p = priorityFilter?.value || "all";
    const goalType = typeFilter?.value || "all";
    const s = statusFilter?.value || "all";
    const dueLimit = Number(dueDateFilter?.value || 0);
    const sort = sortBy?.value || "priority";

    let filtered = goals.filter((goal) => {
      const matchesText = !q
        || String(goal.name || "").toLowerCase().includes(q)
        || String(goal.goal_type || "").toLowerCase().includes(q);
      const matchesPriority = p === "all" || goal.priority === p;
      const matchesType = goalType === "all" || String(goal.goal_type || "") === goalType;
      const matchesStatus = s === "all" || goal.status === s;
      const matchesDue = !dueLimit || Number(goal.months_left || 9999) <= dueLimit;
      return matchesText && matchesPriority && matchesType && matchesStatus && matchesDue;
    });

    filtered.sort((a, b) => {
      if (sort === "deadline") {
        const aVal = a.target_date || "9999-12-31";
        const bVal = b.target_date || "9999-12-31";
        return aVal.localeCompare(bVal);
      }
      if (sort === "progress") {
        return Number(b.progress_pct || 0) - Number(a.progress_pct || 0);
      }
      if (sort === "remaining") {
        return Number(b.remaining_amount_egp || 0) - Number(a.remaining_amount_egp || 0);
      }
      const aRank = _goalPriorityRank(a.priority);
      const bRank = _goalPriorityRank(b.priority);
      if (aRank !== bRank) return aRank - bRank;
      return Number(a.months_left || 9999) - Number(b.months_left || 9999);
    });

    cardsContainer.innerHTML = filtered.length
      ? filtered.map((goal) => `
        <div class="goal-card">
          <div class="goal-card-head">
            <div class="goal-card-heading">
              <div class="goal-type-icon"><i class="bi ${_goalTypeIcon(goal.goal_type)}"></i></div>
              <div>
              <div class="goal-card-title">${_escapeHtml(goal.name || t("goal_planning_not_available"))}</div>
              <div class="goal-card-sub">${_escapeHtml(goal.goal_type || "-")}</div>
              </div>
            </div>
            <span class="portfolio-severity-badge ${_goalStatusClass(goal.status)}" data-i18n="${goal.status_key}"></span>
          </div>

          <div class="goal-card-meta">
            <span data-i18n="goal_planning_target_amount"></span>
            <strong>${fmt(Number(goal.target_amount_egp || 0))}</strong>
          </div>
          <div class="goal-card-meta goal-card-meta-strong">
            <span data-i18n="goal_planning_saved_amount"></span>
            <strong>${fmt(Number(goal.current_saved_egp || 0))}</strong>
          </div>
          <div class="goal-card-meta goal-card-meta-strong">
            <span data-i18n="goal_planning_remaining_amount"></span>
            <strong>${fmt(Number(goal.remaining_amount_egp || 0))}</strong>
          </div>
          <div class="goal-card-meta goal-card-meta-strong">
            <span data-i18n="goal_planning_monthly_required"></span>
            <strong>${fmt(Number(goal.monthly_required_egp || 0))}</strong>
          </div>
          <div class="goal-card-meta">
            <span data-i18n="goal_planning_time_left"></span>
            <strong>${Number(goal.months_left || 0)} <span data-i18n="goal_planning_months_short"></span></strong>
          </div>

          <div class="goal-progress-row">
            <div class="goal-progress-track">
              <div class="goal-progress-fill" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.max(0, Math.min(100, Number(goal.progress_pct || 0)))}" style="--goal-progress:${Math.max(0, Math.min(100, Number(goal.progress_pct || 0)))}%"></div>
            </div>
            <div class="goal-progress-label">${fmtpresent(Number(goal.progress_pct || 0))}%</div>
          </div>

          <div class="goal-card-footer">
            <span class="portfolio-severity-badge portfolio-badge-info" data-i18n="${goal.priority_key || "goal_planning_priority_medium"}"></span>
            <div class="goal-actions">
              <button class="btn btn-sm btn-outline-info" type="button" data-goal-action="view" data-goal-id="${goal.id}" data-i18n="goal_planning_view_details"></button>
              <button class="btn btn-sm btn-outline-light" type="button" data-goal-action="edit" data-goal-id="${goal.id}" data-i18n="btn_edit"></button>
              <button class="btn btn-sm btn-outline-danger" type="button" data-goal-action="delete" data-goal-id="${goal.id}" data-i18n="btn_delete"></button>
            </div>
          </div>
        </div>
      `).join("")
      : `<div class="portfolio-empty-state" data-i18n="goal_planning_empty"></div>`;

    applyTranslations();
  };

  drawGoalCards();
  [searchInput, typeFilter, priorityFilter, statusFilter, dueDateFilter, sortBy].forEach((el) => {
    if (!el) return;
    el.addEventListener("input", drawGoalCards);
    el.addEventListener("change", drawGoalCards);
  });

  const meta = _goalPlanningMeta || { currencies: [], assets: [] };
  const modalEl = document.getElementById("goalEditorModal");
  const modal = modalEl && window.bootstrap
    ? new bootstrap.Modal(modalEl, { backdrop: "static", keyboard: false, focus: true })
    : null;

  const currencySelect = document.getElementById("goalCurrencyInput");
  const linkedAssetSelect = document.getElementById("goalLinkedAssetInput");
  if (currencySelect) {
    currencySelect.innerHTML = (meta.currencies || []).map((item) => `
      <option value="${item.id}">${_escapeHtml(item.code || "EGP")}${item.symbol ? ` (${_escapeHtml(item.symbol)})` : ""}</option>
    `).join("");
  }
  if (linkedAssetSelect) {
    linkedAssetSelect.innerHTML = `
      <option value="">${_escapeHtml(t("goal_planning_none"))}</option>
      ${(meta.assets || []).map((item) => `<option value="${item.id}">${_escapeHtml(item.name || "-")}</option>`).join("")}
    `;
  }

  const openGoalModal = (goalItem) => {
    const title = document.getElementById("goalEditorTitle");
    const idInput = document.getElementById("goalIdInput");
    const nameInput = document.getElementById("goalNameInput");
    const typeInput = document.getElementById("goalTypeInput");
    const targetInput = document.getElementById("goalTargetAmountInput");
    const savedInput = document.getElementById("goalSavedAmountInput");
    const dateInput = document.getElementById("goalTargetDateInput");
    const priorityInput = document.getElementById("goalPriorityInput");
    const notesInput = document.getElementById("goalNotesInput");

    if (!title || !idInput || !nameInput || !typeInput || !targetInput || !savedInput || !dateInput || !priorityInput || !notesInput || !currencySelect || !linkedAssetSelect || !modal) {
      return;
    }

    if (goalItem) {
      title.setAttribute("data-i18n", "goal_planning_edit_title");
      idInput.value = String(goalItem.id || "");
      nameInput.value = goalItem.name || "";
      typeInput.value = goalItem.goal_type || "";
      targetInput.value = Number(goalItem.target_amount || 0);
      savedInput.value = Number(goalItem.current_saved_amount || 0);
      dateInput.value = goalItem.target_date || "";
      priorityInput.value = goalItem.priority || "Medium";
      notesInput.value = goalItem.notes || "";
      currencySelect.value = goalItem.currency_id ? String(goalItem.currency_id) : (currencySelect.options[0]?.value || "");
      linkedAssetSelect.value = goalItem.linked_asset_id ? String(goalItem.linked_asset_id) : "";
    } else {
      title.setAttribute("data-i18n", "goal_planning_create_title");
      idInput.value = "";
      nameInput.value = "";
      typeInput.value = "";
      targetInput.value = "0";
      savedInput.value = "0";
      dateInput.value = "";
      priorityInput.value = "Medium";
      notesInput.value = "";
      currencySelect.value = currencySelect.options[0]?.value || "";
      linkedAssetSelect.value = "";
    }

    applyTranslations();
    modal.show();
  };

  const addBtn = document.getElementById("btnAddGoal");
  if (addBtn) {
    addBtn.addEventListener("click", () => openGoalModal(null));
  }

  if (cardsContainer) {
    cardsContainer.addEventListener("click", async (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const actionEl = target.closest("[data-goal-action]");
      if (!(actionEl instanceof HTMLElement)) return;
      const action = actionEl.getAttribute("data-goal-action");
      const goalId = Number(actionEl.getAttribute("data-goal-id") || 0);
      if (!goalId) return;

      if (action === "edit") {
        try {
          const response = await fetch(`/api/goals/`);
          const data = await response.json();
          const rawGoal = (data.goals || []).find((item) => Number(item.id) === goalId);
          if (rawGoal) openGoalModal(rawGoal);
        } catch (_error) {
          showToast(t("goal_planning_error"), "error");
        }
        return;
      }

      if (action === "view") {
        showToast(`${t("goal_planning_target_amount")}: ${fmt(Number((goals.find((goal) => Number(goal.id) === goalId)?.target_amount_egp) || 0))}`);
        return;
      }

      if (action === "delete") {
        const okay = window.confirm(t("goal_planning_delete_confirm"));
        if (!okay) return;
        try {
          const response = await fetch(`/api/goals/${goalId}/`, { method: "DELETE" });
          if (!response.ok) throw new Error("goal_delete_failed");
          await loadGoalPlanning(true);
          showToast(t("goal_planning_deleted"));
        } catch (_error) {
          showToast(t("goal_planning_save_error"), "error");
        }
      }
    });
  }

  const saveBtn = document.getElementById("btnSaveGoal");
  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const idInput = document.getElementById("goalIdInput");
      const nameInput = document.getElementById("goalNameInput");
      const typeInput = document.getElementById("goalTypeInput");
      const targetInput = document.getElementById("goalTargetAmountInput");
      const savedInput = document.getElementById("goalSavedAmountInput");
      const dateInput = document.getElementById("goalTargetDateInput");
      const priorityInput = document.getElementById("goalPriorityInput");
      const notesInput = document.getElementById("goalNotesInput");

      if (!idInput || !nameInput || !typeInput || !targetInput || !savedInput || !dateInput || !priorityInput || !notesInput || !currencySelect || !linkedAssetSelect) {
        return;
      }

      const payloadBody = {
        name: nameInput.value.trim(),
        goal_type: typeInput.value.trim(),
        target_amount: Number(targetInput.value || 0),
        current_saved_amount: Number(savedInput.value || 0),
        target_date: dateInput.value || null,
        currency_id: currencySelect.value ? Number(currencySelect.value) : null,
        linked_asset_id: linkedAssetSelect.value ? Number(linkedAssetSelect.value) : null,
        priority: priorityInput.value || "Medium",
        notes: notesInput.value || "",
      };

      if (!payloadBody.name || !payloadBody.goal_type) {
        showToast(t("goal_planning_validation_required"), "error");
        return;
      }

      const goalId = Number(idInput.value || 0);
      const url = goalId ? `/api/goals/${goalId}/` : "/api/goals/";
      const method = goalId ? "PUT" : "POST";

      try {
        const response = await fetch(url, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payloadBody),
        });
        if (!response.ok) throw new Error("goal_save_failed");
        if (modal) modal.hide();
        await loadGoalPlanning(true);
        showToast(t("goal_planning_saved"));
      } catch (_error) {
        showToast(t("goal_planning_save_error"), "error");
      }
    });
  }

  _drawGoalTypeChart(payload);
  applyTranslations();
}

async function loadGoalPlanning(force = false) {
  if (_goalPlanningData && !force) {
    _renderGoalPlanning(_goalPlanningData);
    _goalPlanningLoaded = true;
    return;
  }

  _renderGoalPlanningLoading();
  try {
    const [payloadRes, currenciesRes, assetsRes] = await Promise.all([
      fetch("/api/financial-advisor/goal-planning/"),
      fetch("/api/currencies/"),
      fetch("/api/fixed-assets/"),
    ]);

    if (!payloadRes.ok) {
      throw new Error("goal_planning_fetch_failed");
    }

    const payload = await payloadRes.json();
    const currenciesPayload = currenciesRes.ok ? await currenciesRes.json() : { currencies: [] };
    const assetsPayload = assetsRes.ok ? await assetsRes.json() : { assets: [] };

    _goalPlanningMeta = {
      currencies: currenciesPayload?.currencies || [],
      assets: assetsPayload?.assets || [],
    };
    _goalPlanningData = payload;
    _renderGoalPlanning(payload);
    _goalPlanningLoaded = true;
  } catch (_error) {
    _renderGoalPlanningError();
  }
}

