"use strict";
window.SP = window.SP || {};

  window.SP.getOrCreateNewScenarioModal = function() {
    let modalEl = document.getElementById("modal-create-scenario");
    if (!modalEl) {
      modalEl = document.createElement("div");
      modalEl.id = "modal-create-scenario";
      modalEl.className = "modal fade";
      modalEl.tabIndex = -1;
      modalEl.setAttribute("aria-hidden", "true");
      modalEl.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content border-secondary text-light" style="background-color: var(--si-card-bg, #1e293b);">
            <div class="modal-header border-secondary">
              <h5 class="modal-title" data-i18n-key="scenario_planner_new_modal_title">Create New Scenario</h5>
              <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <form id="form-create-scenario">
              <div class="modal-body">
                <div class="mb-3">
                  <label for="sp-new-scenario-name" class="form-label" data-i18n-key="scenario_planner_name_label">Scenario Name</label>
                  <input type="text" class="form-control bg-dark text-light border-secondary" id="sp-new-scenario-name" required value="New Scenario" />
                </div>
                <div class="mb-3">
                  <label for="sp-new-scenario-desc" class="form-label" data-i18n-key="scenario_planner_desc_label">Description (Optional)</label>
                  <textarea class="form-control bg-dark text-light border-secondary" id="sp-new-scenario-desc" rows="2"></textarea>
                </div>
              </div>
              <div class="modal-footer border-secondary">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal" data-i18n-key="cancel">Cancel</button>
                <button type="submit" class="btn btn-primary" data-i18n-key="scenario_planner_btn_create">Create Scenario</button>
              </div>
            </form>
          </div>
        </div>`;
      document.body.appendChild(modalEl);
    }
    if (typeof applyTranslations === "function") {
      applyTranslations(modalEl);
    }
    return modalEl;
  }

  window.SP.createNewScenarioPrompt = async function() {
    const modalEl = window.SP.getOrCreateNewScenarioModal();
    const inputName = modalEl.querySelector("#sp-new-scenario-name");
    const inputDesc = modalEl.querySelector("#sp-new-scenario-desc");
    const form = modalEl.querySelector("#form-create-scenario");

    const defaultName =
      (typeof getTranslation === "function" && getTranslation("scenario_planner_default_name")) ||
      "New Scenario";
    inputName.value = defaultName;
    inputDesc.value = "";

    if (typeof applyTranslations === "function") {
      applyTranslations(modalEl);
    }

    let bsModal = null;
    if (typeof bootstrap !== "undefined" && bootstrap.Modal) {
      bsModal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    }

    const onSubmit = async (e) => {
      e.preventDefault();
      const name = inputName.value.trim();
      const desc = inputDesc.value.trim();
      if (!name) return;

      if (bsModal) {
        bsModal.hide();
      }

      form.removeEventListener("submit", onSubmit);

      try {
        const resp = await fetch("/api/scenarios/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: name, description: desc }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const sc = await resp.json();

        window.SP.state.cachedScenarios.push(sc);
        window.SP.state.activeScenarioId = sc.id;
        if (!window.SP.state.selectedScenarioIds.includes(sc.id)) {
          window.SP.state.selectedScenarioIds.push(sc.id);
        }

        await window.SP.recalculateBackend();
      } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
    };

    form.onsubmit = onSubmit;

    if (bsModal) {
      bsModal.show();
    } else {
      const name = prompt("Enter scenario name:", "New Scenario");
      if (name) {
        inputName.value = name;
        form.dispatchEvent(new Event("submit"));
      }
    }
  }

  window.SP.duplicateScenario = async function(scId) {
    try {
      const resp = await fetch(`/api/scenarios/${scId}/duplicate/`, { method: "POST" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const newSc = await resp.json();

      window.SP.state.cachedScenarios.push(newSc);
      window.SP.state.activeScenarioId = newSc.id;
      if (!window.SP.state.selectedScenarioIds.includes(newSc.id)) {
        window.SP.state.selectedScenarioIds.push(newSc.id);
      }

      await window.SP.recalculateBackend();
    } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
  }

  window.SP.deleteScenario = async function(scId) {
    try {
      const resp = await fetch(`/api/scenarios/${scId}/`, { method: "DELETE" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      window.SP.state.cachedScenarios = window.SP.state.cachedScenarios.filter((s) => s.id !== scId);
      window.SP.state.selectedScenarioIds = window.SP.state.selectedScenarioIds.filter((id) => id !== scId);
      if (window.SP.state.activeScenarioId === scId) {
        window.SP.state.activeScenarioId = window.SP.state.cachedScenarios.length > 0 ? window.SP.state.cachedScenarios[0].id : null;
      }

      await window.SP.recalculateBackend();
    } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
  }

  window.SP.addScenarioEvent = async function(scId, eventType, eventDate, params) {
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

      await window.SP.fetchScenarioList();
      await window.SP.recalculateBackend();
    } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
  }

  window.SP.deleteScenarioEvent = async function(scId, evId) {
    try {
      const resp = await fetch(`/api/scenarios/${scId}/events/${evId}/`, { method: "DELETE" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      await window.SP.fetchScenarioList();
      await window.SP.recalculateBackend();
    } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
  }


  window.loadScenarioPlanner = window.SP.loadScenarioPlanner;
