"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings form: the "Provider and model" group and the page composition (section chips, one card per group,
// sticky Save bar). The other groups are built by settings_groups.js; the generic pieces by layout_helpers.js.

window.AIA.buildProviderHtml = function (ctx) {
  const ui = window.AIA.ui;
  const s = window.AIA.state.currentAISettings;
  const model = escapeHtml(window.AIA.getProviderModelValue(ctx.activeProviderKey));
  const field = (id, key, label, step, min, value, help) =>
    ui.numberField({ id, labelKey: key, label, step, min, value, helpKey: `${key}_help`, help });
  const providerSelect = `<select id="aiProviderSelect" class="form-select" onchange="window.AIA.onAIProviderChanged()">${ctx.providerOptions}</select>`;
  const modelControl = `
    <div class="input-group">
      <input id="aiModelInput" type="text" class="form-control" value="${model}" placeholder="e.g. llama3.2:latest, gpt-4o">
      <button class="btn btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false" id="aiModelDropdownBtn" data-i18n="ai_select_model">${t("ai_select_model", "Models")}</button>
      <ul class="dropdown-menu dropdown-menu-end" id="aiModelDropdownList">
        <li><span class="dropdown-item text-muted small" data-i18n="ai_test_to_load_models">${t("ai_test_to_load_models", "Run Test Connection to list models")}</span></li>
      </ul>
    </div>`;
  const detect = `
    <button type="button" class="btn btn-outline-warning d-flex align-items-center" id="aiRuntimeCapabilitiesBtn" onclick="window.AIA.detectRuntimeCapabilities(this)">
      <i class="bi bi-speedometer2 me-1"></i> <span data-i18n="ai_detect_capabilities">${t("ai_detect_capabilities", "Detect Capabilities & Recommend Config")}</span>
    </button>`;
  const test = `
    <button type="button" class="btn btn-outline-info d-flex align-items-center" id="aiTestConnBtn" onclick="window.AIA.testAIConnectionFromGui()">
      <i class="bi bi-activity me-1"></i> <span data-i18n="ai_test_connection">${t("ai_test_connection", "Test Connection")}</span>
    </button>`;
  return (
    ui.toggleRow({
      id: "aiEnabledToggle",
      checked: !!ctx.enabledChecked,
      labelKey: "ai_enabled",
      label: "Enable AI Advisor",
      helpKey: "ai_enabled_help",
      help: "Turns the whole AI workspace on or off for every user.",
    }) +
    ui.row({
      id: "aiProviderSelect",
      labelKey: "ai_provider",
      label: "Provider",
      control: providerSelect,
    }) +
    ui.row({
      id: "aiModelInput",
      labelKey: "ai_model",
      label: "Model Name / Deployment",
      control: modelControl,
    }) +
    `<div class="aia-row aia-row-wide"><div id="providerSpecificFields" class="row g-3"></div></div>` +
    ui.grid(
      field(
        "aiTemperatureInput",
        "ai_temperature",
        "Temperature",
        "0.05",
        "0.0",
        s.ai_temperature ?? 0.7,
        "Lower is more predictable."
      ) +
        field(
          "aiContextSizeInput",
          "ai_context_size",
          "Context Size",
          "128",
          "256",
          s.ai_context_size ?? 4096,
          "Tokens the model can read at once."
        ) +
        field(
          "aiTimeoutInput",
          "ai_timeout",
          "Timeout (sec)",
          "1",
          "1",
          s.ai_timeout ?? 60,
          "Seconds to wait for one request."
        ),
      3
    ) +
    ui.row({
      id: "aiRuntimeCapabilitiesBtn",
      labelKey: "ai_detect_capabilities_label",
      label: "Detect capabilities",
      helpKey: "ai_detect_capabilities_help",
      help: "Measures this machine and fills the fields above; nothing is saved until you press Save.",
      control: detect,
    }) +
    `<div id="aiRuntimeCapabilitiesResult" class="mb-3" style="display:none;"></div>
    <div class="aia-row aia-row-wide">
            <div class="accordion" id="aiAdvancedAccordion">
                <div class="accordion-item" style="border: 1px solid var(--border-color); background: var(--bg-secondary);">
                    <h2 class="accordion-header" id="headingAdvanced">
                        <button class="accordion-button collapsed fw-semibold" type="button" data-bs-toggle="collapse" data-bs-target="#collapseAdvanced" aria-expanded="false" aria-controls="collapseAdvanced" data-i18n="ai_advanced_params">
                            <i class="bi bi-sliders me-2"></i> ${t("ai_advanced_params", "Advanced Parameters")}
                        </button>
                    </h2>
                    <div id="collapseAdvanced" class="accordion-collapse collapse" aria-labelledby="headingAdvanced" data-bs-parent="#aiAdvancedAccordion">
                        <div class="accordion-body">
                            <div class="mb-3">
                                <label class="form-label fw-semibold" data-i18n="ai_system_prompt">${t("ai_system_prompt", "System Prompt")}</label>
                                <textarea id="aiSystemPromptInput" class="form-control" rows="3">${escapeHtml(window.AIA.state.currentAISettings.ai_system_prompt || "")}</textarea>
                            </div>
                            <div class="row g-3">
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_max_tokens">${t("ai_max_tokens", "Max Tokens")}</label>
                                    <input id="aiMaxTokensInput" type="number" step="64" min="64" class="form-control" value="${window.AIA.state.currentAISettings.ai_max_tokens ?? 2048}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_top_p">${t("ai_top_p", "Top P")}</label>
                                    <input id="aiTopPInput" type="number" step="0.05" min="0.0" max="1.0" class="form-control" value="${window.AIA.state.currentAISettings.ai_top_p ?? 0.9}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_top_k">${t("ai_top_k", "Top K")}</label>
                                    <input id="aiTopKInput" type="number" step="1" min="1" class="form-control" value="${window.AIA.state.currentAISettings.ai_top_k ?? 40}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_repeat_penalty">${t("ai_repeat_penalty", "Repeat Penalty")}</label>
                                    <input id="aiRepeatPenaltyInput" type="number" step="0.05" min="0.5" class="form-control" value="${window.AIA.state.currentAISettings.ai_repeat_penalty ?? 1.1}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold" data-i18n="ai_seed">${t("ai_seed", "Seed (Optional)")}</label>
                                    <input id="aiSeedInput" type="text" class="form-control" value="${escapeHtml(window.AIA.state.currentAISettings.ai_seed || "")}" placeholder="Leave empty for random seed">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold" data-i18n="ai_keep_alive">${t("ai_keep_alive", "Keep Alive")}</label>
                                    <input id="aiKeepAliveInput" type="text" class="form-control" value="${escapeHtml(window.AIA.state.currentAISettings.ai_keep_alive || "5m")}" placeholder="e.g. 5m, 1h, -1">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
    </div>` +
    ui.row({
      id: "aiTestConnBtn",
      labelKey: "ai_test_connection_label",
      label: "Connection",
      helpKey: "ai_test_connection_help",
      help: "Checks that the provider answers with the settings above and lists its models.",
      control: test,
    }) +
    `<div id="aiTestDiagnosticResult" class="mb-3" style="display: none;"></div>`
  );
};

window.AIA.buildAISettingsFormHtml = function (ctx) {
  const ui = window.AIA.ui;
  const s = window.AIA.state.currentAISettings;
  const providerLabel =
    (window.AIA.state.currentProviderSchemas.find((p) => p.key === ctx.activeProviderKey) || {})
      .key || "";
  const bodies = {
    provider: window.AIA.buildProviderHtml(ctx),
    safety: window.AIA.buildSafetyHtml(s),
    routing: window.AIA.buildRoutingHtml(s),
    agent: window.AIA.buildAgentLimitsHtml(s),
    docs: window.AIA.buildDocumentsHtml(s),
    files: window.AIA.buildFilesHtml(s),
    diag: window.AIA.buildDiagnosticsHtml(s),
  };
  const descs = {
    provider: "Which AI runs the advisor and how it is called.",
    safety: "What the AI may touch and how its answers are checked.",
    routing: "How a question is answered before and during an AI run.",
    agent: "Ceilings for each question asked in Agent mode.",
    docs: "Long documents such as the user guide, written one screen at a time.",
    files: "Excel, Word, PDF, CSV and code files built from your data.",
    diag: "For troubleshooting only.",
  };
  const cards = ui.GROUPS.map(([id, icon, key, title]) =>
    ui.card({
      id,
      icon,
      titleKey: key,
      title,
      descKey: `${key}_desc`,
      desc: descs[id],
      body: bodies[id],
      badge:
        id === "provider"
          ? [providerLabel, window.AIA.getProviderModelValue(ctx.activeProviderKey)]
              .filter(Boolean)
              .join(" · ")
          : "",
    })
  ).join("");
  return `
    <p class="aia-intro" data-i18n="ai_settings_desc">${t("ai_settings_desc", "Configure AI provider integration, API endpoints, model selection, and security parameters.")}</p>
    ${ui.chips()}
    <div class="aia-groups">${cards}</div>
    <div class="aia-savebar">
      <button type="button" class="btn btn-primary-custom d-flex align-items-center" id="aiSaveBtn" onclick="window.AIA.saveAISettingsFromGui()">
        <i class="bi bi-check-lg me-1"></i> <span data-i18n="ai_save_settings">${t("ai_save_settings", "Save Settings")}</span>
      </button>
    </div>`;
};
