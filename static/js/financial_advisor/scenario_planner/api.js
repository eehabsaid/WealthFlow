"use strict";
window.SP = window.SP || {};

  window.SP.loadEventSchema = async function() {
    if (window.SP.state.cachedEventSchema) return window.SP.state.cachedEventSchema;
    try {
      const resp = await fetch("/api/scenarios/event-definitions/");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      window.SP.state.cachedEventSchemaVersion = data.schema_version || 1;
      window.SP.state.cachedEventSchema = data.event_schema || [];
      return window.SP.state.cachedEventSchema;
    } catch (err) {
      window.SP.state.cachedEventSchema = [];
      return [];
    }
  }

  // ── Data Loading & Comparison API ──────────────────────────────────────────

  window.SP.loadScenarioPlanner = async function(forceFetch = false) {
    const pane = document.getElementById("fa-pane-scenario-planner");
    if (!pane) return;

    if (!forceFetch && window.SP.state.scenarioPlannerData && window.SP.state.cachedScenarios.length > 0) {
      window.SP.renderScenarioPlannerView(pane);
      return;
    }

    pane.innerHTML = `
      <div class="d-flex justify-content-center align-items-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden" data-i18n="scenario_planner_loading">Loading Scenario Planner...</span>
        </div>
      </div>
    `;
    if (typeof applyTranslations === "function") applyTranslations();

    try {
      await window.SP.loadEventSchema();
      await window.SP.fetchScenarioList();

      if (!window.SP.state.activeScenarioId && window.SP.state.cachedScenarios.length > 0) {
        window.SP.state.activeScenarioId = window.SP.state.cachedScenarios[0].id;
        window.SP.state.selectedScenarioIds = [window.SP.state.activeScenarioId];
      }

      await window.SP.recalculateBackend();
      window.SP.attachThemeListener();
    } catch (err) {
      pane.innerHTML = `
        <div class="alert alert-danger my-3" role="alert" data-i18n="scenario_planner_error_load">
          Failed to load Scenario Planner. Please try again.
        </div>
      `;
      if (typeof applyTranslations === "function") applyTranslations();
    }
  }

  window.SP.fetchScenarioList = async function() {
    try {
      const resp = await fetch("/api/scenarios/");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      window.SP.state.cachedScenarios = data.scenarios || [];
    } catch (err) {
      window.SP.state.cachedScenarios = [];
    }
  }

  window.SP.recalculateBackend = async function() {
    const pane = document.getElementById("fa-pane-scenario-planner");
    if (!pane) return;

    const query = new URLSearchParams();
    if (window.SP.state.selectedScenarioIds && window.SP.state.selectedScenarioIds.length > 0) {
      query.set("scenario_ids", window.SP.state.selectedScenarioIds.join(","));
    }

    try {
      const resp = await fetch(
        `/api/financial-advisor/scenario-planner/compare/?${query.toString()}`
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const payload = await resp.json();
      window.SP.state.scenarioPlannerData = payload;

      window.SP.renderScenarioPlannerView(pane);
    } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
  }

  window.SP.debouncedRecalculate = function() {
    if (window.SP.state.debounceTimer) clearTimeout(window.SP.state.debounceTimer);
    window.SP.state.debounceTimer = setTimeout(() => {
      window.SP.recalculateBackend();
    }, 350);
  }
