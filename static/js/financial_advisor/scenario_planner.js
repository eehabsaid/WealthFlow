"use strict";
// Financial Scenario Planner tab logic
// This file is part of the financial_advisor module. Do not edit directly.

(function () {
  let _scenarioPlannerData = null;
  let _cachedScenarios = [];
  let _cachedEventSchema = null;
  let _activeScenarioId = null;
  let _selectedScenarioIds = [];
  let _activeSubTab = "dashboard"; // "builder" | "dashboard" | "compare" | "insights"
  let _selectedEventType = "house";
  let _debounceTimer = null;
  let _themeListenerAttached = false;

  function _money(value) {
    const num = Number(value) || 0;
    if (typeof fmtpresent === "function") {
      return fmtpresent(num);
    }
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function _fmtDelta(val, isPct = false, digits = 1) {
    if (val === null || val === undefined) return "-";
    const num = Number(val) || 0;
    const sign = num > 0 ? "+" : "";
    if (isPct) return `${sign}${num.toFixed(digits)}%`;
    if (typeof fmtpresent === "function") {
      return `${sign}${fmtpresent(num)}`;
    }
    return `${sign}${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function _attachThemeListener() {
    if (_themeListenerAttached) return;
    window.addEventListener("themeChanged", () => {
      if (_scenarioPlannerData && typeof _renderScenarioPlannerChart === "function") {
        _renderScenarioPlannerChart(_scenarioPlannerData);
      }
    });
    _themeListenerAttached = true;
  }

  // ── Standalone Cached Schema Endpoint ──────────────────────────────────────

  async function _loadEventSchema() {
    if (_cachedEventSchema) return _cachedEventSchema;
    try {
      const resp = await fetch("/api/scenarios/event-definitions/");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _cachedEventSchema = data.event_schema || [];
      return _cachedEventSchema;
    } catch (err) {
      console.error("Failed to load event definitions schema:", err);
      _cachedEventSchema = [];
      return [];
    }
  }

  // ── Data Loading & Comparison API ──────────────────────────────────────────

  async function loadScenarioPlanner(forceFetch = false) {
    const pane = document.getElementById("fa-pane-scenario-planner");
    if (!pane) return;

    if (!forceFetch && _scenarioPlannerData && _cachedScenarios.length > 0) {
      _renderScenarioPlannerView(pane);
      return;
    }

    pane.innerHTML = `
      <div class="d-flex justify-content-center align-items-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden" data-i18n="scenario_planner_loading">Loading Scenario Planner...</span>
        </div>
      </div>
    `;
    if (typeof applyTranslations === "function") applyTranslations();

    try {
      await _loadEventSchema();
      await _fetchScenarioList();

      if (!_activeScenarioId && _cachedScenarios.length > 0) {
        _activeScenarioId = _cachedScenarios[0].id;
        _selectedScenarioIds = [_activeScenarioId];
      }

      await _recalculateBackend();
      _attachThemeListener();
    } catch (err) {
      console.error("Failed to load Scenario Planner:", err);
      pane.innerHTML = `
        <div class="alert alert-danger my-3" role="alert" data-i18n="scenario_planner_error_load">
          Failed to load Scenario Planner. Please try again.
        </div>
      `;
      if (typeof applyTranslations === "function") applyTranslations();
    }
  }

  async function _fetchScenarioList() {
    try {
      const resp = await fetch("/api/scenarios/");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _cachedScenarios = data.scenarios || [];
    } catch (err) {
      console.error("Failed to fetch scenarios list:", err);
      _cachedScenarios = [];
    }
  }

  async function _recalculateBackend() {
    const pane = document.getElementById("fa-pane-scenario-planner");
    if (!pane) return;

    const query = new URLSearchParams();
    if (_selectedScenarioIds && _selectedScenarioIds.length > 0) {
      query.set("scenario_ids", _selectedScenarioIds.join(","));
    }

    try {
      const resp = await fetch(`/api/financial-advisor/scenario-planner/compare/?${query.toString()}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const payload = await resp.json();
      _scenarioPlannerData = payload;

      _renderScenarioPlannerView(pane);
    } catch (err) {
      console.error("Scenario Planner recalculation error:", err);
    }
  }

  function _debouncedRecalculate() {
    if (_debounceTimer) clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(() => {
      _recalculateBackend();
    }, 350);
  }

  // ── Render Views ──────────────────────────────────────────────────────────

  function _renderScenarioPlannerView(pane) {
    if (!_scenarioPlannerData) return;

    pane.innerHTML = `
      <div class="container-fluid p-0">
        <!-- TOP: Header & Action Bar -->
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
          <div>
            <h4 class="fw-bold m-0" style="color:var(--text-primary);" data-i18n="scenario_planner_title">Financial Scenario Planner</h4>
            <p class="small m-0 mt-1" style="color:var(--text-secondary);" data-i18n="scenario_planner_subtitle">Simulate life events and compare trajectories against your real baseline.</p>
          </div>
          <div class="d-flex gap-2">
            <button id="sp-btn-new-scenario" class="btn btn-primary d-inline-flex align-items-center gap-2">
              <i class="bi bi-plus-lg"></i>
              <span data-i18n="scenario_planner_btn_new_scenario">New Scenario</span>
            </button>
          </div>
        </div>

        <!-- TIMELINE STRIP -->
        <div class="card border-0 mb-4 p-3" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
          <div class="fw-bold mb-3 d-flex align-items-center gap-2" style="color:var(--text-primary); font-size:13px;">
            <i class="bi bi-clock-history"></i>
            <span data-i18n="scenario_planner_timeline_title">Life Event Timeline</span>
          </div>
          ${_buildTimelineHtml()}
        </div>

        <!-- MAIN 2-COLUMN GRID: RAIL + WORKSPACE -->
        <div class="row g-4">
          <!-- LEFT RAIL: SCENARIO SELECTION & MANAGE -->
          <div class="col-12 col-lg-3">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between mb-3">
                <span class="fw-bold small" style="color:var(--text-primary);" data-i18n="scenario_planner_rail_title">Scenarios</span>
                <span class="badge bg-secondary">${_cachedScenarios.length}</span>
              </div>

              <!-- Pinned Baseline Card -->
              <div class="p-2 mb-3 rounded d-flex align-items-center gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color); font-size:12px; color:var(--text-secondary);">
                <i class="bi bi-pin-angle-fill text-primary"></i>
                <span data-i18n="scenario_planner_baseline_note">Baseline = Current Real Trajectory</span>
              </div>

              <!-- Scenarios List -->
              <div id="sp-scenario-rail-list" class="d-flex flex-column gap-2">
                ${_buildScenarioRailHtml()}
              </div>
            </div>
          </div>

          <!-- RIGHT WORKSPACE: SUB-TABS & CONTENT -->
          <div class="col-12 col-lg-9 d-flex flex-column gap-3">
            <!-- SUB-TABS NAV -->
            <div class="d-flex gap-2 p-1 rounded" style="background:var(--bg-tertiary); width:fit-content;">
              <button class="btn btn-sm ${_activeSubTab === "builder" ? "btn-primary" : "btn-link text-secondary text-decoration-none"}" id="sp-tab-builder" data-i18n="scenario_planner_subtab_builder">Builder</button>
              <button class="btn btn-sm ${_activeSubTab === "dashboard" ? "btn-primary" : "btn-link text-secondary text-decoration-none"}" id="sp-tab-dashboard" data-i18n="scenario_planner_subtab_dashboard">Impact Dashboard</button>
              <button class="btn btn-sm ${_activeSubTab === "compare" ? "btn-primary" : "btn-link text-secondary text-decoration-none"}" id="sp-tab-compare" data-i18n="scenario_planner_subtab_compare">Compare</button>
              <button class="btn btn-sm ${_activeSubTab === "insights" ? "btn-primary" : "btn-link text-secondary text-decoration-none"}" id="sp-tab-insights" data-i18n="scenario_planner_subtab_insights">Insights</button>
            </div>

            <!-- SUB-TAB CONTENT PANES -->
            <div id="sp-subtab-content">
              ${_buildSubTabContentHtml()}
            </div>
          </div>
        </div>
      </div>
    `;

    if (typeof applyTranslations === "function") applyTranslations();
    _attachEventListeners(pane);

    if (_activeSubTab === "dashboard" && typeof _renderScenarioPlannerChart === "function") {
      _renderScenarioPlannerChart(_scenarioPlannerData);
    }
  }

  // ── HTML Builders ──────────────────────────────────────────────────────────

  function _buildTimelineHtml() {
    const baseline = _scenarioPlannerData?.baseline || {};
    const scenarios = _scenarioPlannerData?.scenarios || [];

    const todayFormatted = typeof formatDate === "function" ? formatDate(new Date()) : "";
    const timelineNodes = [
      { label: typeof t === "function" ? t("balance_tab_overview", "Today") : "Today", dateStr: todayFormatted, type: "now", chip: typeof t === "function" ? t("scenario_planner_baseline_label", "Baseline") : "Baseline" },
    ];

    scenarios.forEach((sc, idx) => {
      (sc.events || []).forEach((ev) => {
        const evLabelKey = `scenario_planner_event_${ev.event_type}`;
        const translatedLabel = typeof t === "function" ? t(evLabelKey, ev.event_type) : ev.event_type;
        timelineNodes.push({
          label: translatedLabel,
          dateStr: typeof formatDate === "function" ? formatDate(ev.event_date) : (ev.event_date || ""),
          type: ev.event_type || "event",
          chip: sc.name || `Scenario ${sc.id}`,
        });
      });
    });

    timelineNodes.push({
      label: typeof t === "function" ? t("scenario_planner_event_retirement", "Retirement Target") : "Retirement Target",
      dateStr: "2050",
      type: "retirement",
      chip: typeof t === "function" ? t("goal_planning_target_date", "Target") : "Target",
    });

    return `
      <div class="d-flex align-items-center gap-4 overflow-x-auto py-2">
        ${timelineNodes
          .map(
            (node) => `
          <div class="d-flex flex-column align-items-center text-center flex-shrink-0" style="min-width:110px;">
            <div class="rounded-circle d-flex align-items-center justify-content-center mb-1" style="width:28px; height:28px; background:var(--bg-tertiary); border:2px solid var(--accent-primary);">
              <i class="bi bi-geo-alt-fill text-primary" style="font-size:12px;"></i>
            </div>
            <span class="fw-bold extra-small text-truncate style="color:var(--text-primary); max-width:100px;">${node.label}</span>
            <span class="extra-small style="color:var(--text-muted);">${node.dateStr}</span>
            <span class="badge bg-secondary extra-small mt-1">${node.chip}</span>
          </div>
        `
          )
          .join("")}
      </div>
    `;
  }

  function _buildScenarioRailHtml() {
    if (_cachedScenarios.length === 0) {
      return `
        <div class="p-3 text-center text-muted extra-small" data-i18n="scenario_planner_no_scenarios">
          No saved scenarios yet. Click 'New Scenario' to create one.
        </div>
      `;
    }

    return _cachedScenarios
      .map((sc) => {
        const isActive = sc.id === _activeScenarioId;
        const isChecked = _selectedScenarioIds.includes(sc.id);
        const eventCount = (sc.events || []).length;

        return `
        <div class="card p-2 border-0 ${isActive ? "border-primary" : ""}" style="background:${isActive ? "rgba(26,110,245,0.1)" : "var(--bg-tertiary)"}; border:1px solid ${isActive ? "var(--accent-primary)" : "var(--border-color)"}; border-radius:8px; cursor:pointer;" data-scenario-id="${sc.id}">
          <div class="d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center gap-2">
              <input type="checkbox" class="form-check-input sp-cmp-check" data-id="${sc.id}" ${isChecked ? "checked" : ""}>
              <div>
                <div class="fw-bold small" style="color:var(--text-primary);">${sc.name}</div>
                <div class="extra-small" style="color:var(--text-muted);">${eventCount} event(s)</div>
              </div>
            </div>
            <button class="btn btn-sm btn-link text-danger p-0 sp-btn-delete-sc" data-id="${sc.id}">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
      `;
      })
      .join("");
  }

  function _buildSubTabContentHtml() {
    if (_activeSubTab === "builder") {
      return _buildBuilderPaneHtml();
    }
    if (_activeSubTab === "dashboard") {
      return _buildDashboardPaneHtml();
    }
    if (_activeSubTab === "compare") {
      return _buildComparePaneHtml();
    }
    if (_activeSubTab === "insights") {
      return _buildInsightsPaneHtml();
    }
    return "";
  }

  // ── Data-Driven Builder Form (Schema-Driven) ──────────────────────────────

  function _buildBuilderPaneHtml() {
    const activeScenario = _cachedScenarios.find((s) => s.id === _activeScenarioId);
    if (!activeScenario) {
      return `
        <div class="alert alert-info" data-i18n="scenario_planner_select_scenario_hint">
          Select or create a scenario from the left rail to edit its events.
        </div>
      `;
    }

    const schema = _cachedEventSchema || [];
    const selectedSchema = schema.find((s) => s.event_type === _selectedEventType) || schema[0];

    return `
      <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
        <h5 class="fw-bold mb-3" style="color:var(--text-primary);">${activeScenario.name} — Event Builder</h5>

        <!-- Data-Driven Event Type Selector Grid -->
        <label class="form-label small fw-semibold" style="color:var(--text-primary);" data-i18n="scenario_planner_select_event_type">Select Event Type</label>
        <div class="row row-cols-2 row-cols-md-5 g-2 mb-4">
          ${schema
            .map(
              (item) => `
            <div class="col">
              <div class="p-2 text-center rounded border sp-event-type-card ${item.event_type === _selectedEventType ? "border-primary bg-primary bg-opacity-10" : ""}" style="cursor:pointer; background:var(--bg-tertiary);" data-event-type="${item.event_type}">
                <i class="bi ${item.icon} text-primary fs-5"></i>
                <div class="extra-small fw-bold mt-1 text-truncate" style="color:var(--text-primary);" data-i18n="${item.label_key}">${item.event_type}</div>
              </div>
            </div>
          `
            )
            .join("")}
        </div>

        <!-- Data-Driven Dynamic Event Form -->
        <div class="p-3 mb-4 rounded" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
          <h6 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="${selectedSchema?.label_key || "scenario_planner_add_event"}">Add Event</h6>
          <form id="sp-event-form">
            <div class="row g-3">
              ${(selectedSchema?.fields || [])
                .map(
                  (f) => `
                <div class="col-12 col-md-4">
                  <label class="form-label extra-small fw-semibold" style="color:var(--text-primary);" data-i18n="${f.label_key}">${f.name}</label>
                  ${
                    f.type === "select"
                      ? `
                    <select class="form-select form-select-sm" name="${f.name}">
                      ${(f.options || []).map((opt) => `<option value="${opt}">${opt}</option>`).join("")}
                    </select>
                  `
                      : `
                    <input type="${f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}" class="form-control form-control-sm" name="${f.name}" value="${f.default || ""}">
                  `
                  }
                </div>
              `
                )
                .join("")}
            </div>
            <div class="mt-3 text-end">
              <button type="submit" class="btn btn-sm btn-primary">
                <i class="bi bi-plus-lg me-1"></i> <span data-i18n="scenario_planner_btn_add_event">Add Event to Scenario</span>
              </button>
            </div>
          </form>
        </div>

        <!-- Current Events in Active Scenario -->
        <h6 class="fw-bold mb-2" style="color:var(--text-primary);" data-i18n="scenario_planner_existing_events">Configured Events</h6>
        <div class="d-flex flex-column gap-2">
          ${(activeScenario.events || []).length === 0
            ? `<div class="extra-small text-muted" data-i18n="scenario_planner_no_events">No events added to this scenario yet.</div>`
            : activeScenario.events
                .map(
                  (ev) => `
              <div class="p-2 rounded d-flex align-items-center justify-content-between" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
                <div>
                  <span class="badge bg-primary me-2">${typeof t === "function" ? t(`scenario_planner_event_${ev.event_type}`, ev.event_type) : ev.event_type}</span>
                  <span class="small fw-semibold" style="color:var(--text-primary);">${typeof formatDate === "function" ? formatDate(ev.event_date) : ev.event_date}</span>
                </div>
                <button class="btn btn-sm btn-link text-danger p-0 sp-btn-delete-event" data-event-id="${ev.id}">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            `
                )
                .join("")}
        </div>
      </div>
    `;
  }

  // ── Impact Dashboard Pane ──────────────────────────────────────────────────

  function _buildDashboardPaneHtml() {
    const base = _scenarioPlannerData?.baseline || {};
    const scList = _scenarioPlannerData?.scenarios || [];
    const activeSc = scList.find((s) => s.id === _activeScenarioId) || scList[0] || base;

    const nwVal = activeSc.net_worth_12m || 0;
    const nwBase = base.net_worth_12m || 0;
    const nwDelta = nwVal - nwBase;

    const flowVal = activeSc.monthly_cash_flow || 0;
    const debtVal = activeSc.total_debt || 0;
    const covVal = activeSc.cash_coverage_months;

    const retireObj = activeSc.retirement_readiness || {};
    const readinessPct = retireObj.readiness_pct || 0;

    return `
      <div class="d-flex flex-column gap-4">
        <!-- KPI CARDS GRID -->
        <div class="row row-cols-1 row-cols-md-5 g-3">
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_networth">Net Worth (12m)</div>
              <div class="fs-5 fw-bold mt-1" style="color:var(--text-primary);">${_money(nwVal)}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${_money(nwBase)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_cashflow">Monthly Cash Flow</div>
              <div class="fs-5 fw-bold mt-1" style="color:var(--text-primary);">${_money(flowVal)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_debt">Total Debt</div>
              <div class="fs-5 fw-bold mt-1" style="color:var(--text-primary);">${_money(debtVal)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_coverage">Cash Coverage</div>
              <div class="fs-5 fw-bold mt-1" style="color:var(--text-primary);">${covVal !== null && covVal !== undefined ? covVal + " mo" : "-"}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_readiness">Retirement Readiness</div>
              <div class="fs-5 fw-bold mt-1" style="color:var(--text-primary);">${readinessPct}%</div>
            </div>
          </div>
        </div>

        <!-- MULTI-SERIES CHART CARD -->
        <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
          <h5 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="scenario_planner_chart_title">Net Worth Trajectory Comparison</h5>
          <div style="height:320px; position:relative;">
            <canvas id="scenarioPlannerChart"></canvas>
          </div>
        </div>
      </div>
    `;
  }

  // ── Scrollable N-Scenario Comparison Table ─────────────────────────────────

  function _buildComparePaneHtml() {
    const base = _scenarioPlannerData?.baseline || {};
    const scenarios = _scenarioPlannerData?.scenarios || [];

    return `
      <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
        <h5 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="scenario_planner_compare_title">Side-by-Side N-Scenario Comparison</h5>

        <!-- Wrap table in overflow-x auto for smooth N-scenario horizontal scrolling -->
        <div style="overflow-x:auto;">
          <table class="table table-dark table-borderless align-middle m-0" style="background:transparent;">
            <thead>
              <tr class="border-bottom border-secondary">
                <th style="color:var(--text-muted); font-size:12px;" data-i18n="scenario_planner_metric_header">Metric</th>
                <th style="color:var(--text-muted); font-size:12px;">Baseline</th>
                ${scenarios.map((sc) => `<th style="color:var(--accent-primary); font-size:12px;">${sc.name}</th>`).join("")}
              </tr>
            </thead>
            <tbody>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_nw">Net Worth (12m)</td>
                <td class="fw-bold text-light">${_money(base.net_worth_12m)}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${_money(sc.net_worth_12m)}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_cashflow">Monthly Cash Flow</td>
                <td class="fw-bold text-light">${_money(base.monthly_cash_flow)}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${_money(sc.monthly_cash_flow)}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_debt">Total Debt</td>
                <td class="fw-bold text-light">${_money(base.total_debt)}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${_money(sc.total_debt)}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_coverage">Cash Coverage (months)</td>
                <td class="fw-bold text-light">${base.cash_coverage_months ?? "-"}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${sc.cash_coverage_months ?? "-"}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_risk">Risk Score</td>
                <td class="fw-bold text-light">${base.risk_score}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${sc.risk_score}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_readiness">Retirement Readiness</td>
                <td class="fw-bold text-light">${base.retirement_readiness?.readiness_pct ?? 0}%</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${sc.retirement_readiness?.readiness_pct ?? 0}%</td>`).join("")}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // ── Insights Pane ──────────────────────────────────────────────────────────

  function _buildInsightsPaneHtml() {
    const scenarios = _scenarioPlannerData?.scenarios || [];
    if (scenarios.length === 0) {
      return `
        <div class="alert alert-info" data-i18n="scenario_planner_insights_no_scenarios">
          Select or compare at least one scenario to generate financial insights.
        </div>
      `;
    }

    return `
      <div class="d-flex flex-column gap-3">
        ${scenarios
          .map((sc) => {
            const insights = sc.insights || [];
            return `
            <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <h6 class="fw-bold mb-3" style="color:var(--text-primary);">${sc.name} — Insights</h6>
              <div class="d-flex flex-column gap-2">
                ${insights
                  .map(
                    (ins) => `
                  <div class="p-3 rounded d-flex align-items-start gap-3" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
                    <i class="bi ${ins.severity === "good" ? "bi-check-circle-fill text-success" : ins.severity === "bad" ? "bi-exclamation-octagon-fill text-danger" : "bi-exclamation-triangle-fill text-warning"} fs-5"></i>
                    <div>
                      <div class="fw-bold small" style="color:var(--text-primary);" data-i18n="${ins.title_key}">${ins.title_key}</div>
                      <div class="extra-small mt-1" style="color:var(--text-secondary);" data-i18n="${ins.body_key}">${ins.body_key}</div>
                    </div>
                  </div>
                `
                  )
                  .join("")}
              </div>
            </div>
          `;
          })
          .join("")}
      </div>
    `;
  }

  // ── Event Listeners ────────────────────────────────────────────────────────

  function _attachEventListeners(pane) {
    // New scenario button
    const btnNew = pane.querySelector("#sp-btn-new-scenario");
    if (btnNew) {
      btnNew.addEventListener("click", _createNewScenarioPrompt);
    }

    // Scenario rail click (select active scenario)
    pane.querySelectorAll("[data-scenario-id]").forEach((el) => {
      el.addEventListener("click", (e) => {
        if (e.target.closest(".sp-cmp-check") || e.target.closest(".sp-btn-delete-sc")) return;
        const scId = Number(el.getAttribute("data-scenario-id"));
        if (scId) {
          _activeScenarioId = scId;
          _renderScenarioPlannerView(pane);
        }
      });
    });

    // Comparison Checkboxes
    pane.querySelectorAll(".sp-cmp-check").forEach((chk) => {
      chk.addEventListener("change", (e) => {
        const id = Number(e.target.getAttribute("data-id"));
        if (e.target.checked) {
          if (!_selectedScenarioIds.includes(id)) _selectedScenarioIds.push(id);
        } else {
          _selectedScenarioIds = _selectedScenarioIds.filter((x) => x !== id);
        }
        _debouncedRecalculate();
      });
    });

    // Delete scenario buttons
    pane.querySelectorAll(".sp-btn-delete-sc").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = Number(btn.getAttribute("data-id"));
        if (id && confirm("Delete this scenario?")) {
          await _deleteScenario(id);
        }
      });
    });

    // Sub-tab buttons
    ["builder", "dashboard", "compare", "insights"].forEach((tabKey) => {
      const btn = pane.querySelector(`#sp-tab-${tabKey}`);
      if (btn) {
        btn.addEventListener("click", () => {
          _activeSubTab = tabKey;
          _renderScenarioPlannerView(pane);
        });
      }
    });

    // Event type cards (Builder)
    pane.querySelectorAll(".sp-event-type-card").forEach((card) => {
      card.addEventListener("click", () => {
        _selectedEventType = card.getAttribute("data-event-type");
        _renderScenarioPlannerView(pane);
      });
    });

    // Add event form submit
    const eventForm = pane.querySelector("#sp-event-form");
    if (eventForm) {
      eventForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = new FormData(eventForm);
        const params = {};
        let eventDate = "";

        for (const [k, v] of formData.entries()) {
          if (k === "event_date") {
            eventDate = v;
          } else {
            params[k] = isNaN(v) || v === "" ? v : Number(v);
          }
        }

        if (!_activeScenarioId || !eventDate) return;

        await _addScenarioEvent(_activeScenarioId, _selectedEventType, eventDate, params);
      });
    }

    // Delete event buttons
    pane.querySelectorAll(".sp-btn-delete-event").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const evId = Number(btn.getAttribute("data-event-id"));
        if (evId && _activeScenarioId) {
          await _deleteScenarioEvent(_activeScenarioId, evId);
        }
      });
    });
  }

  async function _createNewScenarioPrompt() {
    const name = prompt("Enter scenario name:", "New Scenario");
    if (!name) return;

    try {
      const resp = await fetch("/api/scenarios/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), description: "" }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const sc = await resp.json();

      _cachedScenarios.push(sc);
      _activeScenarioId = sc.id;
      if (!_selectedScenarioIds.includes(sc.id)) {
        _selectedScenarioIds.push(sc.id);
      }

      await _recalculateBackend();
    } catch (err) {
      console.error("Failed to create scenario:", err);
    }
  }

  async function _deleteScenario(scId) {
    try {
      const resp = await fetch(`/api/scenarios/${scId}/`, { method: "DELETE" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      _cachedScenarios = _cachedScenarios.filter((s) => s.id !== scId);
      _selectedScenarioIds = _selectedScenarioIds.filter((id) => id !== scId);
      if (_activeScenarioId === scId) {
        _activeScenarioId = _cachedScenarios.length > 0 ? _cachedScenarios[0].id : null;
      }

      await _recalculateBackend();
    } catch (err) {
      console.error("Failed to delete scenario:", err);
    }
  }

  async function _addScenarioEvent(scId, eventType, eventDate, params) {
    try {
      const resp = await fetch(`/api/scenarios/${scId}/events/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: eventType,
          event_date: eventDate,
          params: params,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      await _fetchScenarioList();
      await _recalculateBackend();
    } catch (err) {
      console.error("Failed to add scenario event:", err);
    }
  }

  async function _deleteScenarioEvent(scId, evId) {
    try {
      const resp = await fetch(`/api/scenarios/${scId}/events/${evId}/`, { method: "DELETE" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      await _fetchScenarioList();
      await _recalculateBackend();
    } catch (err) {
      console.error("Failed to delete scenario event:", err);
    }
  }

  window.loadScenarioPlanner = loadScenarioPlanner;
})();
