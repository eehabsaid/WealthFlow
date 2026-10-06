"use strict";
window.AIA = window.AIA || {};
// AI Advisor settings: "Self-Evolving AI Platform & Model Lifecycle" card markup (split from render_settings_form.js).

window.AIA.buildPlatformCardHtml = function () {
  return `
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
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
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
};
