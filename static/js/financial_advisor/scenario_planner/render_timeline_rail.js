"use strict";
window.SP = window.SP || {};

// ── Requirement 1: Chronological Life Event Timeline Strip ───────────────

window.SP.buildTimelineHtml = function () {
  const scenarios = window.SP.state.scenarioPlannerData?.scenarios || [];

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
    {
      label: typeof t === "function" ? t("balance_tab_overview", "Today") : "Today",
      dateStr: todayFormatted,
      type: "now",
      chip: "Baseline",
    },
  ];

  let hasRetirementEvent = false;

  allEvents.forEach((ev) => {
    if (ev.event_type === "retirement") hasRetirementEvent = true;
    const evLabelKey = `scenario_planner_event_${ev.event_type}`;
    const translatedLabel = typeof t === "function" ? t(evLabelKey, ev.event_type) : ev.event_type;
    timelineNodes.push({
      label: translatedLabel,
      dateStr: typeof formatDate === "function" ? formatDate(ev.event_date) : ev.event_date || "",
      type: ev.event_type || "event",
      chip: ev.scenarioName,
    });
  });

  if (!hasRetirementEvent) {
    const birthYear = window.SP.state.scenarioPlannerData?.user_birth_year;
    const targetAge = window.SP.state.scenarioPlannerData?.config?.DEFAULT_RETIREMENT_AGE || 60;
    const targetYear = birthYear ? birthYear + targetAge : new Date().getFullYear() + 20;

    timelineNodes.push({
      label:
        typeof t === "function"
          ? t("scenario_planner_event_retirement", "Retirement Target")
          : "Retirement Target",
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
};

// ── Requirement 6: Improved Scenario Management Rail ─────────────────────

window.SP.buildScenarioRailHtml = function () {
  if (window.SP.state.cachedScenarios.length === 0) {
    return `
        <div class="p-3 text-center text-muted extra-small rounded" style="background:var(--bg-tertiary);">
          <p class="m-0 mb-2">No saved scenarios yet.</p>
          <button class="btn btn-sm btn-primary py-1 px-3" id="sp-btn-rail-new-empty">+ Create Scenario</button>
        </div>
      `;
  }

  return window.SP.state.cachedScenarios
    .map((sc) => {
      const isActive = sc.id === window.SP.state.activeScenarioId;
      const isChecked = window.SP.state.selectedScenarioIds.includes(sc.id);
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
};

window.SP.buildSubTabContentHtml = function () {
  if (window.SP.state.activeSubTab === "builder") {
    return window.SP.buildBuilderPaneHtml();
  }
  if (window.SP.state.activeSubTab === "dashboard") {
    return window.SP.buildDashboardPaneHtml();
  }
  if (window.SP.state.activeSubTab === "compare") {
    return window.SP.buildComparePaneHtml();
  }
  if (window.SP.state.activeSubTab === "insights") {
    return window.SP.buildInsightsPaneHtml();
  }
  return "";
};
