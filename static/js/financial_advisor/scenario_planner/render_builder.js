"use strict";
window.SP = window.SP || {};


  // ── Requirement 2 & 7: Redesigned Event Templates & Chronological Flow ──

  window.SP.buildBuilderPaneHtml = function() {
    const activeScenario = window.SP.state.cachedScenarios.find((s) => s.id === window.SP.state.activeScenarioId);
    if (!activeScenario) {
      return `
        <div class="alert alert-info" data-i18n="scenario_planner_select_scenario_hint">
          Select or create a scenario from the left rail to edit its events.
        </div>
      `;
    }

    const schema = window.SP.state.cachedEventSchema || [];
    const selectedSchema = schema.find((s) => s.event_type === window.SP.state.selectedEventType) || schema[0];

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
              const isSelected = item.event_type === window.SP.state.selectedEventType;
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
                    .map(
                      ([k, v]) =>
                        `<span class="badge bg-secondary bg-opacity-50 text-light extra-small">${k.replace("_", " ")}: ${v}</span>`
                    )
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

