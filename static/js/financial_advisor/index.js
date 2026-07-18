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

  const renderTabButton = (tab, cssClass) => `
    <button
      class="${cssClass} ${tab.id === activeTabId ? "active" : ""}"
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

  const primaryTabsNav = primaryTabs.map((tab) => renderTabButton(tab, "financial-advisor-tab")).join("");
  const overflowTabsNav = overflowTabs.map((tab) => renderTabButton(tab, "financial-advisor-dropdown-item")).join("");

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
        <div class="financial-advisor-tabs-shell">
          <div class="financial-advisor-tabs-row" id="financialAdvisorTabs" role="tablist">
            <div class="financial-advisor-main-tabs">
              ${primaryTabsNav}
            </div>
            <div class="financial-advisor-more-wrap ${overflowHasActive ? "active" : ""}" id="financialAdvisorMoreWrap">
              <button
                class="financial-advisor-tab financial-advisor-more-toggle ${overflowHasActive ? "active" : ""}"
                id="financialAdvisorMoreBtn"
                type="button"
                aria-haspopup="true"
                aria-expanded="false"
              >
                <span data-i18n="financial_advisor_tab_more"></span>
                <i class="bi bi-chevron-down financial-advisor-more-icon"></i>
              </button>
              <div class="financial-advisor-more-menu" id="financialAdvisorMoreMenu" role="menu">
                ${overflowTabsNav}
              </div>
            </div>
          </div>
        </div>
        <div class="tab-content" id="financialAdvisorTabsContent">
          ${tabsContent}
        </div>
      </div>
    </div>
  `;

  applyTranslations();

  const tabsContainer = document.getElementById("financialAdvisorTabs");
  const moreWrap = document.getElementById("financialAdvisorMoreWrap");
  const moreBtn = document.getElementById("financialAdvisorMoreBtn");
  const moreMenu = document.getElementById("financialAdvisorMoreMenu");

  const closeMoreMenu = () => {
    if (!moreWrap || !moreBtn) return;
    moreWrap.classList.remove("open");
    moreBtn.setAttribute("aria-expanded", "false");
  };

  const positionMoreMenu = () => {
    if (!moreMenu) return;
    moreMenu.classList.remove("align-right", "align-left");
    const rect = moreMenu.getBoundingClientRect();
    const viewportPadding = 12;

    if (rect.right > (window.innerWidth - viewportPadding)) {
      moreMenu.classList.add("align-right");
      return;
    }

    if (rect.left < viewportPadding) {
      moreMenu.classList.add("align-left");
    }
  };

  const openMoreMenu = () => {
    if (!moreWrap || !moreBtn) return;
    moreWrap.classList.add("open");
    moreBtn.setAttribute("aria-expanded", "true");
    window.requestAnimationFrame(positionMoreMenu);
  };

  const syncMoreActiveState = () => {
    if (!moreWrap || !moreBtn) return;
    const hasOverflowActive = overflowTabs.some((tab) => {
      const tabButton = document.getElementById(`fa-tab-${tab.id}`);
      return tabButton?.classList.contains("active");
    });
    moreWrap.classList.toggle("active", hasOverflowActive);
    moreBtn.classList.toggle("active", hasOverflowActive);
  };

  if (_financialAdvisorMenuEventsAbortController) {
    _financialAdvisorMenuEventsAbortController.abort();
  }
  _financialAdvisorMenuEventsAbortController = new AbortController();
  const menuEventsSignal = _financialAdvisorMenuEventsAbortController.signal;

  if (moreBtn && moreWrap && moreMenu) {
    moreBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      if (moreWrap.classList.contains("open")) {
        closeMoreMenu();
      } else {
        openMoreMenu();
      }
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!moreWrap.contains(target)) {
        closeMoreMenu();
      }
    }, { signal: menuEventsSignal });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMoreMenu();
      }
    }, { signal: menuEventsSignal });

    window.addEventListener("resize", () => {
      if (moreWrap.classList.contains("open")) {
        positionMoreMenu();
      }
    }, { signal: menuEventsSignal });

    moreMenu.querySelectorAll('[data-bs-toggle="pill"]').forEach((menuTab) => {
      menuTab.addEventListener("click", () => {
        closeMoreMenu();
      });
    });
  }

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
        }
        closeMoreMenu();
        syncMoreActiveState();
      });
    });
  }

  syncMoreActiveState();

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
