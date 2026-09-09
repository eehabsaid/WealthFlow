"use strict";
// Goal Planning tab — card list filtering, sorting, and HTML rendering.
// Split out of goal_planning.js (200-line backlog). Bare globals; converted
// from a closure inside _renderGoalPlanning to standalone functions taking
// explicit params (goals array + current filter/sort values).
// ════════════════════════════════════════════════════════════════════════════

function filterAndSortGoals(goals, opts) {
  const { q, p, goalType, s, dueLimit, sort } = opts;

  let filtered = goals.filter((goal) => {
    const matchesText =
      !q ||
      String(goal.name || "")
        .toLowerCase()
        .includes(q) ||
      String(goal.goal_type || "")
        .toLowerCase()
        .includes(q);
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

  return filtered;
}

function buildGoalCardsHtml(filtered) {
  return filtered.length
    ? filtered
        .map(
          (goal) => `
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
              <button class="btn btn-sm btn-outline-info" type="button" data-goal-action="edit" data-goal-id="${goal.id}" data-i18n="btn_edit"></button>
              <button class="btn btn-sm btn-outline-danger" type="button" data-goal-action="delete" data-goal-id="${goal.id}" data-i18n="btn_delete"></button>
            </div>
          </div>
        </div>
      `
        )
        .join("")
    : `<div class="portfolio-empty-state" data-i18n="goal_planning_empty"></div>`;
}

function renderGoalCardsList(cardsContainer, goals, els) {
  if (!cardsContainer) return;
  const { searchInput, priorityFilter, typeFilter, statusFilter, dueDateFilter, sortBy } = els;
  const opts = {
    q: (searchInput?.value || "").trim().toLowerCase(),
    p: priorityFilter?.value || "all",
    goalType: typeFilter?.value || "all",
    s: statusFilter?.value || "all",
    dueLimit: Number(dueDateFilter?.value || 0),
    sort: sortBy?.value || "priority",
  };
  const filtered = filterAndSortGoals(goals, opts);
  cardsContainer.innerHTML = buildGoalCardsHtml(filtered);
  applyTranslations();
}
