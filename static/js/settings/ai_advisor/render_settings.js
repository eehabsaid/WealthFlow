"use strict";
// AI Advisor settings: main render orchestrator. Split from the former
// monolithic ai_advisor.js (200-line rule). Sibling files:
// - state.js                    Shared window.AIA.state + escapeHtml helper
// - render_settings_form.js     Builds the settings form HTML
// - provider_fields.js          Provider dropdown + dynamic field rendering
// - connection_test.js          "Test Connection" button handler
// - diagnostics_model_select.js Diagnostic result rendering + model picker
// - save_settings.js            "Save" button handler
// - platform_overview_actions.js  Platform overview panel + scan/promote actions

window.AIA = window.AIA || {};

window.AIA.renderAIAdvisorSettings = async function() {
  const container = document.getElementById("settingsContent");
  if (!container) return;

  // Show loading state
  container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>`;

  try {
    const res = await fetch("/api/settings/ai/");
    if (!res.ok) {
      throw new Error("Failed to load AI settings from backend.");
    }

    window.AIA.state.currentAISettings = await res.json();
    window.AIA.state.currentProviderSchemas = Array.isArray(window.AIA.state.currentAISettings.providers_schema)
      ? window.AIA.state.currentAISettings.providers_schema
      : [];
  } catch (err) {
    container.innerHTML = `
            <div class="alert alert-danger d-flex align-items-center m-3" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2 fs-4"></i>
                <div>
                    <strong>${t("ai_load_failed_title", "Unable to load AI Advisor Settings")}</strong><br>
                    ${t("ai_load_failed_desc", "Could not retrieve configuration from the backend server. Please try refreshing or check server logs.")}
                </div>
            </div>`;
    return;
  }

  const activeProviderKey = window.AIA.state.currentAISettings.ai_provider || "ollama";
  const providerOptions = window.AIA.state.currentProviderSchemas
    .map((p) => {
      const selected = p.key === activeProviderKey ? "selected" : "";
      const label = t(p.label_key, p.key.toUpperCase());
      return `<option value="${p.key}" ${selected}>${label}</option>`;
    })
    .join("");

  const enabledChecked = window.AIA.state.currentAISettings.ai_enabled ? "checked" : "";
  const readOnlyChecked = (window.AIA.state.currentAISettings.ai_read_only ?? true) ? "checked" : "";

  const html = window.AIA.buildAISettingsFormHtml({
    activeProviderKey, providerOptions, enabledChecked, readOnlyChecked,
  });
  container.innerHTML = html;

  window.AIA.loadAIPlatformOverviewData();

  window.AIA.renderProviderFields(activeProviderKey);

  if (typeof applyTranslations === "function") {
    applyTranslations();
  }
}

