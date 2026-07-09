"use strict";
// Fixed assets tab rendering and switching
// This file is part of the fixed_assets module. Do not edit directly.

function renderFixedAssets(activeTab = "assets") {
  fixedAssetsState.activeTab = activeTab;
  const target = document.getElementById("main-content");
  if (!target) return;

  target.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3 pb-2" style="border-bottom: 1px solid var(--border-color); gap: 1rem;">
            <h3 class="m-0 font-weight-bold fixed-assets-heading" data-i18n="fixed_assets">Fixed Assets</h3>
            <div id="fixedAssetsHeaderAction"></div>
        </div>
        <div class="settings-tabs-container" style="border-bottom:1px solid var(--border-color);margin-bottom:20px;display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap;">
            <button class="settings-tab ${fixedAssetsState.activeTab === "assets" ? "active" : ""}" onclick="switchFixedAssetsTab('assets')">
                <span class="fixed-assets-tab-title" data-i18n="fixed_assets_tab_assets">Assets</span>
            </button>
            <button class="settings-tab ${fixedAssetsState.activeTab === "dashboard" ? "active" : ""}" onclick="switchFixedAssetsTab('dashboard')">
                <span class="fixed-assets-tab-title" data-i18n="dashboard">Dashboard</span>
            </button>
            <button class="settings-tab ${fixedAssetsState.activeTab === "analytics" ? "active" : ""}" onclick="switchFixedAssetsTab('analytics')">
                <span class="fixed-assets-tab-title" data-i18n="fixed_assets_tab_analytics">Analytics</span>
            </button>
            <button class="settings-tab ${fixedAssetsState.activeTab === "reports" ? "active" : ""}" onclick="switchFixedAssetsTab('reports')">
                <span class="fixed-assets-tab-title" data-i18n="nav_reports">Reports</span>
            </button>
        </div>
        <div id="fixedAssetsContainer"></div>
    `;

  renderFixedAssetsHeaderAction();
  renderActiveFixedAssetsTab();
  applyTranslations();

  setTimeout(() => {
    fetchAndRenderFixedAssets();
  }, 0);
}

function switchFixedAssetsTab(tab) {
  fixedAssetsState.activeTab = tab;
  renderFixedAssetsHeaderAction();
  updateFixedAssetsTabButtons();
  renderActiveFixedAssetsTab();
  applyTranslations();
}

function updateFixedAssetsTabButtons() {
  document.querySelectorAll(".settings-tabs-container .settings-tab").forEach((button) => {
    button.classList.toggle(
      "active",
      button.getAttribute("onclick") === `switchFixedAssetsTab('${fixedAssetsState.activeTab}')`,
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

