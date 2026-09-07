"use strict";
// AI Advisor settings: Diagnostic result rendering + model picker.

window.AIA = window.AIA || {};

window.AIA.renderAIDiagnosticResult = function(data) {
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
          return `<li><a class="dropdown-item" href="#" onclick="window.AIA.selectAIModel('${name}'); return false;">${name}${size}</a></li>`;
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

window.AIA.selectAIModel = function(modelName) {
  const input = document.getElementById("aiModelInput");
  if (input) {
    input.value = modelName;
    if (typeof showToast === "function") {
      showToast(t("ai_model_selected", `Model "${modelName}" selected`));
    }
  }
}

