"use strict";
// Financial advisor entry-point exports.
// This file is part of the financial_advisor module. Do not edit directly.
// Split out of the original financial_advisor/index.js monolith to stay
// under the 200-line-per-file ceiling. Structural split only - no logic
// changes.
//
// Siblings (loaded before this file, in templates/index.html):
// - tab_panes.js: _renderFATabPane(tab, activeTabId) - per-tab pane HTML.
// - render.js: renderFinancialAdvisor() - main page render and tab wiring.
//
// This file only re-exports functions already defined by the files above
// (and by the other financial_advisor/*.js loaders) onto window.

window.renderFinancialAdvisor = renderFinancialAdvisor;

// ════════════════════════════════════════════════════════════════════════════
// GLOBAL WINDOW EXPORTS FOR HTML BACKWARD COMPATIBILITY
// ════════════════════════════════════════════════════════════════════════════

window.renderFinancialAdvisor = renderFinancialAdvisor;
window.loadOverview = loadOverview;
window.loadCashFlowForecast = loadCashFlowForecast;
window.loadWealthGrowthForecast = loadWealthGrowthForecast;
window.loadPortfolioOptimizer = loadPortfolioOptimizer;
window.loadGoalPlanning = loadGoalPlanning;
window.loadRiskAnalysis =
  typeof loadRiskAnalysis !== "undefined"
    ? loadRiskAnalysis
    : window.loadRiskAnalysis || (() => {});
window.loadSpendingIntelligence =
  typeof loadSpendingIntelligence !== "undefined"
    ? loadSpendingIntelligence
    : window.loadSpendingIntelligence || (() => {});
window.loadOpportunityDetection =
  typeof loadOpportunityDetection !== "undefined"
    ? loadOpportunityDetection
    : window.loadOpportunityDetection || (() => {});
window.loadPerformance =
  typeof loadPerformance !== "undefined" ? loadPerformance : window.loadPerformance || (() => {});
window.loadWhatIfSimulator =
  typeof loadWhatIfSimulator !== "undefined"
    ? loadWhatIfSimulator
    : window.loadWhatIfSimulator || (() => {});
window.loadScenarioPlanner =
  typeof loadScenarioPlanner !== "undefined"
    ? loadScenarioPlanner
    : window.loadScenarioPlanner || (() => {});
