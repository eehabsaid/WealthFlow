"use strict";

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
              <button class="btn btn-sm btn-outline-info" type="button" data-goal-action="edit" data-goal-id="${goal.id}" data-i18n="btn_edit"></button>
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
