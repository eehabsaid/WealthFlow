"use strict";
window.SP = window.SP || {};


  // ── Event Listeners & Actions (Requirement 6) ──────────────────────────────

  window.SP.attachEventListeners = function(pane) {
    // New scenario button (Header & Rail)
    const btnNewHeader = pane.querySelector("#sp-btn-new-scenario");
    const btnNewRail = pane.querySelector("#sp-btn-rail-new");
    const btnNewEmpty = pane.querySelector("#sp-btn-rail-new-empty");
    const btnTimelineAdd = pane.querySelector("#sp-btn-timeline-add");

    if (btnNewHeader) btnNewHeader.addEventListener("click", window.SP.createNewScenarioPrompt);
    if (btnNewRail) btnNewRail.addEventListener("click", window.SP.createNewScenarioPrompt);
    if (btnNewEmpty) btnNewEmpty.addEventListener("click", window.SP.createNewScenarioPrompt);
    if (btnTimelineAdd) {
      btnTimelineAdd.addEventListener("click", () => {
        window.SP.state.activeSubTab = "builder";
        window.SP.renderScenarioPlannerView(pane);
      });
    }

    // Scenario rail click (select active scenario)
    pane.querySelectorAll("[data-scenario-id]").forEach((el) => {
      el.addEventListener("click", (e) => {
        if (
          e.target.closest(".sp-cmp-check") ||
          e.target.closest(".sp-btn-delete-sc") ||
          e.target.closest(".sp-btn-dup-sc")
        )
          return;
        const scId = Number(el.getAttribute("data-scenario-id"));
        if (scId) {
          window.SP.state.activeScenarioId = scId;
          window.SP.renderScenarioPlannerView(pane);
        }
      });
    });

    // Comparison Checkboxes
    pane.querySelectorAll(".sp-cmp-check").forEach((chk) => {
      chk.addEventListener("change", (e) => {
        const id = Number(e.target.getAttribute("data-id"));
        if (e.target.checked) {
          if (!window.SP.state.selectedScenarioIds.includes(id)) window.SP.state.selectedScenarioIds.push(id);
        } else {
          window.SP.state.selectedScenarioIds = window.SP.state.selectedScenarioIds.filter((x) => x !== id);
        }
        window.SP.debouncedRecalculate();
      });
    });

    // Duplicate Scenario button (Requirement 6)
    pane.querySelectorAll(".sp-btn-dup-sc").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = Number(btn.getAttribute("data-id"));
        if (id) {
          await window.SP.duplicateScenario(id);
        }
      });
    });

    // Delete scenario buttons
    pane.querySelectorAll(".sp-btn-delete-sc").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = Number(btn.getAttribute("data-id"));
        if (id && confirm("Delete this scenario?")) {
          await window.SP.deleteScenario(id);
        }
      });
    });

    // Sub-tab buttons
    ["builder", "dashboard", "compare", "insights"].forEach((tabKey) => {
      const btn = pane.querySelector(`#sp-tab-${tabKey}`);
      if (btn) {
        btn.addEventListener("click", () => {
          window.SP.state.activeSubTab = tabKey;
          window.SP.renderScenarioPlannerView(pane);
        });
      }
    });

    // Event template cards (Builder)
    pane.querySelectorAll(".sp-event-type-card").forEach((card) => {
      card.addEventListener("click", () => {
        window.SP.state.selectedEventType = card.getAttribute("data-event-type");
        window.SP.renderScenarioPlannerView(pane);
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

        if (!window.SP.state.activeScenarioId || !eventDate) return;

        await window.SP.addScenarioEvent(window.SP.state.activeScenarioId, window.SP.state.selectedEventType, eventDate, params);
      });
    }

    // Delete event buttons
    pane.querySelectorAll(".sp-btn-delete-event").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const evId = Number(btn.getAttribute("data-event-id"));
        if (evId && window.SP.state.activeScenarioId) {
          await window.SP.deleteScenarioEvent(window.SP.state.activeScenarioId, evId);
        }
      });
    });
  }

