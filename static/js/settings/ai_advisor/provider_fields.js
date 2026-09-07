"use strict";
// AI Advisor settings: Provider dropdown + dynamic field rendering.

window.AIA = window.AIA || {};

window.AIA.getProviderModelValue = function(providerKey) {
  if (!window.AIA.state.currentAISettings) return "";
  if (providerKey === "ollama") return window.AIA.state.currentAISettings.ai_model || "";
  if (providerKey === "openai") return window.AIA.state.currentAISettings.ai_openai_model || "";
  if (providerKey === "claude") return window.AIA.state.currentAISettings.ai_claude_model || "";
  if (providerKey === "gemini") return window.AIA.state.currentAISettings.ai_gemini_model || "";
  if (providerKey === "azure") return window.AIA.state.currentAISettings.ai_azure_deployment || "";
  return window.AIA.state.currentAISettings.ai_model || "";
}

window.AIA.onAIProviderChanged = function() {
  const pKey = document.getElementById("aiProviderSelect")?.value || "ollama";
  window.AIA.renderProviderFields(pKey);
  const mInput = document.getElementById("aiModelInput");
  if (mInput) {
    mInput.value = window.AIA.getProviderModelValue(pKey);
  }
}

window.AIA.renderProviderFields = function(providerKey) {
  const container = document.getElementById("providerSpecificFields");
  if (!container) return;

  const schema = window.AIA.state.currentProviderSchemas.find((s) => s.key === providerKey);
  if (!schema || !Array.isArray(schema.fields) || schema.fields.length === 0) {
    container.innerHTML = "";
    return;
  }

  container.innerHTML = schema.fields
    .map((f) => {
      if (
        f.name === "ai_model" ||
        f.name === "ai_openai_model" ||
        f.name === "ai_claude_model" ||
        f.name === "ai_gemini_model" ||
        f.name === "ai_azure_deployment"
      ) {
        return ""; // Model is rendered in main top control
      }
      const val = window.AIA.state.currentAISettings ? (window.AIA.state.currentAISettings[f.name] ?? "") : "";
      const label = t(f.label_key || f.name, f.name);
      const inputType = f.type || "text";
      const placeholder = f.placeholder ? `placeholder="${escapeHtml(f.placeholder)}"` : "";

      return `
            <div class="col-md-6">
                <label class="form-label fw-semibold" data-i18n="${f.label_key || f.name}">${label}</label>
                <input id="${f.name}" type="${inputType}" class="form-control" value="${escapeHtml(val)}" ${placeholder}>
            </div>`;
    })
    .join("");

  if (typeof applyTranslations === "function") {
    applyTranslations();
  }
}

