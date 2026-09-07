"use strict";
// Financial Scenario Planner tab logic
// Split from the former monolithic scenario_planner.js (200-line rule).
// Sibling files (load order does not matter at runtime, all attach to
// window.SP before any user interaction triggers a call):
// - state.js                     Shared window.SP.state + money/delta format helpers
// - api.js                       Event schema + scenario list fetch, backend recalculation
// - render_view.js               Top-level pane view renderer
// - render_timeline_rail.js      Timeline chart HTML + scenario selector rail
// - render_builder.js            Scenario builder sub-tab pane
// - render_dashboard.js          Dashboard sub-tab pane + KPI badge helper
// - render_compare_insights.js   Compare + insights sub-tab panes
// - events.js                    DOM event listener wiring for the pane
// - modal_actions.js             New/duplicate/delete scenario + event CRUD actions

window.SP = window.SP || {};
window.SP.state = {
  scenarioPlannerData: null,
  cachedScenarios: [],
  cachedEventSchema: null,
  cachedEventSchemaVersion: null,
  activeScenarioId: null,
  selectedScenarioIds: [],
  activeSubTab: "dashboard", // "builder" | "dashboard" | "compare" | "insights"
  selectedEventType: "house",
  debounceTimer: null,
  themeListenerAttached: false,
};

  window.SP.money = function(value) {
    const num = Number(value) || 0;
    if (typeof fmtpresent === "function") {
      return fmtpresent(num);
    }
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  window.SP.fmtDelta = function(val, isPct = false, digits = 1) {
    if (val === null || val === undefined) return "-";
    const num = Number(val) || 0;
    const sign = num > 0 ? "+" : "";
    if (isPct) return `${sign}${num.toFixed(digits)}%`;
    if (typeof fmtpresent === "function") {
      return `${sign}${fmtpresent(num)}`;
    }
    return `${sign}${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  window.SP.attachThemeListener = function() {
    if (window.SP.state.themeListenerAttached) return;
    window.addEventListener("themeChanged", () => {
      if (window.SP.state.scenarioPlannerData && typeof _renderScenarioPlannerChart === "function") {
        _renderScenarioPlannerChart(window.SP.state.scenarioPlannerData);
      }
    });
    window.SP.state.themeListenerAttached = true;
  }

