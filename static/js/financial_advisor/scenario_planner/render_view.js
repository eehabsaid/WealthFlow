"use strict";
window.SP = window.SP || {};

  window.SP.renderScenarioPlannerView = function(pane) {
    if (!window.SP.state.scenarioPlannerData) return;

    pane.innerHTML = `
      <div class="container-fluid p-0">
        <!-- TOP: Action Bar & Subtitle (Requirement 8: Second title removed) -->
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-3">
          <div>
            <p class="small m-0" style="color:var(--text-secondary);" data-i18n="scenario_planner_subtitle">Simulate life events and compare trajectories against your real baseline.</p>
          </div>
          <div class="d-flex gap-2">
            <button id="sp-btn-new-scenario" class="btn btn-primary d-inline-flex align-items-center gap-2 btn-sm">
              <i class="bi bi-plus-circle-fill"></i>
              <span data-i18n="scenario_planner_btn_new_scenario">New Scenario</span>
            </button>
          </div>
        </div>

        <!-- TIMELINE STRIP (Requirement 1: Clean empty state or chronological events) -->
        <div class="card border-0 mb-4 p-3" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
          <div class="fw-bold mb-2 d-flex align-items-center justify-content-between" style="color:var(--text-primary); font-size:13px;">
            <div class="d-flex align-items-center gap-2">
              <i class="bi bi-clock-history text-primary"></i>
              <span data-i18n="scenario_planner_timeline_title">Life Event Timeline</span>
            </div>
          </div>
          ${window.SP.buildTimelineHtml()}
        </div>

        <!-- MAIN 2-COLUMN GRID: RAIL + WORKSPACE -->
        <div class="row g-4">
          <!-- LEFT RAIL: SCENARIO SELECTION & MANAGEMENT (Requirement 6) -->
          <div class="col-12 col-lg-3">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between mb-3">
                <span class="fw-bold small" style="color:var(--text-primary);" data-i18n="scenario_planner_rail_title">Scenarios</span>
                <button id="sp-btn-rail-new" class="btn btn-sm btn-outline-primary py-0 px-2" title="Create New Scenario">
                  <i class="bi bi-plus-lg"></i>
                </button>
              </div>

              <!-- Pinned Baseline Card (Requirement 6) -->
              <div class="p-2 mb-3 rounded d-flex align-items-center justify-content-between" style="background:var(--bg-tertiary); border:1px solid var(--accent-primary); font-size:12px; color:var(--text-secondary);">
                <div class="d-flex align-items-center gap-2">
                  <i class="bi bi-pin-angle-fill text-primary"></i>
                  <span class="fw-bold text-light" data-i18n="scenario_planner_baseline_label">Baseline</span>
                </div>
                <span class="badge bg-primary bg-opacity-25 text-primary extra-small">Pinned</span>
              </div>

              <!-- Scenarios List -->
              <div id="sp-scenario-rail-list" class="d-flex flex-column gap-2">
                ${window.SP.buildScenarioRailHtml()}
              </div>
            </div>
          </div>

          <!-- RIGHT WORKSPACE: SUB-TABS & CONTENT -->
          <div class="col-12 col-lg-9 d-flex flex-column gap-3">
            <!-- SUB-TABS NAV -->
            <div class="d-flex gap-2 p-1 rounded" style="background:var(--bg-tertiary); width:fit-content;">
              <button class="btn btn-sm ${window.SP.state.activeSubTab === "builder" ? "btn-primary" : "btn-link text-secondary text-decoration-none"}" id="sp-tab-builder" data-i18n="scenario_planner_subtab_builder">Builder</button>
              <button class="btn btn-sm ${window.SP.state.activeSubTab === "dashboard" ? "btn-primary" : "btn-link text-secondary text-decoration-none"}" id="sp-tab-dashboard" data-i18n="scenario_planner_subtab_dashboard">Impact Dashboard</button>
              <button class="btn btn-sm ${window.SP.state.activeSubTab === "compare" ? "btn-primary" : "btn-link text-secondary text-decoration-none"}" id="sp-tab-compare" data-i18n="scenario_planner_subtab_compare">Compare</button>
              <button class="btn btn-sm ${window.SP.state.activeSubTab === "insights" ? "btn-primary" : "btn-link text-secondary text-decoration-none"}" id="sp-tab-insights" data-i18n="scenario_planner_subtab_insights">Insights</button>
            </div>

            <!-- SUB-TAB CONTENT PANES -->
            <div id="sp-subtab-content">
              ${window.SP.buildSubTabContentHtml()}
            </div>
          </div>
        </div>
      </div>
    `;

    if (typeof applyTranslations === "function") applyTranslations();
    window.SP.attachEventListeners(pane);

    if (window.SP.state.activeSubTab === "dashboard" && typeof _renderScenarioPlannerChart === "function") {
      _renderScenarioPlannerChart(window.SP.state.scenarioPlannerData);
    }
  }

