"use strict";
// AI Financial Advisor settings panel logic (Phase 1 Infrastructure)

function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function renderAIAdvisorSettings() {
    const container = document.getElementById('settingsContent');
    if (!container) return;

    // Show loading state
    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>`;

    let providersData, settingsData;
    try {
        const [providersRes, settingsRes] = await Promise.all([
            fetch('/api/settings/ai/providers/'),
            fetch('/api/settings/ai/')
        ]);

        if (!providersRes.ok || !settingsRes.ok) {
            throw new Error('Failed to load AI settings from backend.');
        }

        providersData = await providersRes.json();
        settingsData = await settingsRes.json();

        if (!providersData || !Array.isArray(providersData.providers) || !settingsData) {
            throw new Error('Invalid or malformed settings payload from backend.');
        }
    } catch (err) {
        // Strict adherence to Rule 5: If backend fails, show error state and halt rendering.
        // No hardcoded fallbacks in JS.
        container.innerHTML = `
            <div class="alert alert-danger d-flex align-items-center m-3" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2 fs-4"></i>
                <div>
                    <strong>${t('ai_load_failed_title', 'Unable to load AI Advisor Settings')}</strong><br>
                    ${t('ai_load_failed_desc', 'Could not retrieve configuration from the backend server. Please try refreshing or check server logs.')}
                </div>
            </div>`;
        return;
    }

    const providers = providersData.providers || [];
    const providerOptions = providers.map(p => {
        const selected = p.key === settingsData.ai_provider ? 'selected' : '';
        const label = t(p.label_key, p.key.toUpperCase());
        return `<option value="${p.key}" ${selected}>${label}</option>`;
    }).join('');

    const enabledChecked = settingsData.ai_enabled ? 'checked' : '';

    container.innerHTML = `
        <div class="si-modern-card p-4 mb-4">
            <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                <div>
                    <p class="text-muted small mb-0" data-i18n="ai_settings_desc">${t('ai_settings_desc', 'Configure local AI provider integration, endpoint parameters, and model parameters.')}</p>
                </div>
                <div class="form-check form-switch fs-5">
                    <input class="form-check-input" type="checkbox" id="aiEnabledToggle" ${enabledChecked}>
                    <label class="form-check-label fs-6 fw-semibold ms-2" for="aiEnabledToggle" data-i18n="ai_enabled">${t('ai_enabled', 'Enable AI Advisor')}</label>
                </div>
            </div>

            <!-- Basic & Endpoint Configuration -->
            <div class="row g-3 mb-4">
                <div class="col-md-6">
                    <label class="form-label fw-semibold" data-i18n="ai_provider">${t('ai_provider', 'Provider')}</label>
                    <select id="aiProviderSelect" class="form-select">
                        ${providerOptions}
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-semibold" data-i18n="ai_ollama_url">${t('ai_ollama_url', 'Ollama Base URL')}</label>
                    <input id="aiOllamaUrl" type="url" class="form-control" value="${escapeHtml(settingsData.ai_ollama_url || '')}">
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-semibold" data-i18n="ai_model">${t('ai_model', 'Model Name')}</label>
                    <div class="input-group">
                        <input id="aiModelInput" type="text" class="form-control" value="${escapeHtml(settingsData.ai_model || '')}" placeholder="e.g. llama3.2:latest">
                        <button class="btn btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false" id="aiModelDropdownBtn" data-i18n="ai_select_model">${t('ai_select_model', 'Models')}</button>
                        <ul class="dropdown-menu dropdown-menu-end" id="aiModelDropdownList">
                            <li><span class="dropdown-item text-muted small" data-i18n="ai_test_to_load_models">${t('ai_test_to_load_models', 'Run Test Connection to list models')}</span></li>
                        </ul>
                    </div>
                </div>
                <div class="col-md-2">
                    <label class="form-label fw-semibold" data-i18n="ai_temperature">${t('ai_temperature', 'Temperature')}</label>
                    <input id="aiTemperatureInput" type="number" step="0.05" min="0.0" max="2.0" class="form-control" value="${settingsData.ai_temperature ?? 0.7}">
                </div>
                <div class="col-md-2">
                    <label class="form-label fw-semibold" data-i18n="ai_context_size">${t('ai_context_size', 'Context Size')}</label>
                    <input id="aiContextSizeInput" type="number" step="128" min="256" class="form-control" value="${settingsData.ai_context_size ?? 4096}">
                </div>
                <div class="col-md-2">
                    <label class="form-label fw-semibold" data-i18n="ai_timeout">${t('ai_timeout', 'Timeout (sec)')}</label>
                    <input id="aiTimeoutInput" type="number" step="1" min="1" class="form-control" value="${settingsData.ai_timeout ?? 15}">
                </div>
            </div>

            <!-- Diagnostics Card / Result -->
            <div id="aiTestDiagnosticResult" class="mb-4" style="display: none;"></div>

            <!-- Advanced / Future Parameters Accordion -->
            <div class="accordion mb-4" id="aiAdvancedAccordion">
                <div class="accordion-item" style="border: 1px solid var(--border-color); background: var(--bg-secondary);">
                    <h2 class="accordion-header" id="headingAdvanced">
                        <button class="accordion-button collapsed fw-semibold" type="button" data-bs-toggle="collapse" data-bs-target="#collapseAdvanced" aria-expanded="false" aria-controls="collapseAdvanced" data-i18n="ai_advanced_params">
                            <i class="bi bi-sliders me-2"></i> ${t('ai_advanced_params', 'Advanced Parameters')}
                        </button>
                    </h2>
                    <div id="collapseAdvanced" class="accordion-collapse collapse" aria-labelledby="headingAdvanced" data-bs-parent="#aiAdvancedAccordion">
                        <div class="accordion-body">
                            <div class="mb-3">
                                <label class="form-label fw-semibold" data-i18n="ai_system_prompt">${t('ai_system_prompt', 'System Prompt')}</label>
                                <textarea id="aiSystemPromptInput" class="form-control" rows="3">${escapeHtml(settingsData.ai_system_prompt || '')}</textarea>
                            </div>
                            <div class="row g-3">
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_max_tokens">${t('ai_max_tokens', 'Max Tokens')}</label>
                                    <input id="aiMaxTokensInput" type="number" step="64" min="64" class="form-control" value="${settingsData.ai_max_tokens ?? 2048}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_top_p">${t('ai_top_p', 'Top P')}</label>
                                    <input id="aiTopPInput" type="number" step="0.05" min="0.0" max="1.0" class="form-control" value="${settingsData.ai_top_p ?? 0.9}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_top_k">${t('ai_top_k', 'Top K')}</label>
                                    <input id="aiTopKInput" type="number" step="1" min="1" class="form-control" value="${settingsData.ai_top_k ?? 40}">
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label fw-semibold" data-i18n="ai_repeat_penalty">${t('ai_repeat_penalty', 'Repeat Penalty')}</label>
                                    <input id="aiRepeatPenaltyInput" type="number" step="0.05" min="0.5" class="form-control" value="${settingsData.ai_repeat_penalty ?? 1.1}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold" data-i18n="ai_seed">${t('ai_seed', 'Seed (Optional)')}</label>
                                    <input id="aiSeedInput" type="text" class="form-control" value="${escapeHtml(settingsData.ai_seed || '')}" placeholder="Leave empty for random seed">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label fw-semibold" data-i18n="ai_keep_alive">${t('ai_keep_alive', 'Keep Alive')}</label>
                                    <input id="aiKeepAliveInput" type="text" class="form-control" value="${escapeHtml(settingsData.ai_keep_alive || '5m')}" placeholder="e.g. 5m, 1h, -1">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Action Buttons -->
            <div class="d-flex justify-content-end gap-2">
                <button type="button" class="btn btn-outline-info d-flex align-items-center" id="aiTestConnBtn" onclick="testAIConnectionFromGui()">
                    <i class="bi bi-activity me-1"></i> <span data-i18n="ai_test_connection">${t('ai_test_connection', 'Test Connection')}</span>
                </button>
                <button type="button" class="btn btn-primary-custom d-flex align-items-center" id="aiSaveBtn" onclick="saveAISettingsFromGui()">
                    <i class="bi bi-check-lg me-1"></i> <span data-i18n="ai_save_settings">${t('ai_save_settings', 'Save Settings')}</span>
                </button>
            </div>
        </div>`;

    if (typeof applyTranslations === 'function') {
        applyTranslations();
    }
}

async function testAIConnectionFromGui() {
    const btn = document.getElementById('aiTestConnBtn');
    const resultDiv = document.getElementById('aiTestDiagnosticResult');
    if (!resultDiv) return;

    const provider = document.getElementById('aiProviderSelect')?.value || '';
    const baseUrl = (document.getElementById('aiOllamaUrl')?.value || '').trim();
    const model = (document.getElementById('aiModelInput')?.value || '').trim();
    const timeout = (document.getElementById('aiTimeoutInput')?.value || '').trim();

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> ${t('ai_testing', 'Testing...')}`;
    }

    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `
        <div class="alert alert-info d-flex align-items-center mb-0">
            <span class="spinner-border spinner-border-sm me-2"></span>
            <span>${t('ai_testing_connection_desc', 'Connecting to AI provider and inspecting model availability...')}</span>
        </div>`;

    try {
        const res = await fetch('/api/settings/ai/test-connection/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider: provider,
                base_url: baseUrl,
                model: model,
                timeout: parseInt(timeout, 10) || 15
            })
        });

        const data = await res.json();
        renderAIDiagnosticResult(data);
    } catch (err) {
        resultDiv.innerHTML = `
            <div class="alert alert-danger d-flex align-items-center mb-0">
                <i class="bi bi-x-circle-fill me-2 fs-5"></i>
                <div>
                    <strong>${t('ai_test_failed', 'Test Connection Failed')}</strong><br>
                    ${escapeHtml(err.message || 'Network error')}
                </div>
            </div>`;
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="bi bi-activity me-1"></i> <span>${t('ai_test_connection', 'Test Connection')}</span>`;
        }
    }
}

function renderAIDiagnosticResult(data) {
    const resultDiv = document.getElementById('aiTestDiagnosticResult');
    if (!resultDiv) return;

    const reachable = Boolean(data.reachable);
    const modelAvailable = Boolean(data.model_available);
    const version = data.version || '—';
    const responseTimeMs = data.response_time_ms ?? 0;
    const errorMsg = data.error || '';
    const models = Array.isArray(data.models) ? data.models : [];

    // Populate model dropdown list with retrieved models
    const dropdownList = document.getElementById('aiModelDropdownList');
    if (dropdownList) {
        if (models.length > 0) {
            dropdownList.innerHTML = models.map(m => {
                const name = escapeHtml(m.name || m.model || '');
                const size = m.size ? ` (${(m.size / (1024 * 1024 * 1024)).toFixed(1)} GB)` : '';
                return `<li><a class="dropdown-item" href="#" onclick="selectAIModel('${name}'); return false;">${name}${size}</a></li>`;
            }).join('');
        } else {
            dropdownList.innerHTML = `<li><span class="dropdown-item text-muted small">${t('ai_no_models_found', 'No models found')}</span></li>`;
        }
    }

    const reachBadge = reachable
        ? `<span class="badge bg-success"><i class="bi bi-check-circle-fill me-1"></i> ${t('ai_reachable', 'Reachable')}</span>`
        : `<span class="badge bg-danger"><i class="bi bi-x-circle-fill me-1"></i> ${t('ai_unreachable', 'Unreachable')}</span>`;

    const modelBadge = modelAvailable
        ? `<span class="badge bg-success"><i class="bi bi-check-circle-fill me-1"></i> ${t('ai_model_available', 'Model Available')}</span>`
        : `<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${t('ai_model_not_found', 'Model Not Found')}</span>`;

    const alertClass = (reachable && modelAvailable) ? 'alert-success' : (reachable ? 'alert-warning' : 'alert-danger');

    resultDiv.innerHTML = `
        <div class="alert ${alertClass} mb-0 p-3">
            <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                <div class="fw-bold fs-6">
                    <i class="bi bi-card-checklist me-1"></i> ${t('ai_diagnostic_results', 'Diagnostic Results')}
                </div>
                <div class="d-flex gap-2">
                    ${reachBadge}
                    ${modelBadge}
                </div>
            </div>
            <div class="row g-2 small">
                <div class="col-md-4">
                    <strong>${t('ai_version_label', 'Ollama Version')}:</strong> ${escapeHtml(version)}
                </div>
                <div class="col-md-4">
                    <strong>${t('ai_response_time_label', 'Response Time')}:</strong> ${responseTimeMs} ms
                </div>
                <div class="col-md-4">
                    <strong>${t('ai_models_count_label', 'Available Models')}:</strong> ${models.length}
                </div>
                ${errorMsg ? `<div class="col-12 text-danger mt-1"><strong>${t('error', 'Error')}:</strong> ${escapeHtml(errorMsg)}</div>` : ''}
            </div>
        </div>`;
}

function selectAIModel(modelName) {
    const input = document.getElementById('aiModelInput');
    if (input) {
        input.value = modelName;
        if (typeof showToast === 'function') {
            showToast(t('ai_model_selected', `Model "${modelName}" selected`));
        }
    }
}

async function saveAISettingsFromGui() {
    const btn = document.getElementById('aiSaveBtn');
    const enabled = document.getElementById('aiEnabledToggle')?.checked || false;
    const provider = document.getElementById('aiProviderSelect')?.value || 'ollama';
    const baseUrl = (document.getElementById('aiOllamaUrl')?.value || '').trim();
    const model = (document.getElementById('aiModelInput')?.value || '').trim();
    const temperature = parseFloat(document.getElementById('aiTemperatureInput')?.value || '0.7');
    const contextSize = parseInt(document.getElementById('aiContextSizeInput')?.value || '4096', 10);
    const timeout = parseInt(document.getElementById('aiTimeoutInput')?.value || '15', 10);

    const systemPrompt = (document.getElementById('aiSystemPromptInput')?.value || '').trim();
    const maxTokens = parseInt(document.getElementById('aiMaxTokensInput')?.value || '2048', 10);
    const topP = parseFloat(document.getElementById('aiTopPInput')?.value || '0.9');
    const topK = parseInt(document.getElementById('aiTopKInput')?.value || '40', 10);
    const repeatPenalty = parseFloat(document.getElementById('aiRepeatPenaltyInput')?.value || '1.1');
    const seed = (document.getElementById('aiSeedInput')?.value || '').trim();
    const keepAlive = (document.getElementById('aiKeepAliveInput')?.value || '5m').trim();

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> ${t('saving', 'Saving...')}`;
    }

    try {
        const res = await fetch('/api/settings/ai/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ai_enabled: enabled,
                ai_provider: provider,
                ai_ollama_url: baseUrl,
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
                ai_keep_alive: keepAlive
            })
        });

        const data = await res.json();
        if (!res.ok || !data.ok) {
            throw new Error(data.error || t('settings_save_failed', 'Save failed'));
        }

        // Post-save connection test validation messaging (User requirement #14)
        if (!enabled) {
            showToast(t('settings_saved', 'Settings saved ✓'));
        } else if (data.connection_ok) {
            showToast(t('ai_saved_success', 'Configuration saved successfully ✓'));
        } else {
            showToast(t('ai_saved_conn_failed', 'Configuration saved, but connection test failed ⚠️'), 'warning');
        }
    } catch (err) {
        if (typeof showToast === 'function') {
            showToast(err.message || t('settings_save_failed', 'Save failed'), 'error');
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="bi bi-check-lg me-1"></i> <span>${t('ai_save_settings', 'Save Settings')}</span>`;
        }
    }
}
