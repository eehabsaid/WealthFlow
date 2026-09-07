"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings form HTML builder (the main settings form markup).

window.AIA.buildAISettingsFormHtml = function (ctx) {
  const { activeProviderKey, providerOptions, enabledChecked, readOnlyChecked } = ctx;
  return `
        <div class="si-modern-card p-4 mb-4">
            <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-3">
                <div>
                    <p class="text-muted small mb-0" data-i18n="ai_settings_desc">${t("ai_settings_desc", "Configure AI provider integration, API endpoints, model selection, and security parameters.")}</p>
                </div>
                <div class="d-flex align-items-center gap-4 flex-wrap">
                    <div class="form-check form-switch fs-5 mb-0">
                        <input class="form-check-input" type="checkbox" id="aiReadOnlyToggle" ${readOnlyChecked}>
                        <label class="form-check-label fs-6 fw-semibold ms-2" for="aiReadOnlyToggle" data-i18n="ai_read_only_label">${t("ai_read_only_label", "Enforce Read-Only Tools")}</label>
                    </div>
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
        </div>

        <!-- Self-Evolving AI Platform & Model Lifecycle Control Panel -->
        <div class="si-modern-card p-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="fw-bold mb-0" style="color:var(--text-primary);">
                    <i class="bi bi-cpu-fill text-primary me-2"></i> <span data-i18n="ai_platform_lifecycle_title">${t("ai_platform_lifecycle_title", "Self-Evolving AI Platform & Model Lifecycle")}</span>
                </h5>
                <button type="button" class="btn btn-sm btn-outline-primary d-flex align-items-center gap-1" onclick="window.AIA.runAutonomousAppScan(this)">
                    <i class="bi bi-radar"></i> <span data-i18n="ai_platform_trigger_scan">${t("ai_platform_trigger_scan", "Trigger Autonomous Scan")}</span>
                </button>
            </div>

            <div class="row g-3">
                <div class="col-md-6">
                    <div class="p-3 rounded" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
                        <h6 class="fw-semibold mb-2" style="color:var(--text-primary);"><i class="bi bi-database-check me-1 text-info"></i> <span data-i18n="ai_platform_dataset_health">${t("ai_platform_dataset_health", "SFT Dataset Health")}</span></h6>
                        <div id="aiPlatformDatasetHealth">
                            <small class="text-muted" data-i18n="ai_platform_loading_dataset_health">${t("ai_platform_loading_dataset_health", "Loading dataset health metrics...")}</small>
                        </div>
                        <button type="button" class="btn btn-sm btn-outline-info mt-2" onclick="window.AIA.refreshDatasetStats(this)" data-i18n="ai_platform_revalidate_dataset">
                            ${t("ai_platform_revalidate_dataset", "Re-validate Dataset")}
                        </button>
                    </div>
                </div>

                <div class="col-md-6">
                    <div class="p-3 rounded" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
                        <h6 class="fw-semibold mb-2" style="color:var(--text-primary);"><i class="bi bi-sliders2 me-1 text-warning"></i> <span data-i18n="ai_platform_training_backend">${t("ai_platform_training_backend", "Training Backend & Fine-Tuning")}</span></h6>
                        <div class="mb-2">
                            <label class="form-label small text-muted mb-1" data-i18n="ai_platform_select_backend_adapter">${t("ai_platform_select_backend_adapter", "Select Training Backend Adapter")}</label>
                            <select id="aiTrainingBackendSelect" class="form-select form-select-sm">
                                <option value="ollama" selected data-i18n="ai_platform_ollama_adapter">${t("ai_platform_ollama_adapter", "Ollama Adapter")}</option>
                                <option value="unsloth" data-i18n="ai_platform_unsloth_adapter">${t("ai_platform_unsloth_adapter", "Unsloth Adapter")}</option>
                                <option value="axolotl" data-i18n="ai_platform_axolotl_adapter">${t("ai_platform_axolotl_adapter", "Axolotl Adapter")}</option>
                                <option value="llamacpp" data-i18n="ai_platform_llamacpp_ecosystem">${t("ai_platform_llamacpp_ecosystem", "llama.cpp Ecosystem")}</option>
                            </select>
                        </div>
                        <button type="button" class="btn btn-sm btn-success w-100" onclick="window.AIA.triggerModelFineTuning(this)">
                            <i class="bi bi-play-circle me-1"></i> <span data-i18n="ai_platform_launch_finetune_pipeline">${t("ai_platform_launch_finetune_pipeline", "Launch Dataset-First Fine-Tuning Pipeline")}</span>
                        </button>
                    </div>
                </div>

                <div class="col-12 mt-3">
                    <h6 class="fw-semibold mb-2" style="color:var(--text-primary);"><i class="bi bi-diagram-3 me-1 text-primary"></i> <span data-i18n="ai_platform_installed_models_history">${t("ai_platform_installed_models_history", "Installed Models & Pre-Promotion Benchmark History")}</span></h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered align-middle text-start" style="border-color:var(--border-color); background:transparent;">
                            <thead>
                                <tr style="background:rgba(255,255,255,0.05);">
                                    <th data-i18n="ai_platform_th_version">${t("ai_platform_th_version", "Version")}</th>
                                    <th data-i18n="ai_platform_th_base_model">${t("ai_platform_th_base_model", "Base Model")}</th>
                                    <th data-i18n="ai_platform_th_backend">${t("ai_platform_th_backend", "Backend")}</th>
                                    <th data-i18n="ai_platform_th_dataset">${t("ai_platform_th_dataset", "Dataset")}</th>
                                    <th data-i18n="ai_platform_th_benchmark_score">${t("ai_platform_th_benchmark_score", "Benchmark Score")}</th>
                                    <th data-i18n="ai_platform_th_status">${t("ai_platform_th_status", "Status")}</th>
                                    <th data-i18n="ai_platform_th_action">${t("ai_platform_th_action", "Action")}</th>
                                </tr>
                            </thead>
                            <tbody id="aiPlatformModelList">
                                <tr><td colspan="7" class="text-muted text-center py-2" data-i18n="ai_platform_loading_models">${t("ai_platform_loading_models", "Loading model versions...")}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>`;

}
