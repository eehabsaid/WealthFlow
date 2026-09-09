"use strict";
// Goal Planning tab — main render orchestrator and data loader. Split out
// into sibling files (200-line backlog): goal_planning_cards.js,
// goal_planning_modal.js, goal_planning_modal_events.js. This file is the
// orchestrator, calling the extracted helpers in place of the original
// inline closures.
// ════════════════════════════════════════════════════════════════════════════

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
  const atRiskCount = goals.filter(
    (goal) => goal.status === "at_risk" || goal.status === "critical" || goal.status === "watch"
  ).length;
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
  const filterEls = { searchInput, priorityFilter, typeFilter, statusFilter, dueDateFilter, sortBy };

  const drawGoalCards = () => renderGoalCardsList(cardsContainer, goals, filterEls);

  drawGoalCards();
  [searchInput, typeFilter, priorityFilter, statusFilter, dueDateFilter, sortBy].forEach((el) => {
    if (!el) return;
    el.addEventListener("input", drawGoalCards);
    el.addEventListener("change", drawGoalCards);
  });

  const modalEls = setupGoalModal();
  wireGoalModalEvents(cardsContainer, goals, modalEls);

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
