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
          ${_buildTimelineHtml()}
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

  // ── Requirement 1: Chronological Life Event Timeline Strip ───────────────

  function _buildTimelineHtml() {
    const scenarios = _scenarioPlannerData?.scenarios || [];

    // Collect events across selected scenarios
    const allEvents = [];
    scenarios.forEach((sc) => {
      (sc.events || []).forEach((ev) => {
        allEvents.push({ ...ev, scenarioName: sc.name || `Scenario ${sc.id}` });
      });
    });

    // Clean Empty State if no events exist (Requirement 1)
    if (allEvents.length === 0) {
      return `
        <div class="py-3 text-center text-muted extra-small rounded" style="background:var(--bg-tertiary); border:1px dashed var(--border-color);">
          <i class="bi bi-calendar-event me-2 text-primary fs-6"></i>
          <span>No life events added yet.</span>
          <button class="btn btn-sm btn-link p-0 text-primary fw-bold ms-2 text-decoration-none" id="sp-btn-timeline-add">
            + Add Your First Event
          </button>
        </div>
      `;
    }

    // Sort events strictly in chronological order by date
    allEvents.sort((a, b) => new Date(a.event_date) - new Date(b.event_date));

    const todayFormatted = typeof formatDate === "function" ? formatDate(new Date()) : "";
    const timelineNodes = [
      { label: typeof t === "function" ? t("balance_tab_overview", "Today") : "Today", dateStr: todayFormatted, type: "now", chip: "Baseline" },
    ];

    let hasRetirementEvent = false;

    allEvents.forEach((ev) => {
      if (ev.event_type === "retirement") hasRetirementEvent = true;
      const evLabelKey = `scenario_planner_event_${ev.event_type}`;
      const translatedLabel = typeof t === "function" ? t(evLabelKey, ev.event_type) : ev.event_type;
      timelineNodes.push({
        label: translatedLabel,
        dateStr: typeof formatDate === "function" ? formatDate(ev.event_date) : (ev.event_date || ""),
        type: ev.event_type || "event",
        chip: ev.scenarioName,
      });
    });

    if (!hasRetirementEvent) {
      const birthYear = _scenarioPlannerData?.user_birth_year;
      const targetAge = _scenarioPlannerData?.config?.DEFAULT_RETIREMENT_AGE || 60;
      const targetYear = birthYear ? (birthYear + targetAge) : (new Date().getFullYear() + 20);

      timelineNodes.push({
        label: typeof t === "function" ? t("scenario_planner_event_retirement", "Retirement Target") : "Retirement Target",
        dateStr: `${targetYear}`,
        type: "retirement",
        chip: "Target",
      });
    }

    return `
      <div class="d-flex align-items-center gap-4 overflow-x-auto py-2">
        ${timelineNodes
          .map(
            (node) => `
          <div class="d-flex flex-column align-items-center text-center flex-shrink-0" style="min-width:115px;">
            <div class="rounded-circle d-flex align-items-center justify-content-center mb-1" style="width:30px; height:30px; background:var(--bg-tertiary); border:2px solid var(--accent-primary);">
              <i class="bi ${node.type === "now" ? "bi-geo-alt-fill text-primary" : node.type === "retirement" ? "bi-flag-fill text-warning" : "bi-calendar-check-fill text-info"}" style="font-size:12px;"></i>
            </div>
            <span class="fw-bold extra-small text-truncate style="color:var(--text-primary); max-width:105px;">${node.label}</span>
            <span class="extra-small style="color:var(--text-muted);">${node.dateStr}</span>
            <span class="badge bg-secondary extra-small mt-1">${node.chip}</span>
          </div>
        `
          )
          .join("")}
      </div>
    `;
  }

  // ── Requirement 6: Improved Scenario Management Rail ─────────────────────

  function _buildScenarioRailHtml() {
    if (_cachedScenarios.length === 0) {
      return `
        <div class="p-3 text-center text-muted extra-small rounded" style="background:var(--bg-tertiary);">
          <p class="m-0 mb-2">No saved scenarios yet.</p>
          <button class="btn btn-sm btn-primary py-1 px-3" id="sp-btn-rail-new-empty">+ Create Scenario</button>
        </div>
      `;
    }

    return _cachedScenarios
      .map((sc) => {
        const isActive = sc.id === _activeScenarioId;
        const isChecked = _selectedScenarioIds.includes(sc.id);
        const eventCount = (sc.events || []).length;

        return `
        <div class="card p-2 border-0 ${isActive ? "border-primary" : ""}" style="background:${isActive ? "rgba(26,110,245,0.12)" : "var(--bg-tertiary)"}; border:1px solid ${isActive ? "var(--accent-primary)" : "var(--border-color)"}; border-radius:8px; cursor:pointer;" data-scenario-id="${sc.id}">
          <div class="d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center gap-2">
              <input type="checkbox" class="form-check-input sp-cmp-check" data-id="${sc.id}" ${isChecked ? "checked" : ""} title="Include in comparison">
              <div>
                <div class="fw-bold small" style="color:var(--text-primary);">${sc.name}</div>
                <div class="extra-small" style="color:var(--text-muted);">${eventCount} event(s)</div>
              </div>
            </div>
            <div class="d-flex align-items-center gap-1">
              <button class="btn btn-sm btn-link text-secondary p-0 sp-btn-dup-sc" data-id="${sc.id}" title="Duplicate Scenario">
                <i class="bi bi-files"></i>
              </button>
              <button class="btn btn-sm btn-link text-danger p-0 sp-btn-delete-sc" data-id="${sc.id}" title="Delete Scenario">
                <i class="bi bi-trash"></i>
              </button>
            </div>
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

  // ── Requirement 2 & 7: Redesigned Event Templates & Chronological Flow ──

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

    // Template Subtitles mapping (Requirement 7)
    const templateSubtitles = {
      house: "Property Purchase & Mortgage",
      car: "Vehicle Acquisition & Installments",
      salary_change: "Income Scaling & Adjustments",
      marriage: "Wedding & Household Setup",
      child: "Newborn & Family Care",
      retirement: "Retirement Transition Plan",
      inheritance: "Windfall & Inheritance Inflow",
      medical: "Healthcare & Care Expenses",
      business: "Capital Investment & Profits",
      job_loss: "Employment Transition / Safety Buffer",
    };

    // Sort configured events chronologically (Requirement 2)
    const configuredEvents = [...(activeScenario.events || [])];
    configuredEvents.sort((a, b) => new Date(a.event_date) - new Date(b.event_date));

    return `
      <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
        <div class="d-flex align-items-center justify-content-between mb-3">
          <h5 class="fw-bold m-0" style="color:var(--text-primary);">${activeScenario.name} — Life Event Builder</h5>
          <span class="badge bg-primary">${configuredEvents.length} Event(s) Configured</span>
        </div>

        <!-- Requirement 7: Redesigned Larger Visual Event Template Tiles -->
        <label class="form-label small fw-semibold mb-2" style="color:var(--text-primary);" data-i18n="scenario_planner_select_event_type">Select Event Template</label>
        <div class="row row-cols-2 row-cols-md-5 g-2 mb-4">
          ${schema
            .map((item) => {
              const isSelected = item.event_type === _selectedEventType;
              const sub = templateSubtitles[item.event_type] || "Life Event Template";
              return `
            <div class="col">
              <div class="p-3 text-center rounded border sp-event-type-card ${isSelected ? "border-primary bg-primary bg-opacity-15 shadow-sm" : ""}" style="cursor:pointer; background:var(--bg-tertiary); height:110px; display:flex; flex-direction:column; justify-content:center; align-items:center;" data-event-type="${item.event_type}">
                <div class="rounded-circle d-flex align-items-center justify-content-center mb-2" style="width:36px; height:36px; background:rgba(26,110,245,0.15);">
                  <i class="bi ${item.icon} text-primary fs-5"></i>
                </div>
                <div class="fw-bold extra-small text-truncate w-100" style="color:var(--text-primary);" data-i18n="${item.label_key}">${item.event_type}</div>
                <div class="extra-small text-muted text-truncate w-100 mt-1" style="font-size:10px;">${sub}</div>
              </div>
            </div>
          `;
            })
            .join("")}
        </div>

        <!-- Dynamic Event Form -->
        <div class="p-3 mb-4 rounded" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
          <h6 class="fw-bold mb-3 d-flex align-items-center gap-2" style="color:var(--text-primary);">
            <i class="bi bi-sliders text-primary"></i>
            <span data-i18n="${selectedSchema?.label_key || "scenario_planner_add_event"}">Configure Parameters</span>
          </h6>
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

        <!-- Requirement 2: Chronological Life-Event Flow Cards -->
        <h6 class="fw-bold mb-3 d-flex align-items-center gap-2" style="color:var(--text-primary);">
          <i class="bi bi-diagram-3-fill text-primary"></i>
          <span>Chronological Life-Event Flow</span>
        </h6>
        ${
          configuredEvents.length === 0
            ? `
          <div class="p-4 text-center text-muted extra-small rounded" style="background:var(--bg-tertiary); border:1px dashed var(--border-color);">
            <i class="bi bi-info-circle fs-5 d-block mb-2 text-primary"></i>
            <span>No events added to this scenario yet. Select an event template above to add your first event.</span>
          </div>
        `
            : `
          <div class="d-flex flex-column gap-3 position-relative ps-3" style="border-left:2px solid var(--accent-primary);">
            ${configuredEvents
              .map(
                (ev) => `
              <div class="card p-3 border-0 rounded position-relative" style="background:var(--bg-tertiary); border:1px solid var(--border-color); border-radius:10px;">
                <div class="d-flex flex-wrap align-items-center justify-content-between gap-2">
                  <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-primary me-1">${ev.event_type ? ev.event_type.replace("_", " ").toUpperCase() : "EVENT"}</span>
                    <span class="fw-bold small text-light">${typeof formatDate === "function" ? formatDate(ev.event_date) : ev.event_date}</span>
                  </div>
                  <button class="btn btn-sm btn-link text-danger p-0 sp-btn-delete-event" data-event-id="${ev.id}" title="Remove Event">
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
                <div class="mt-2 d-flex flex-wrap gap-2">
                  ${Object.entries(ev.params || {})
                    .map(([k, v]) => `<span class="badge bg-secondary bg-opacity-50 text-light extra-small">${k.replace("_", " ")}: ${v}</span>`)
                    .join("")}
                </div>
              </div>
            `
              )
              .join("")}
          </div>
        `
        }
      </div>
    `;
  }

  // ── Requirement 4: Enhanced KPI Cards with Visual Change Indicators ───────

  function _buildDashboardPaneHtml() {
    const base = _scenarioPlannerData?.baseline || {};
    const scList = _scenarioPlannerData?.scenarios || [];
    const activeSc = scList.find((s) => s.id === _activeScenarioId) || scList[0] || base;

    // Deltas vs Baseline
    const nwVal = activeSc.net_worth_12m || 0;
    const nwBase = base.net_worth_12m || 0;
    const nwDelta = nwVal - nwBase;

    const flowVal = activeSc.monthly_cash_flow || 0;
    const flowBase = base.monthly_cash_flow || 0;
    const flowDelta = flowVal - flowBase;

    const debtVal = activeSc.total_debt || 0;
    const debtBase = base.total_debt || 0;
    const debtDelta = debtVal - debtBase;

    const covVal = activeSc.cash_coverage_months;
    const covBase = base.cash_coverage_months;
    const covDelta = covVal !== null && covBase !== null ? covVal - covBase : 0;

    const retireObj = activeSc.retirement_readiness || {};
    const readinessPct = retireObj.readiness_pct || 0;
    const baseReadiness = base.retirement_readiness?.readiness_pct || 0;
    const readinessDelta = readinessPct - baseReadiness;

    function _renderKpiBadge(delta, isInverse = false) {
      if (delta === 0 || isNaN(delta)) {
        return `<span class="badge bg-secondary extra-small"><i class="bi bi-dash"></i> Baseline</span>`;
      }
      const isGood = isInverse ? delta < 0 : delta > 0;
      const colorClass = isGood ? "bg-success text-white" : "bg-danger text-white";
      const icon = isGood ? "bi-arrow-up-right" : "bi-arrow-down-right";
      const sign = delta > 0 ? "+" : "";
      return `<span class="badge ${colorClass} extra-small"><i class="bi ${icon}"></i> ${sign}${typeof delta === "number" ? delta.toFixed(1) : delta}</span>`;
    }

    return `
      <div class="d-flex flex-column gap-4">
        <!-- Requirement 4: Enhanced KPI Cards with Visual Change Indicators -->
        <div class="row row-cols-1 row-cols-md-5 g-3">
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_networth">Net Worth (12m)</div>
                ${_renderKpiBadge(nwDelta)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${_money(nwVal)}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${_money(nwBase)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_cashflow">Monthly Cash Flow</div>
                ${_renderKpiBadge(flowDelta)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${_money(flowVal)}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${_money(flowBase)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_debt">Total Debt</div>
                ${_renderKpiBadge(debtDelta, true)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${_money(debtVal)}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${_money(debtBase)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_coverage">Cash Coverage</div>
                ${_renderKpiBadge(covDelta)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${covVal !== null && covVal !== undefined ? covVal + " mo" : "-"}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${covBase ?? "-"} mo</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_readiness">Retirement Readiness</div>
                ${_renderKpiBadge(readinessDelta)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${readinessPct}%</div>
              <div class="extra-small text-muted mt-1">Baseline: ${baseReadiness}%</div>
            </div>
          </div>
        </div>

        <!-- MULTI-SERIES CHART CARD (Requirement 3) -->
        <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
          <h5 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="scenario_planner_chart_title">Net Worth Trajectory Comparison</h5>
          <div style="height:320px; position:relative;">
            <canvas id="scenarioPlannerChart"></canvas>
          </div>
        </div>
      </div>
    `;
  }

  // ── Requirement 3: Scrollable N-Scenario Comparison Table ─────────────────

  function _buildComparePaneHtml() {
    const base = _scenarioPlannerData?.baseline || {};
    const scenarios = _scenarioPlannerData?.scenarios || [];

    return `
      <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
        <h5 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="scenario_planner_compare_title">Side-by-Side N-Scenario Comparison</h5>

        <!-- Requirement 3: Scrollable N-scenario table -->
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

  // ── Requirement 5: Actionable Insights with Financial Impact & Alternatives

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
              <h6 class="fw-bold mb-3" style="color:var(--text-primary);">${sc.name} — Actionable Financial Insights</h6>
              <div class="d-flex flex-column gap-3">
                ${insights
                  .map(
                    (ins) => `
                  <div class="p-3 rounded d-flex align-items-start gap-3" style="background:var(--bg-tertiary); border:1px solid var(--border-color); border-radius:10px;">
                    <i class="bi ${ins.severity === "good" ? "bi-check-circle-fill text-success" : ins.severity === "bad" ? "bi-exclamation-octagon-fill text-danger" : "bi-exclamation-triangle-fill text-warning"} fs-4 mt-1"></i>
                    <div class="w-100">
                      <div class="fw-bold small text-light mb-1" data-i18n="${ins.title_key}">${ins.title_key}</div>
                      <div class="extra-small text-muted mb-2" data-i18n="${ins.body_key}">${ins.body_key}</div>

                      <!-- Structured Impact, Action, and Alternative -->
                      <div class="p-2 rounded bg-dark bg-opacity-50 border border-secondary border-opacity-25 d-flex flex-column gap-1">
                        ${ins.impact_text ? `<div class="extra-small text-info"><strong><i class="bi bi-pie-chart-fill me-1"></i>Financial Impact:</strong> ${ins.impact_text}</div>` : ""}
                        ${ins.action_text ? `<div class="extra-small text-primary"><strong><i class="bi bi-lightning-charge-fill me-1"></i>Recommended Action:</strong> ${ins.action_text}</div>` : ""}
                        ${ins.alternative_text ? `<div class="extra-small text-warning"><strong><i class="bi bi-arrow-repeat me-1"></i>Alternative Option:</strong> ${ins.alternative_text}</div>` : ""}
                      </div>
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

  // ── Event Listeners & Actions (Requirement 6) ──────────────────────────────

  function _attachEventListeners(pane) {
    // New scenario button (Header & Rail)
    const btnNewHeader = pane.querySelector("#sp-btn-new-scenario");
    const btnNewRail = pane.querySelector("#sp-btn-rail-new");
    const btnNewEmpty = pane.querySelector("#sp-btn-rail-new-empty");
    const btnTimelineAdd = pane.querySelector("#sp-btn-timeline-add");

    if (btnNewHeader) btnNewHeader.addEventListener("click", _createNewScenarioPrompt);
    if (btnNewRail) btnNewRail.addEventListener("click", _createNewScenarioPrompt);
    if (btnNewEmpty) btnNewEmpty.addEventListener("click", _createNewScenarioPrompt);
    if (btnTimelineAdd) {
      btnTimelineAdd.addEventListener("click", () => {
        _activeSubTab = "builder";
        _renderScenarioPlannerView(pane);
      });
    }

    // Scenario rail click (select active scenario)
    pane.querySelectorAll("[data-scenario-id]").forEach((el) => {
      el.addEventListener("click", (e) => {
        if (e.target.closest(".sp-cmp-check") || e.target.closest(".sp-btn-delete-sc") || e.target.closest(".sp-btn-dup-sc")) return;
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

    // Duplicate Scenario button (Requirement 6)
    pane.querySelectorAll(".sp-btn-dup-sc").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = Number(btn.getAttribute("data-id"));
        if (id) {
          await _duplicateScenario(id);
        }
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

    // Event template cards (Builder)
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

  async function _duplicateScenario(scId) {
    try {
      const resp = await fetch(`/api/scenarios/${scId}/duplicate/`, { method: "POST" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const newSc = await resp.json();

      _cachedScenarios.push(newSc);
      _activeScenarioId = newSc.id;
      if (!_selectedScenarioIds.includes(newSc.id)) {
        _selectedScenarioIds.push(newSc.id);
      }

      await _recalculateBackend();
    } catch (err) {
      console.error("Failed to duplicate scenario:", err);
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
