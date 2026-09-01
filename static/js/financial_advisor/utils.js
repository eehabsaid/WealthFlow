"use strict";

const FINANCIAL_ADVISOR_TABS = [
  {
    id: "overview",
    key: "financial_advisor_tab_overview",
    shortKey: "financial_advisor_tab_overview",
  },
  {
    id: "cash-flow-forecast",
    key: "financial_advisor_tab_cash_flow_forecast",
    shortKey: "financial_advisor_tab_cash_flow",
  },
  {
    id: "wealth-growth-forecast",
    key: "financial_advisor_tab_wealth_growth_forecast",
    shortKey: "financial_advisor_tab_wealth_growth",
  },
  {
    id: "portfolio-optimizer",
    key: "financial_advisor_tab_portfolio_optimizer",
    shortKey: "financial_advisor_tab_portfolio",
  },
  { id: "goal-planning", key: "financial_advisor_tab_goal_planning" },
  { id: "risk-analysis", key: "financial_advisor_tab_risk_analysis" },
  { id: "spending-intelligence", key: "financial_advisor_tab_spending_intelligence" },
  {
    id: "opportunity-detection",
    key: "financial_advisor_tab_opportunity_detection",
    shortKey: "financial_advisor_tab_opportunities",
  },
  {
    id: "performance",
    key: "financial_advisor_tab_performance",
    shortKey: "financial_advisor_tab_performance",
  },
  { id: "what-if-simulator", key: "financial_advisor_tab_what_if_simulator" },
  { id: "scenario-planner", key: "financial_advisor_tab_scenario_planner" },
];

const FINANCIAL_ADVISOR_ACTIVE_TAB_KEY = "wf_financial_advisor_active_tab";
const FINANCIAL_ADVISOR_PRIMARY_TAB_IDS = [
  "overview",
  "cash-flow-forecast",
  "wealth-growth-forecast",
  "portfolio-optimizer",
];

let _cashFlowForecastLoaded = false;
let _cashFlowForecastData = null;
let _wealthGrowthForecastLoaded = false;
let _wealthGrowthForecastData = null;
let _wealthGrowthForecastThemeListenerAttached = false;
let _portfolioOptimizerLoaded = false;
let _portfolioOptimizerData = null;
let _goalPlanningLoaded = false;
let _goalPlanningData = null;
let _goalPlanningMeta = null;
let _financialAdvisorMenuEventsAbortController = null;

function _cashFlowPaneId() {
  return "fa-pane-cash-flow-forecast";
}

function _money(value) {
  return fmtpresent(value || 0);
}

function _eventTranslationKey(eventType) {
  return `cash_flow_event_${eventType || "none"}`;
}

function _wealthComponentTitle(key) {
  return (
    {
      none: "wealth_growth_component_none",
      liquid_cash: "wealth_growth_component_liquid_cash",
      fixed_assets: "wealth_growth_component_fixed_assets",
      gold: "wealth_growth_component_gold",
      certificates: "wealth_growth_component_certificates",
    }[key] || key
  );
}

function _scenarioTitle(key) {
  return (
    {
      conservative: "wealth_growth_scenario_conservative",
      expected: "wealth_growth_scenario_expected",
      optimistic: "wealth_growth_scenario_optimistic",
    }[key] || key
  );
}

function _goalPriorityRank(priority) {
  if (priority === "High") return 0;
  if (priority === "Medium") return 1;
  return 2;
}

function _goalStatusClass(status) {
  if (status === "achieved") return "goal-status-achieved";
  if (status === "on_track") return "goal-status-on-track";
  if (status === "watch") return "goal-status-watch";
  if (status === "critical") return "goal-status-critical";
  return "goal-status-risk";
}

function _goalSeverityClass(severity) {
  if (severity === "high") return "portfolio-badge-high";
  if (severity === "medium") return "portfolio-badge-medium";
  if (severity === "info") return "portfolio-badge-info";
  return "portfolio-badge-low";
}

function _goalTypeIcon(goalType) {
  const normalized = String(goalType || "").toLowerCase();
  if (normalized.includes("property") || normalized.includes("home")) return "bi-house-door";
  if (normalized.includes("retire")) return "bi-piggy-bank";
  if (normalized.includes("educ")) return "bi-mortarboard";
  if (normalized.includes("travel")) return "bi-airplane";
  if (normalized.includes("emergency") || normalized.includes("safety")) return "bi-shield-check";
  if (normalized.includes("business")) return "bi-briefcase";
  if (normalized.includes("vehicle") || normalized.includes("car")) return "bi-car-front";
  return "bi-bullseye";
}

function _escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function _destroyChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !window.Chart) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
}

function _themeColor(variableName, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
  return value || fallback;
}

function _pageDirection() {
  const htmlDir = (document.documentElement.getAttribute("dir") || "ltr").toLowerCase();
  return htmlDir === "rtl" ? "rtl" : "ltr";
}

function _portfolioSeverityClass(severity) {
  if (severity === "high") return "portfolio-badge-high";
  if (severity === "medium") return "portfolio-badge-medium";
  if (severity === "info") return "portfolio-badge-info";
  return "portfolio-badge-low";
}

function _portfolioStatusClass(status) {
  if (status === "good") return "portfolio-status-good";
  if (status === "warning") return "portfolio-status-warning";
  return "portfolio-status-danger";
}
