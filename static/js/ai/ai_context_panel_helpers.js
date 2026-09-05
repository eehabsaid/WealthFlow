"use strict";

/**
 * AI Workspace — Context Panel helpers.
 *
 * - _getApplicationModuleChips(): "Application Modules" chip source,
 *   derived live from the sidebar DOM (see below).
 * - _AI_WS_SOURCES_MAP: i18n label lookup for "Context Sources" chips.
 *
 * Depends on: sidebar.js (renderSidebar must have run at least once).
 */
function _getApplicationModuleChips() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return [];

  const chips = [];
  const seen = new Set();

  sidebar.querySelectorAll(".nav-item").forEach((item) => {
    // "welcome" is the logged-out/onboarding entry, not an app module.
    if (item.dataset.route === "welcome") return;

    const label = item.querySelector("[data-i18n]");
    if (!label) return;

    const i18nKey = label.getAttribute("data-i18n");
    if (seen.has(i18nKey)) return;
    seen.add(i18nKey);

    chips.push({ i18nKey, text: label.textContent.trim() });
  });

  return chips;
}

window._getApplicationModuleChips = _getApplicationModuleChips;

/**
 * Maps internal data/service keys (from AIMessage.sources and provider
 * registries — see core/services/financial_advisor/registry.py and
 * core/services/ai/providers/registry.py) to i18n labels for the
 * "Context Sources" chip list in the AI Workspace right panel.
 *
 * Any key not listed here still renders (ai_context_panel.js falls back
 * to the raw key name), so a gap here is a display-polish issue, not a
 * functional one — but keep this in sync with the two registries above
 * whenever a new advisor service or data provider is added.
 */
const _AI_WS_SOURCES_MAP = {
  overview: "ai_ws_source_overview",
  cash_flow: "ai_ws_source_cash_flow",
  goal_planning: "ai_ws_source_goal_planning",
  risk_analysis: "ai_ws_source_risk_analysis",
  // Reuse the existing Financial Advisor tab labels (already translated in
  // all 4 locales) instead of duplicating new ai_ws_source_* keys.
  wealth_growth: "financial_advisor_tab_wealth_growth",
  portfolio_optimizer: "financial_advisor_tab_portfolio_optimizer",
  spending_intelligence: "financial_advisor_tab_spending_intelligence",
  opportunity_detection: "financial_advisor_tab_opportunity_detection",
  performance: "financial_advisor_tab_performance",
  what_if_simulator: "financial_advisor_tab_what_if_simulator",
  scenario_planner: "financial_advisor_tab_scenario_planner",
  balance: "ai_ws_source_balance",
  bank_certificates: "ai_ws_source_certificates",
  expenses: "ai_ws_source_expenses",
  salary: "ai_ws_source_employment",
  gold: "ai_ws_source_gold",
  fixed_assets: "ai_ws_source_fixed_assets",
  market_data: "ai_ws_source_market_data",
};

window._AI_WS_SOURCES_MAP = _AI_WS_SOURCES_MAP;
