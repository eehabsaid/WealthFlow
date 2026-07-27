"use strict";
// Financial advisor entry-point and router
// This file is part of the financial_advisor module. Do not edit directly.

function renderFinancialAdvisor() {
  const main = document.getElementById("main-content");
  if (!main) return;

  const savedTab = sessionStorage.getItem(FINANCIAL_ADVISOR_ACTIVE_TAB_KEY) || "overview";
  const hasSavedTab = FINANCIAL_ADVISOR_TABS.some((tab) => tab.id === savedTab);
  const activeTabId = hasSavedTab ? savedTab : "overview";
  const primaryTabs = FINANCIAL_ADVISOR_TABS.filter((tab) => FINANCIAL_ADVISOR_PRIMARY_TAB_IDS.includes(tab.id));
  const overflowTabs = FINANCIAL_ADVISOR_TABS.filter((tab) => !FINANCIAL_ADVISOR_PRIMARY_TAB_IDS.includes(tab.id));
  const overflowHasActive = overflowTabs.some((tab) => tab.id === activeTabId);

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

  const renderTabPane = (tab) => {
    const paneId = `fa-pane-${tab.id}`;
    const isActive = tab.id === activeTabId ? "show active" : "";

    if (tab.id === "overview") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0">
          <div id="fa-overview-content"></div>
        </div>
      `;
    }

    if (tab.id === "cash-flow-forecast") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0">
          <div id="fa-cash-flow-content"></div>
        </div>
      `;
    }

    if (tab.id === "wealth-growth-forecast") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0">
          <div id="fa-wealth-growth-content"></div>
        </div>
      `;
    }

    if (tab.id === "portfolio-optimizer") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0"></div>
      `;
    }

    if (tab.id === "goal-planning") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0"></div>
      `;
    }

    if (tab.id === "risk-analysis") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0"></div>
      `;
    }

    if (tab.id === "spending-intelligence") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0"></div>
      `;
    }

    if (tab.id === "opportunity-detection") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0"></div>
      `;
    }

    if (tab.id === "performance" || tab.id === "market-intelligence") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0"></div>
      `;
    }

    return `
      <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0">
        <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
          <div class="card-body" style="padding:24px;">
            <h5 style="color:var(--text-primary); margin-bottom:10px;" data-i18n="financial_advisor_feature_coming_soon"></h5>
            <p style="color:var(--text-secondary); margin:0;" data-i18n="financial_advisor_next_phase_description"></p>
          </div>
        </div>
      </div>
    `;
  };

  const tabsContent = FINANCIAL_ADVISOR_TABS.map((tab) => renderTabPane(tab)).join("");

  const activeTabObj = FINANCIAL_ADVISOR_TABS.find(tab => tab.id === activeTabId) || FINANCIAL_ADVISOR_TABS[0];
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

  if (typeof window.initTabsWithMoreMenu === 'function') {
    window.initTabsWithMoreMenu({
      containerId: 'financialAdvisorTabs',
      visibleCount: 4,
      moreLabel: typeof t === 'function' ? t('financial_advisor_tab_more', 'More') : 'More',
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
          const activeTabObj = FINANCIAL_ADVISOR_TABS.find(t => t.id === tabId) || FINANCIAL_ADVISOR_TABS[0];
          const activeKey = activeTabObj.shortKey || activeTabObj.key;
          const titleEl = document.querySelector('.page-header .page-title span');
          if (titleEl) {
            titleEl.setAttribute('data-i18n', activeKey);
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
        } else if (targetSelector === "#fa-pane-performance" || targetSelector === "#fa-pane-market-intelligence") {
          if (typeof loadPerformance === "function") loadPerformance();
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
  } else if (activeTabId === "performance" || activeTabId === "market-intelligence") {
    if (typeof loadPerformance === "function") loadPerformance();
  }
}

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
window.loadRiskAnalysis = (typeof loadRiskAnalysis !== 'undefined') ? loadRiskAnalysis : () => {};
window.loadSpendingIntelligence = (typeof loadSpendingIntelligence !== 'undefined') ? loadSpendingIntelligence : () => {};
window.loadOpportunityDetection = (typeof loadOpportunityDetection !== 'undefined') ? loadOpportunityDetection : () => {};
window.loadPerformance = (typeof loadPerformance !== 'undefined') ? loadPerformance : () => {};

