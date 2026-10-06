"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings form HTML builder (the main settings form markup).

window.AIA.buildAISettingsFormHtml = function (ctx) {
  const { activeProviderKey, providerOptions, enabledChecked, permissionTier, multiAgentChecked } =
    ctx;
  const tierOption = (value, labelKey, fallback) =>
    `<option value="${value}" ${permissionTier === value ? "selected" : ""}>${t(labelKey, fallback)}</option>`;
  return `
        <div class="si-modern-card p-4 mb-4">
            <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-3">
                <div>
                    <p class="text-muted small mb-0" data-i18n="ai_settings_desc">${t("ai_settings_desc", "Configure AI provider integration, API endpoints, model selection, and security parameters.")}</p>
                </div>
                <div class="d-flex align-items-center gap-4 flex-wrap">
                    <div class="d-flex align-items-center gap-2 mb-0">
                        <label class="fs-6 fw-semibold mb-0" for="aiPermissionTierSelect" data-i18n="ai_permission_tier_label">${t("ai_permission_tier_label", "AI Tool Permissions")}</label>
                        <select class="form-select form-select-sm" id="aiPermissionTierSelect" style="width:auto;">
                            ${tierOption("read", "ai_permission_tier_read", "Read Only")}
                            ${tierOption("execute", "ai_permission_tier_execute", "Read + Execute")}
                            ${tierOption("modify", "ai_permission_tier_modify", "Read + Execute + Modify")}
                        </select>
                    </div>
                    <div class="form-check form-switch fs-5 mb-0">
                        <input class="form-check-input" type="checkbox" id="aiMultiAgentToggle" ${multiAgentChecked}>
                        <label class="form-check-label fs-6 fw-semibold ms-2" for="aiMultiAgentToggle" data-i18n="ai_multi_agent_label">${t("ai_multi_agent_label", "Multi-Agent Orchestration")}</label>
                    </div>
${window.AIA.buildPipelineControlsHtml()}
                    <div class="form-check form-switch fs-5 mb-0">
                        <input class="form-check-input" type="checkbox" id="aiEnabledToggle" ${enabledChecked}>
                        <label class="form-check-label fs-6 fw-semibold ms-2" for="aiEnabledToggle" data-i18n="ai_enabled">${t("ai_enabled", "Enable AI Advisor")}</label>
                    </div>
                </div>
            </div>

            <!-- Provider Selection & Dynamic Fields Container -->
            <div class="row g-3 mb-4">
                <div class="col-md-6">
                    <label class="form-label fw-semibold" data-i18n="ai_provider">${t("ai_provider", "Provider")}</label>
                    <select id="aiProviderSelect" class="form-select" onchange="window.AIA.onAIProviderChanged()">
                        ${providerOptions}
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-semibold" data-i18n="ai_model">${t("ai_model", "Model Name / Deployment")}</label>
                    <div class="input-group">
                        <input id="aiModelInput" type="text" class="form-control" value="${escapeHtml(window.AIA.getProviderModelValue(activeProviderKey))}" placeholder="e.g. llama3.2:latest, gpt-4o">
                        <button class="btn btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false" id="aiModelDropdownBtn" data-i18n="ai_select_model">${t("ai_select_model", "Models")}</button>
                        <ul class="dropdown-menu dropdown-menu-end" id="aiModelDropdownList">
                            <li><span class="dropdown-item text-muted small" data-i18n="ai_test_to_load_models">${t("ai_test_to_load_models", "Run Test Connection to list models")}</span></li>
                        </ul>
                    </div>
                </div>

                <!-- Container for provider-specific config inputs (API Key, Base URL, etc.) -->
                <div class="col-12">
                    <div id="providerSpecificFields" class="row g-3"></div>
                </div>

                <div class="col-md-4">
                    <label class="form-label fw-semibold" data-i18n="ai_temperature">${t("ai_temperature", "Temperature")}</label>
                    <input id="aiTemperatureInput" type="number" step="0.05" min="0.0" max="2.0" class="form-control" value="${window.AIA.state.currentAISettings.ai_temperature ?? 0.7}">
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-semibold" data-i18n="ai_context_size">${t("ai_context_size", "Context Size")}</label>
                    <input id="aiContextSizeInput" type="number" step="128" min="256" class="form-control" value="${window.AIA.state.currentAISettings.ai_context_size ?? 4096}">
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-semibold" data-i18n="ai_timeout">${t("ai_timeout", "Timeout (sec)")}</label>
                    <input id="aiTimeoutInput" type="number" step="1" min="1" class="form-control" value="${window.AIA.state.currentAISettings.ai_timeout ?? 60}">
                </div>
            </div>

            <!-- Runtime capability inspection (hardware + Ollama /api/show + a live timing
                 benchmark) -> recommended context/max-tokens/timeout/keep-alive. Preview only:
                 fills the fields above, doesn't save anything until "Save Settings" is clicked. -->
            <div class="mb-4">
                <button type="button" class="btn btn-outline-warning d-flex align-items-center" id="aiRuntimeCapabilitiesBtn" onclick="window.AIA.detectRuntimeCapabilities(this)">
                    <i class="bi bi-speedometer2 me-1"></i> <span data-i18n="ai_detect_capabilities">${t("ai_detect_capabilities", "Detect Capabilities & Recommend Config")}</span>
                </button>
                <div id="aiRuntimeCapabilitiesResult" class="mt-3" style="display:none;"></div>
            </div>

            <!-- Diagnostics Card / Result -->
            <div id="aiTestDiagnosticResult" class="mb-4" style="display: none;"></div>

            <!-- Advanced Parameters Accordion -->
            <div class="accordion mb-4" id="aiAdvancedAccordion">
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

            <!-- Action Buttons -->
            <div class="d-flex justify-content-end gap-2">
                <button type="button" class="btn btn-outline-info d-flex align-items-center" id="aiTestConnBtn" onclick="window.AIA.testAIConnectionFromGui()">
                    <i class="bi bi-activity me-1"></i> <span data-i18n="ai_test_connection">${t("ai_test_connection", "Test Connection")}</span>
                </button>
                <button type="button" class="btn btn-primary-custom d-flex align-items-center" id="aiSaveBtn" onclick="window.AIA.saveAISettingsFromGui()">
                    <i class="bi bi-check-lg me-1"></i> <span data-i18n="ai_save_settings">${t("ai_save_settings", "Save Settings")}</span>
                </button>
            </div>
        </div>`;
};
