"use strict";
// render.js — Financial Advisor page render: tab bar, tab-pane assembly
// (via tab_panes.js's _renderFATabPane), and tab-switch/initial-load
// wiring. Split out of the former financial_advisor/index.js monolith;
// index.js is now the thin window.* export aggregator. See its header
// comment for the sibling list.

// Financial advisor entry-point and router
// This file is part of the financial_advisor module. Do not edit directly.

function renderFinancialAdvisor() {
  const main = document.getElementById("main-content");
  if (!main) return;

  const savedTab = sessionStorage.getItem(FINANCIAL_ADVISOR_ACTIVE_TAB_KEY) || "overview";
  const hasSavedTab = FINANCIAL_ADVISOR_TABS.some((tab) => tab.id === savedTab);
  const activeTabId = hasSavedTab ? savedTab : "overview";

  const renderTabButton = (tab) => `
    <button
      class="wf-tab ${tab.id === activeTabId ? "active" : ""}"
      id="fa-tab-${tab.id}"
      data-bs-toggle="pill"
      data-bs-target="#fa-pane-${tab.id}"
      type="button"
      role="tab"
      aria-controls="fa-pane-${tab.id}"
      aria-selected="${tab.id === activeTabId ? "true" : "false"}"
      data-i18n="${tab.shortKey || tab.key}"
    ></button>
  `;

  const tabsNav = FINANCIAL_ADVISOR_TABS.map((tab) => renderTabButton(tab)).join("");

  const tabsContent = FINANCIAL_ADVISOR_TABS.map((tab) => _renderFATabPane(tab, activeTabId)).join(
    ""
  );

  const activeTabObj =
    FINANCIAL_ADVISOR_TABS.find((tab) => tab.id === activeTabId) || FINANCIAL_ADVISOR_TABS[0];
  const activeKey = activeTabObj.shortKey || activeTabObj.key;

  main.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">
          <i class="bi bi-brilliance" style="color:var(--text-primary);"></i>
          <span data-i18n="${activeKey}"></span>
        </div>
      </div>
    </div>

    <div class="card border-0" style="background:var(--bg-primary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:16px;">
        <div class="wf-tabs-shell">
          <div class="wf-tabs-row" id="financialAdvisorTabs" role="tablist">
            ${tabsNav}
          </div>
        </div>
        <div class="tab-content" id="financialAdvisorTabsContent">
          ${tabsContent}
        </div>
      </div>
    </div>
  `;

  applyTranslations();

  if (typeof window.initTabsWithMoreMenu === "function") {
    window.initTabsWithMoreMenu({
      containerId: "financialAdvisorTabs",
      visibleCount: 4,
      moreLabel: typeof t === "function" ? t("financial_advisor_tab_more", "More") : "More",
    });
  }

  const tabsContainer = document.getElementById("financialAdvisorTabs");
  if (tabsContainer) {
    tabsContainer.querySelectorAll('[data-bs-toggle="pill"]').forEach((tabButton) => {
      tabButton.addEventListener("shown.bs.tab", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const targetSelector = target.getAttribute("data-bs-target") || "";
        const tabId = target.id.replace("fa-tab-", "");
        if (tabId) {
          sessionStorage.setItem(FINANCIAL_ADVISOR_ACTIVE_TAB_KEY, tabId);
          const activeTabObj =
            FINANCIAL_ADVISOR_TABS.find((t) => t.id === tabId) || FINANCIAL_ADVISOR_TABS[0];
          const activeKey = activeTabObj.shortKey || activeTabObj.key;
          const titleEl = document.querySelector(".page-header .page-title span");
          if (titleEl) {
            titleEl.setAttribute("data-i18n", activeKey);
            titleEl.textContent = t(activeKey);
          }
        }
        if (targetSelector === "#fa-pane-overview") {
          loadOverview();
        } else if (targetSelector === `#${_cashFlowPaneId()}`) {
          loadCashFlowForecast();
        } else if (targetSelector === "#fa-pane-wealth-growth-forecast") {
          loadWealthGrowthForecast();
        } else if (targetSelector === "#fa-pane-portfolio-optimizer") {
          loadPortfolioOptimizer();
        } else if (targetSelector === "#fa-pane-goal-planning") {
          loadGoalPlanning();
        } else if (targetSelector === "#fa-pane-risk-analysis") {
          if (typeof loadRiskAnalysis === "function") loadRiskAnalysis();
        } else if (targetSelector === "#fa-pane-spending-intelligence") {
          if (typeof loadSpendingIntelligence === "function") loadSpendingIntelligence();
        } else if (targetSelector === "#fa-pane-opportunity-detection") {
          if (typeof loadOpportunityDetection === "function") loadOpportunityDetection();
        } else if (targetSelector === "#fa-pane-performance") {
          if (typeof loadPerformance === "function") loadPerformance();
        } else if (targetSelector === "#fa-pane-what-if-simulator") {
          if (typeof loadWhatIfSimulator === "function") loadWhatIfSimulator();
        } else if (targetSelector === "#fa-pane-scenario-planner") {
          if (typeof loadScenarioPlanner === "function") loadScenarioPlanner();
        }
      });
    });
  }

  if (activeTabId === "overview") {
    loadOverview();
  } else if (activeTabId === "cash-flow-forecast") {
    loadCashFlowForecast();
  } else if (activeTabId === "wealth-growth-forecast") {
    loadWealthGrowthForecast();
  } else if (activeTabId === "portfolio-optimizer") {
    loadPortfolioOptimizer();
  } else if (activeTabId === "goal-planning") {
    loadGoalPlanning();
  } else if (activeTabId === "risk-analysis") {
    if (typeof loadRiskAnalysis === "function") loadRiskAnalysis();
  } else if (activeTabId === "spending-intelligence") {
    if (typeof loadSpendingIntelligence === "function") loadSpendingIntelligence();
  } else if (activeTabId === "opportunity-detection") {
    if (typeof loadOpportunityDetection === "function") loadOpportunityDetection();
  } else if (activeTabId === "performance") {
    if (typeof loadPerformance === "function") loadPerformance();
  } else if (activeTabId === "what-if-simulator") {
    if (typeof loadWhatIfSimulator === "function") loadWhatIfSimulator();
  }
}
