"use strict";
// AI Financial Advisor settings panel logic (Phase 4 Multi-Provider & Security Hardening)

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

let currentAISettings = null;
let currentProviderSchemas = [];

async function renderAIAdvisorSettings() {
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

    currentAISettings = await res.json();
    currentProviderSchemas = Array.isArray(currentAISettings.providers_schema)
      ? currentAISettings.providers_schema
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

  const activeProviderKey = currentAISettings.ai_provider || "ollama";
  const providerOptions = currentProviderSchemas
    .map((p) => {
      const selected = p.key === activeProviderKey ? "selected" : "";
      const label = t(p.label_key, p.key.toUpperCase());
      return `<option value="${p.key}" ${selected}>${label}</option>`;
    })
    .join("");

  const enabledChecked = currentAISettings.ai_enabled ? "checked" : "";
  const readOnlyChecked = (currentAISettings.ai_read_only ?? true) ? "checked" : "";

  container.innerHTML = `
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
                    <select id="aiProviderSelect" class="form-select" onchange="onAIProviderChanged()">
                        ${providerOptions}
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-semibold" data-i18n="ai_model">${t("ai_model", "Model Name / Deployment")}</label>
                    <div class="input-group">
                        <input id="aiModelInput" type="text" class="form-control" value="${escapeHtml(getProviderModelValue(activeProviderKey))}" placeholder="e.g. llama3.2:latest, gpt-4o">
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
                    <input id="aiTemperatureInput" type="number" step="0.05" min="0.0" max="2.0" class="form-control" value="${currentAISettings.ai_temperature ?? 0.7}">
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-semibold" data-i18n="ai_context_size">${t("ai_context_size", "Context Size")}</label>
                    <input id="aiContextSizeInput" type="number" step="128" min="256" class="form-control" value="${currentAISettings.ai_context_size ?? 4096}">
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-semibold" data-i18n="ai_timeout">${t("ai_timeout", "Timeout (sec)")}</label>
                    <input id="aiTimeoutInput" type="number" step="1" min="1" class="form-control" value="${currentAISettings.ai_timeout ?? 60}">
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
                                <textarea id="aiSystemPromptInput" class="form-control" rows="3">${escapeHtml(currentAISettings.ai_system_prompt || "")}</textarea>
                            </div>
                            <div class="row g-3">
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_max_tokens">${t("ai_max_tokens", "Max Tokens")}</label>
                                    <input id="aiMaxTokensInput" type="number" step="64" min="64" class="form-control" value="${currentAISettings.ai_max_tokens ?? 2048}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_top_p">${t("ai_top_p", "Top P")}</label>
                                    <input id="aiTopPInput" type="number" step="0.05" min="0.0" max="1.0" class="form-control" value="${currentAISettings.ai_top_p ?? 0.9}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_top_k">${t("ai_top_k", "Top K")}</label>
                                    <input id="aiTopKInput" type="number" step="1" min="1" class="form-control" value="${currentAISettings.ai_top_k ?? 40}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_repeat_penalty">${t("ai_repeat_penalty", "Repeat Penalty")}</label>
                                    <input id="aiRepeatPenaltyInput" type="number" step="0.05" min="0.5" class="form-control" value="${currentAISettings.ai_repeat_penalty ?? 1.1}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold" data-i18n="ai_seed">${t("ai_seed", "Seed (Optional)")}</label>
                                    <input id="aiSeedInput" type="text" class="form-control" value="${escapeHtml(currentAISettings.ai_seed || "")}" placeholder="Leave empty for random seed">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold" data-i18n="ai_keep_alive">${t("ai_keep_alive", "Keep Alive")}</label>
                                    <input id="aiKeepAliveInput" type="text" class="form-control" value="${escapeHtml(currentAISettings.ai_keep_alive || "5m")}" placeholder="e.g. 5m, 1h, -1">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Action Buttons -->
            <div class="d-flex justify-content-end gap-2">
                <button type="button" class="btn btn-outline-info d-flex align-items-center" id="aiTestConnBtn" onclick="testAIConnectionFromGui()">
                    <i class="bi bi-activity me-1"></i> <span data-i18n="ai_test_connection">${t("ai_test_connection", "Test Connection")}</span>
                </button>
                <button type="button" class="btn btn-primary-custom d-flex align-items-center" id="aiSaveBtn" onclick="saveAISettingsFromGui()">
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
                <button type="button" class="btn btn-sm btn-outline-primary d-flex align-items-center gap-1" onclick="runAutonomousAppScan(this)">
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
                        <button type="button" class="btn btn-sm btn-outline-info mt-2" onclick="refreshDatasetStats(this)" data-i18n="ai_platform_revalidate_dataset">
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
                        <button type="button" class="btn btn-sm btn-success w-100" onclick="triggerModelFineTuning(this)">
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

  loadAIPlatformOverviewData();

  renderProviderFields(activeProviderKey);

  if (typeof applyTranslations === "function") {
    applyTranslations();
  }
}

function getProviderModelValue(providerKey) {
  if (!currentAISettings) return "";
  if (providerKey === "ollama") return currentAISettings.ai_model || "";
  if (providerKey === "openai") return currentAISettings.ai_openai_model || "";
  if (providerKey === "claude") return currentAISettings.ai_claude_model || "";
  if (providerKey === "gemini") return currentAISettings.ai_gemini_model || "";
  if (providerKey === "azure") return currentAISettings.ai_azure_deployment || "";
  return currentAISettings.ai_model || "";
}

function onAIProviderChanged() {
  const pKey = document.getElementById("aiProviderSelect")?.value || "ollama";
  renderProviderFields(pKey);
  const mInput = document.getElementById("aiModelInput");
  if (mInput) {
    mInput.value = getProviderModelValue(pKey);
  }
}

function renderProviderFields(providerKey) {
  const container = document.getElementById("providerSpecificFields");
  if (!container) return;

  const schema = currentProviderSchemas.find((s) => s.key === providerKey);
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
      const val = currentAISettings ? (currentAISettings[f.name] ?? "") : "";
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

async function testAIConnectionFromGui() {
  const btn = document.getElementById("aiTestConnBtn");
  const resultDiv = document.getElementById("aiTestDiagnosticResult");
  if (!resultDiv) return;

  const provider = document.getElementById("aiProviderSelect")?.value || "ollama";
  const model = (document.getElementById("aiModelInput")?.value || "").trim();
  const timeout = (document.getElementById("aiTimeoutInput")?.value || "").trim();

  const payload = {
    provider: provider,
    model: model,
    timeout: parseInt(timeout, 10) || 60,
  };

  // Include provider specific fields
  const schema = currentProviderSchemas.find((s) => s.key === provider);
  if (schema && Array.isArray(schema.fields)) {
    schema.fields.forEach((f) => {
      const el = document.getElementById(f.name);
      if (el) payload[f.name] = el.value.trim();
    });
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> ${t("ai_testing", "Testing...")}`;
  }

  resultDiv.style.display = "block";
  resultDiv.innerHTML = `
        <div class="alert alert-info d-flex align-items-center mb-0">
            <span class="spinner-border spinner-border-sm me-2"></span>
            <span>${t("ai_testing_connection_desc", "Connecting to AI provider and inspecting model availability...")}</span>
        </div>`;

  try {
    const res = await fetch("/api/settings/ai/test-connection/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    renderAIDiagnosticResult(data);
  } catch (err) {
    resultDiv.innerHTML = `
            <div class="alert alert-danger d-flex align-items-center mb-0">
                <i class="bi bi-x-circle-fill me-2 fs-5"></i>
                <div>
                    <strong>${t("ai_test_failed", "Test Connection Failed")}</strong><br>
                    ${escapeHtml(err.message || "Network error")}
                </div>
            </div>`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-activity me-1"></i> <span>${t("ai_test_connection", "Test Connection")}</span>`;
    }
  }
}

function renderAIDiagnosticResult(data) {
  const resultDiv = document.getElementById("aiTestDiagnosticResult");
  if (!resultDiv) return;

  const reachable = Boolean(data.reachable);
  const modelAvailable = Boolean(data.model_available);
  const version = data.version || "—";
  const responseTimeMs = data.response_time_ms ?? 0;
  const errorMsg = data.error || "";
  const models = Array.isArray(data.models) ? data.models : [];

  // Populate model dropdown list with retrieved models
  const dropdownList = document.getElementById("aiModelDropdownList");
  if (dropdownList) {
    if (models.length > 0) {
      dropdownList.innerHTML = models
        .map((m) => {
          const name = escapeHtml(m.name || m.model || "");
          const size = m.size ? ` (${(m.size / (1024 * 1024 * 1024)).toFixed(1)} GB)` : "";
          return `<li><a class="dropdown-item" href="#" onclick="selectAIModel('${name}'); return false;">${name}${size}</a></li>`;
        })
        .join("");
    } else {
      dropdownList.innerHTML = `<li><span class="dropdown-item text-muted small">${t("ai_no_models_found", "No models found")}</span></li>`;
    }
  }

  const reachBadge = reachable
    ? `<span class="badge bg-success"><i class="bi bi-check-circle-fill me-1"></i> ${t("ai_reachable", "Reachable")}</span>`
    : `<span class="badge bg-danger"><i class="bi bi-x-circle-fill me-1"></i> ${t("ai_unreachable", "Unreachable")}</span>`;

  const modelBadge = modelAvailable
    ? `<span class="badge bg-success"><i class="bi bi-check-circle-fill me-1"></i> ${t("ai_model_available", "Model Available")}</span>`
    : `<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${t("ai_model_not_found", "Model Not Found")}</span>`;

  const alertClass =
    reachable && modelAvailable ? "alert-success" : reachable ? "alert-warning" : "alert-danger";

  resultDiv.innerHTML = `
        <div class="alert ${alertClass} mb-0 p-3">
            <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                <div class="fw-bold fs-6">
                    <i class="bi bi-card-checklist me-1"></i> ${t("ai_diagnostic_results", "Diagnostic Results")}
                </div>
                <div class="d-flex gap-2">
                    ${reachBadge}
                    ${modelBadge}
                </div>
            </div>
            <div class="row g-2 small">
                <div class="col-md-4">
                    <strong>${t("ai_version_label", "Version")}:</strong> ${escapeHtml(version)}
                </div>
                <div class="col-md-4">
                    <strong>${t("ai_response_time_label", "Response Time")}:</strong> ${responseTimeMs} ms
                </div>
                <div class="col-md-4">
                    <strong>${t("ai_models_count_label", "Available Models")}:</strong> ${models.length}
                </div>
                ${errorMsg ? `<div class="col-12 text-danger mt-1"><strong>${t("error", "Error")}:</strong> ${escapeHtml(errorMsg)}</div>` : ""}
            </div>
        </div>`;
}

function selectAIModel(modelName) {
  const input = document.getElementById("aiModelInput");
  if (input) {
    input.value = modelName;
    if (typeof showToast === "function") {
      showToast(t("ai_model_selected", `Model "${modelName}" selected`));
    }
  }
}

async function saveAISettingsFromGui() {
  const btn = document.getElementById("aiSaveBtn");
  const enabled = document.getElementById("aiEnabledToggle")?.checked || false;
  const readOnly = document.getElementById("aiReadOnlyToggle")?.checked ?? true;
  const provider = document.getElementById("aiProviderSelect")?.value || "ollama";
  const model = (document.getElementById("aiModelInput")?.value || "").trim();
  const temperature = parseFloat(document.getElementById("aiTemperatureInput")?.value || "0.7");
  const contextSize = parseInt(document.getElementById("aiContextSizeInput")?.value || "4096", 10);
  const timeout = parseInt(document.getElementById("aiTimeoutInput")?.value || "60", 10);

  const systemPrompt = (document.getElementById("aiSystemPromptInput")?.value || "").trim();
  const maxTokens = parseInt(document.getElementById("aiMaxTokensInput")?.value || "2048", 10);
  const topP = parseFloat(document.getElementById("aiTopPInput")?.value || "0.9");
  const topK = parseInt(document.getElementById("aiTopKInput")?.value || "40", 10);
  const repeatPenalty = parseFloat(document.getElementById("aiRepeatPenaltyInput")?.value || "1.1");
  const seed = (document.getElementById("aiSeedInput")?.value || "").trim();
  const keepAlive = (document.getElementById("aiKeepAliveInput")?.value || "5m").trim();

  const payload = {
    ai_enabled: enabled,
    ai_read_only: readOnly,
    ai_provider: provider,
    ai_model: model,
    ai_temperature: temperature,
    ai_context_size: contextSize,
    ai_timeout: timeout,
    ai_system_prompt: systemPrompt,
    ai_max_tokens: maxTokens,
    ai_top_p: topP,
    ai_top_k: topK,
    ai_repeat_penalty: repeatPenalty,
    ai_seed: seed,
    ai_keep_alive: keepAlive,
  };

  // Save provider specific models
  if (provider === "ollama") payload.ai_model = model;
  if (provider === "openai") payload.ai_openai_model = model;
  if (provider === "claude") payload.ai_claude_model = model;
  if (provider === "gemini") payload.ai_gemini_model = model;
  if (provider === "azure") payload.ai_azure_deployment = model;

  // Collect all provider specific inputs
  currentProviderSchemas.forEach((schema) => {
    if (Array.isArray(schema.fields)) {
      schema.fields.forEach((f) => {
        const el = document.getElementById(f.name);
        if (el) {
          payload[f.name] = el.value.trim();
        }
      });
    }
  });

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> ${t("saving", "Saving...")}`;
  }

  try {
    const res = await fetch("/api/settings/ai/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.error || t("settings_save_failed", "Save failed"));
    }

    if (!enabled) {
      showToast(t("settings_saved", "Settings saved ✓"));
    } else if (data.connection_ok) {
      showToast(t("ai_saved_success", "Configuration saved successfully ✓"));
    } else {
      showToast(
        t("ai_saved_conn_failed", "Configuration saved, but connection test failed ⚠️"),
        "warning"
      );
    }
    await renderAIAdvisorSettings();
  } catch (err) {
    if (typeof showToast === "function") {
      showToast(err.message || t("settings_save_failed", "Save failed"), "error");
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-check-lg me-1"></i> <span>${t("ai_save_settings", "Save Settings")}</span>`;
    }
  }
}

async function loadAIPlatformOverviewData() {
  try {
    const [dsRes, mRes] = await Promise.all([
      fetch("/api/ai-platform/datasets/"),
      fetch("/api/ai-platform/models/"),
    ]);

    if (dsRes.ok) {
      const dsData = await dsRes.json();
      const stats = dsData.dataset_stats || {};
      const container = document.getElementById("aiPlatformDatasetHealth");
      if (container) {
        container.innerHTML = `
                    <div class="small">
                        <div><strong data-i18n="ai_platform_total_sft_samples">${t("ai_platform_total_sft_samples", "Total SFT Samples:")}</strong> ${stats.total_samples || 0}</div>
                        <div><strong data-i18n="ai_platform_duplicates_removed">${t("ai_platform_duplicates_removed", "Duplicates Removed:")}</strong> ${stats.duplicates_removed || 0}</div>
                        <div><strong data-i18n="ai_platform_validation_status">${t("ai_platform_validation_status", "Validation Status:")}</strong> <span class="badge bg-success">${stats.validation_status || "Clean"}</span></div>
                    </div>
                `;
      }
    }

    if (mRes.ok) {
      const mData = await mRes.json();
      const versions = mData.model_versions || [];
      const tbody = document.getElementById("aiPlatformModelList");
      if (tbody) {
        if (versions.length === 0) {
          tbody.innerHTML = `<tr><td colspan="7" class="text-muted text-center py-2" data-i18n="ai_platform_no_models">${t("ai_platform_no_models", "No custom model versions found.")}</td></tr>`;
        } else {
          let html = "";
          versions.forEach((v) => {
            const activeBadge = v.is_active
              ? `<span class="badge bg-primary" data-i18n="ai_platform_active_production">${t("ai_platform_active_production", "Active Production")}</span>`
              : `<span class="badge bg-secondary" data-i18n="ai_platform_archived">${t("ai_platform_archived", "Archived")}</span>`;
            const actionBtn = v.is_active
              ? `<button class="btn btn-sm btn-outline-secondary" disabled data-i18n="ai_platform_btn_active">${t("ai_platform_btn_active", "Active")}</button>`
              : `<button class="btn btn-sm btn-outline-success" onclick="promoteModelVersion('${v.version_name}')" data-i18n="ai_platform_btn_promote">${t("ai_platform_btn_promote", "Promote")}</button>`;
            html += `
                            <tr>
                                <td class="fw-bold">${v.version_name}</td>
                                <td>${v.base_model}</td>
                                <td>${v.training_backend}</td>
                                <td>${v.dataset_version}</td>
                                <td><span class="badge bg-info text-dark">${v.benchmark_score} / 100</span></td>
                                <td>${activeBadge}</td>
                                <td>${actionBtn}</td>
                            </tr>
                        `;
          });
          tbody.innerHTML = html;
        }
      }
    }

    if (typeof applyTranslations === "function") {
      applyTranslations();
    }
  } catch (err) {
    console.error("Failed to load AI Platform overview:", err);
  }
}

async function runAutonomousAppScan(btn) {
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/ai-platform/knowledge/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "scan" }),
    });
    const data = await res.json();
    if (data.ok) {
      if (typeof showToast === "function")
        showToast(`Autonomous scan complete ✓ (${data.updated_entries_count} entries updated)`);
      loadAIPlatformOverviewData();
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Autonomous scan failed", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function refreshDatasetStats(btn) {
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/ai-platform/datasets/", { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      if (typeof showToast === "function") showToast("Dataset re-generated & validated ✓");
      loadAIPlatformOverviewData();
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Dataset validation failed", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function triggerModelFineTuning(btn) {
  const backend = document.getElementById("aiTrainingBackendSelect")?.value || "ollama";
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/ai-platform/models/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "fine_tune", backend_name: backend }),
    });
    const data = await res.json();
    if (data.ok) {
      const promotedText = data.promoted_to_active
        ? "Candidate promoted to Production ✓"
        : "Benchmark score did not exceed production ⚠️";
      if (typeof showToast === "function") showToast(`Fine-tuning finished. ${promotedText}`);
      loadAIPlatformOverviewData();
    } else {
      if (typeof showToast === "function") showToast(data.error || "Fine-tuning failed", "error");
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Fine-tuning request failed", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function promoteModelVersion(versionName) {
  try {
    const res = await fetch("/api/ai-platform/models/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "promote", version_name: versionName }),
    });
    const data = await res.json();
    if (data.ok) {
      if (typeof showToast === "function")
        showToast(`Promoted ${versionName} to active production ✓`);
      loadAIPlatformOverviewData();
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Promotion failed", "error");
  }
}
