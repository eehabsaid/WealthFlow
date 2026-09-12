"use strict";
// tab_panes.js — pure per-tab pane HTML generator for the Financial
// Advisor page. Extracted from the renderTabPane closure inside the
// former render function in index.js. Structural split only - identical
// output, now taking activeTabId as an explicit parameter instead of
// capturing it via closure. See index.js header comment for the sibling
// list.
function _renderFATabPane(tab, activeTabId) {
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

    if (tab.id === "performance") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0"></div>
      `;
    }

    if (tab.id === "what-if-simulator") {
      return `
        <div class="tab-pane fade ${isActive}" id="${paneId}" role="tabpanel" aria-labelledby="fa-tab-${tab.id}" tabindex="0"></div>
      `;
    }

    if (tab.id === "scenario-planner") {
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
}
