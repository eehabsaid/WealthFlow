"use strict";
// Fixed assets tab rendering and switching
// This file is part of the fixed_assets module. Do not edit directly.

function renderFixedAssets(activeTab = "assets") {
  fixedAssetsState.activeTab = activeTab;
  const target = document.getElementById("main-content");
  if (!target) return;

  let activeKey = "fixed_assets_tab_assets";
  let activeLabel = "Assets";
  if (activeTab === "dashboard") {
    activeKey = "dashboard";
    activeLabel = "Dashboard";
  } else if (activeTab === "analytics") {
    activeKey = "fixed_assets_tab_analytics";
    activeLabel = "Analytics";
  } else if (activeTab === "reports") {
    activeKey = "nav_reports";
    activeLabel = "Reports";
  }

  target.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3 pb-2" style="border-bottom: 1px solid var(--border-color); gap: 1rem;">
            <h3 class="m-0 font-weight-bold fixed-assets-heading" data-i18n="${activeKey}">${t(activeKey, activeLabel)}</h3>
            <div id="fixedAssetsHeaderAction"></div>
        </div>
        <div class="wf-tabs-shell">
            <div class="wf-tabs-row" id="fixedAssetsTabsBar" role="tablist">
                <button class="wf-tab ${fixedAssetsState.activeTab === "assets" ? "active" : ""}" onclick="switchFixedAssetsTab('assets')" data-i18n="fixed_assets_tab_assets">
                    Assets
                </button>
                <button class="wf-tab ${fixedAssetsState.activeTab === "dashboard" ? "active" : ""}" onclick="switchFixedAssetsTab('dashboard')" data-i18n="dashboard">
                    Dashboard
                </button>
                <button class="wf-tab ${fixedAssetsState.activeTab === "analytics" ? "active" : ""}" onclick="switchFixedAssetsTab('analytics')" data-i18n="fixed_assets_tab_analytics">
                    Analytics
                </button>
                <button class="wf-tab ${fixedAssetsState.activeTab === "reports" ? "active" : ""}" onclick="switchFixedAssetsTab('reports')" data-i18n="nav_reports">
                    Reports
                </button>
            </div>
        </div>
        <div id="fixedAssetsContainer"></div>
    `;

  renderFixedAssetsHeaderAction();
  renderActiveFixedAssetsTab();
  applyTranslations();

  if (typeof window.initTabsWithMoreMenu === "function") {
    window.initTabsWithMoreMenu({
      containerId: "fixedAssetsTabsBar",
      visibleCount: 4,
      moreLabel: typeof t === "function" ? t("financial_advisor_tab_more", "More") : "More",
    });
  }

  setTimeout(() => {
    fetchAndRenderFixedAssets();
  }, 0);
}

function switchFixedAssetsTab(tab) {
  fixedAssetsState.activeTab = tab;

  const heading = document.querySelector(".fixed-assets-heading");
  if (heading) {
    if (tab === "assets") {
      heading.setAttribute("data-i18n", "fixed_assets_tab_assets");
      heading.textContent = t("fixed_assets_tab_assets", "Assets");
    } else if (tab === "dashboard") {
      heading.setAttribute("data-i18n", "dashboard");
      heading.textContent = t("dashboard", "Dashboard");
    } else if (tab === "analytics") {
      heading.setAttribute("data-i18n", "fixed_assets_tab_analytics");
      heading.textContent = t("fixed_assets_tab_analytics", "Analytics");
    } else if (tab === "reports") {
      heading.setAttribute("data-i18n", "nav_reports");
      heading.textContent = t("nav_reports", "Reports");
    }
  }

  renderFixedAssetsHeaderAction();
  updateFixedAssetsTabButtons();
  renderActiveFixedAssetsTab();
  applyTranslations();
}

function updateFixedAssetsTabButtons() {
  document.querySelectorAll("#fixedAssetsTabsBar button").forEach((button) => {
    button.classList.toggle(
      "active",
      button.getAttribute("onclick") === `switchFixedAssetsTab('${fixedAssetsState.activeTab}')`
    );
  });
}

function renderFixedAssetsHeaderAction() {
  const actionContainer = document.getElementById("fixedAssetsHeaderAction");
  if (!actionContainer) return;

  if (fixedAssetsState.activeTab === "assets") {
    actionContainer.innerHTML = `
      <button class="btn-primary-custom" onclick="showFixedAssetModal()">
          <i class="bi bi-plus-lg"></i> <span data-i18n="add_new_asset">Add Asset</span>
      </button>
    `;
  } else {
    actionContainer.innerHTML = "";
  }
}

function renderActiveFixedAssetsTab() {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  if (fixedAssetsState.isLoading) {
    container.innerHTML = `
      <div style="display:flex;justify-content:center;padding:60px;">
        <div class="spinner-border" style="color:var(--accent-primary)"></div>
      </div>
    `;
    return;
  }

  if (fixedAssetsState.activeTab === "assets") {
    renderFixedAssetsList(fixedAssetsState.assets);
    return;
  }

  if (fixedAssetsState.activeTab === "dashboard") {
    renderFixedAssetsDashboard(fixedAssetsState.assets);
    return;
  }

  if (fixedAssetsState.activeTab === "analytics") {
    renderFixedAssetsAnalytics(fixedAssetsState.assets);
    return;
  }

  renderFixedAssetsReports(fixedAssetsState.assets);
}

// ════════════════════════════════════════════════════════════════════════════
// LIST RENDERING (CARD VIEW)
// ════════════════════════════════════════════════════════════════════════════
