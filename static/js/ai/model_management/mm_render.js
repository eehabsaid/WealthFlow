/**
 * WealthFlow AI Workspace - Model Management: Rendering
 * Modal shell HTML and dynamic body rendering.
 */

"use strict";

window.MM = window.MM || {};

window.MM.renderModalShell = function () {
  const t = window.MM.t;
  const esc = window.MM.escapeHtml;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div class="d-flex align-items-center gap-2">
        <div class="rounded-circle bg-primary bg-opacity-10 p-2 d-flex align-items-center justify-content-center" style="width:38px;height:38px;">
          <i class="bi bi-sliders fs-5 text-primary"></i>
        </div>
        <div>
          <h5 class="modal-title fw-bold mb-0 text-body">${esc(t("ai_mm_title", "Model Management"))}</h5>
          <small class="text-muted">${esc(t("ai_mm_subtitle", "Lifecycle & Fine-Tuning"))}</small>
        </div>
      </div>
      <button type="button" class="btn-close text-reset ms-auto" onclick="closeModal()" aria-label="Close"></button>
    </div>
    <div class="modal-body p-0" id="mm-modal-body" style="min-height: 420px;"></div>
  `;
};

window.MM.renderBody = function () {
  const body = document.getElementById("mm-modal-body");
  if (!body) return;
  const t = window.MM.t;
  const esc = window.MM.escapeHtml;
  const state = window.MM.state;

  if (state.loading || state.busy) {
    body.innerHTML = `<div class="text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>${esc(t("ai_platform_loading_models", "Loading model versions..."))}</div>`;
    return;
  }

  if (state.error) {
    body.innerHTML = `<div class="alert alert-danger m-4">${esc(state.error)}</div>`;
    return;
  }

  const active = state.activeModel;
  const activeBlock = active
    ? `
    <div class="border rounded p-3 mb-4 bg-success bg-opacity-10">
      <div class="small text-muted mb-1">${esc(t("ai_mm_active_label", "Active Production Model"))}</div>
      <div class="fw-bold text-body">${esc(active.version_name)}</div>
      <div class="small text-muted">${esc(active.base_model)} &middot; ${esc(active.training_backend)} &middot; Score: ${esc(active.benchmark_score)}</div>
    </div>`
    : "";

  const backends = state.availableBackends;
  const backendOpts = backends.length
    ? backends
        .map(function (b) {
          return `<option value="${esc(b)}">${esc(b)}</option>`;
        })
        .join("")
    : '<option value="ollama">ollama</option>';

  const rows =
    state.modelVersions.length === 0
      ? `<tr><td colspan="5" class="text-center text-muted py-4">${esc(t("ai_platform_no_models", "No custom model versions found."))}</td></tr>`
      : state.modelVersions
          .map(function (m) {
            const isActive = m.is_active;
            return `<tr>
          <td class="small">${esc(m.version_name)}</td>
          <td class="small">${esc(m.base_model)}</td>
          <td class="small">${esc(m.training_backend)}</td>
          <td class="small">${esc(m.benchmark_score)}</td>
          <td>
            ${
              isActive
                ? `<span class="badge bg-success">${esc(t("ai_platform_btn_active", "Active"))}</span>`
                : `<button class="btn btn-xs btn-outline-primary btn-sm py-0 px-2" onclick="window.MM.promote('${esc(m.version_name)}')">${esc(t("ai_platform_btn_promote", "Promote"))}</button>`
            }
          </td>
        </tr>`;
          })
          .join("");

  body.innerHTML = `
    <div class="p-4">
      ${activeBlock}
      <h6 class="fw-semibold mb-3 text-body">${esc(t("ai_platform_training_backend", "Training Backend & Fine-Tuning"))}</h6>
      <div class="d-flex gap-2 align-items-end mb-4">
        <div class="flex-grow-1">
          <label class="form-label small mb-1">${esc(t("ai_platform_th_base_model", "Base Model"))}</label>
          <input id="mm-base-model" type="text" class="form-control form-control-sm" value="llama3:latest" placeholder="e.g. llama3:latest">
        </div>
        <div style="min-width:160px;">
          <label class="form-label small mb-1">${esc(t("ai_platform_select_backend_adapter", "Backend"))}</label>
          <select id="mm-backend" class="form-select form-select-sm">${backendOpts}</select>
        </div>
        <button class="btn btn-sm btn-primary d-inline-flex align-items-center gap-1" onclick="window.MM.fineTune()">
          <i class="bi bi-play-fill"></i> ${esc(t("ai_mm_finetune_btn", "Launch Fine-Tuning"))}
        </button>
      </div>
      <h6 class="fw-semibold mb-2 text-body">${esc(t("ai_platform_installed_models_history", "Installed Models"))}</h6>
      <div class="table-responsive">
        <table class="table table-sm table-hover mb-0">
          <thead class="table-light">
            <tr>
              <th>${esc(t("ai_platform_th_version", "Version"))}</th>
              <th>${esc(t("ai_platform_th_base_model", "Base Model"))}</th>
              <th>${esc(t("ai_platform_th_backend", "Backend"))}</th>
              <th>${esc(t("ai_platform_th_benchmark_score", "Score"))}</th>
              <th>${esc(t("ai_platform_th_action", "Action"))}</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
  if (window.applyTranslations) window.applyTranslations();
};
