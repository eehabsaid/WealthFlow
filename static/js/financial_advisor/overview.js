"use strict";

let _overviewLoaded = false;
let _overviewData = null;

async function loadOverview(force = false) {
  if (_overviewData && !force) {
    _renderOverview(_overviewData);
    _overviewLoaded = true;
    return;
  }

  _renderOverviewLoading();
  try {
    const response = await fetch("/api/financial-advisor/overview/");
    if (!response.ok) {
      throw new Error("overview_fetch_failed");
    }
    const payload = await response.json();
    _overviewData = payload;
    _renderOverview(payload);
    _overviewLoaded = true;
  } catch (error) {
    console.error("Overview error:", error);
    _renderOverviewError();
  }
}

function switchFinancialAdvisorTab(tabId) {
  const tabButton = document.getElementById(`fa-tab-${tabId}`);
  if (tabButton) {
    tabButton.click();
    if (typeof bootstrap !== "undefined" && bootstrap.Tab) {
      const tabTrigger = new bootstrap.Tab(tabButton);
      tabTrigger.show();
    }
  }
}

// Bind to window context
window.loadOverview = loadOverview;
window.switchFinancialAdvisorTab = switchFinancialAdvisorTab;
