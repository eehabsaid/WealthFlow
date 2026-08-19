/**
 * WealthFlow AI Workspace - Dataset Manager: Rendering
 * Modal shell HTML and dynamic body rendering.
 */

'use strict';

window.DM = window.DM || {};

window.DM.renderModalShell = function () {
  const t = window.DM.t;
  const esc = window.DM.escapeHtml;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div class="d-flex align-items-center gap-2">
        <div class="rounded-circle bg-primary bg-opacity-10 p-2 d-flex align-items-center justify-content-center" style="width:38px;height:38px;">
          <i class="bi bi-server fs-5 text-primary"></i>
        </div>
        <div>
          <h5 class="modal-title fw-bold mb-0 text-body">${esc(t('ai_dm_title', 'Dataset Manager'))}</h5>
          <small class="text-muted">${esc(t('ai_dm_subtitle', 'SFT Dataset Health & Generation'))}</small>
        </div>
      </div>
      <div class="d-flex align-items-center gap-2 ms-auto">
        <button type="button" class="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1" onclick="window.DM.loadStats()">
          <i class="bi bi-arrow-clockwise"></i> <span>${esc(t('ai_platform_revalidate_dataset', 'Re-validate Dataset'))}</span>
        </button>
        <button type="button" class="btn btn-sm btn-primary d-inline-flex align-items-center gap-1" onclick="window.DM.generateDataset()">
          <i class="bi bi-play-fill"></i> <span>${esc(t('ai_dm_generate_btn', 'Generate SFT Dataset'))}</span>
        </button>
        <button type="button" class="btn-close text-reset ms-2" onclick="closeModal()" aria-label="Close"></button>
      </div>
    </div>
    <div class="modal-body p-0" id="dm-modal-body" style="min-height: 340px;"></div>
  `;
};

window.DM.renderBody = function () {
  const body = document.getElementById('dm-modal-body');
  if (!body) return;
  const t = window.DM.t;
  const esc = window.DM.escapeHtml;
  const state = window.DM.state;

  if (state.loading || state.generating) {
    const msg = state.generating
      ? t('ai_platform_launch_finetune_pipeline', 'Generating...')
      : t('ai_platform_loading_dataset_health', 'Loading dataset health metrics...');
    body.innerHTML = `<div class="text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>${esc(msg)}</div>`;
    return;
  }

  if (state.error) {
    body.innerHTML = `<div class="alert alert-danger m-4">${esc(state.error)}</div>`;
    return;
  }

  const s = state.stats;
  if (!s || s.ok === false) {
    body.innerHTML = `<div class="text-center text-muted py-5">${esc(t('ai_dm_no_data', 'No dataset found. Generate one first.'))}</div>`;
    return;
  }

  const cats = s.category_breakdown || {};
  const catRows = Object.entries(cats).map(function ([cat, count]) {
    return `<div class="d-flex justify-content-between px-4 py-2 border-bottom border-secondary-subtle small">
      <span class="text-muted">${esc(cat)}</span>
      <span class="fw-semibold">${esc(count)}</span>
    </div>`;
  }).join('');

  body.innerHTML = `
    <div class="p-4">
      <h6 class="fw-semibold mb-3 text-body">${esc(t('ai_platform_dataset_health', 'SFT Dataset Health'))}</h6>
      <div class="row g-3 mb-4">
        <div class="col-sm-4">
          <div class="border rounded p-3 text-center">
            <div class="fs-4 fw-bold text-primary">${esc(s.total_samples)}</div>
            <div class="small text-muted">${esc(t('ai_platform_total_sft_samples', 'Total SFT Samples'))}</div>
          </div>
        </div>
        <div class="col-sm-4">
          <div class="border rounded p-3 text-center">
            <div class="fs-4 fw-bold text-warning">${esc(s.duplicates_removed)}</div>
            <div class="small text-muted">${esc(t('ai_platform_duplicates_removed', 'Duplicates Removed'))}</div>
          </div>
        </div>
        <div class="col-sm-4">
          <div class="border rounded p-3 text-center">
            <div class="fs-6 fw-bold text-success">${esc(s.validation_status)}</div>
            <div class="small text-muted">${esc(t('ai_platform_validation_status', 'Validation Status'))}</div>
          </div>
        </div>
      </div>
      ${catRows ? `<h6 class="fw-semibold mb-2 text-body">${esc(t('ai_dm_categories', 'Category Breakdown'))}</h6>
      <div class="border rounded overflow-hidden">${catRows}</div>` : ''}
    </div>
  `;
  if (window.applyTranslations) window.applyTranslations();
};
