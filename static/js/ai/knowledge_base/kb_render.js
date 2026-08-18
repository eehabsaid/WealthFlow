/**
 * WealthFlow AI Workspace - Knowledge Base: Rendering
 * Modal shell HTML and dynamic body rendering (category tabs, entry form, entry list).
 */

'use strict';

window.KB = window.KB || {};

window.KB.renderModalShell = function () {
  const t = window.KB.t;
  const esc = window.KB.escapeHtml;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div class="d-flex align-items-center gap-2">
        <div class="rounded-circle bg-primary bg-opacity-10 p-2 d-flex align-items-center justify-content-center" style="width:38px;height:38px;">
          <i class="bi bi-journal-text fs-5 text-primary"></i>
        </div>
        <div>
          <h5 class="modal-title fw-bold mb-0 text-body" data-i18n="ai_kb_title">${esc(t('ai_kb_title', 'Knowledge Base'))}</h5>
          <small class="text-muted" data-i18n="ai_kb_subtitle">${esc(t('ai_kb_subtitle', 'Distilled long-term knowledge WealthFlow AI uses for context'))}</small>
        </div>
      </div>
      <div class="d-flex align-items-center gap-2 ms-auto">
        <button type="button" class="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1" id="kb-scan-btn" onclick="window.KB.triggerScan()">
          <i class="bi bi-radar"></i> <span data-i18n="ai_kb_scan_btn">${esc(t('ai_kb_scan_btn', 'Run Autonomous Scan'))}</span>
        </button>
        <button type="button" class="btn btn-sm btn-primary d-inline-flex align-items-center gap-1" onclick="window.KB.newForm()">
          <i class="bi bi-plus-lg"></i> <span data-i18n="ai_kb_new_btn">${esc(t('ai_kb_new_btn', 'New Entry'))}</span>
        </button>
        <button type="button" class="btn-close text-reset ms-2" onclick="closeModal()" aria-label="Close"></button>
      </div>
    </div>
    <div class="modal-body p-0" id="kb-modal-body" style="min-height: 480px;">
      <!-- Rendered via JS -->
    </div>
  `;
};

window.KB.categoryBadge = function (category) {
  const t = window.KB.t;
  const esc = window.KB.escapeHtml;
  const found = window.KB.CATEGORIES.find((c) => c.code === category);
  const label = found ? t(found.i18n, found.fallback) : category;
  return `<span class="badge bg-secondary-subtle text-secondary-emphasis border">${esc(label)}</span>`;
};

window.KB.renderTabs = function () {
  const state = window.KB.state;
  return window.KB.CATEGORIES.map((c) => `
    <button type="button" class="btn btn-sm ${state.activeCategory === c.code ? 'btn-primary' : 'btn-outline-secondary'}" onclick="window.KB.categoryChange('${c.code}')">
      ${window.KB.escapeHtml(window.KB.t(c.i18n, c.fallback))}
    </button>
  `).join('');
};

window.KB.renderScanResult = function () {
  const t = window.KB.t;
  const esc = window.KB.escapeHtml;
  const result = window.KB.state.scanResult;
  if (!result) return '';
  if (result.error || result.ok === false) {
    return `<div class="alert alert-danger py-2 px-3 mb-3 small" data-i18n="ai_kb_scan_error">${esc(t('ai_kb_scan_error', 'Scan failed. Please try again.'))}</div>`;
  }
  const learned = result.updated_entries_count ?? 0;
  const suffix = learned ? ` (${learned} ${esc(t('ai_kb_scan_new_entries', 'new/updated entries'))})` : '';
  return `<div class="alert alert-success py-2 px-3 mb-3 small">${esc(t('ai_kb_scan_success', 'Scan complete.'))}${suffix}</div>`;
};

window.KB.renderForm = function () {
  const t = window.KB.t;
  const esc = window.KB.escapeHtml;
  if (!window.KB.state.isFormOpen) return '';
  const errorHtml = window.KB.formError
    ? `<div class="alert alert-danger py-2 px-3 mb-2 small">${esc(window.KB.formError)}</div>`
    : '';
  const options = window.KB.CATEGORIES.filter((c) => c.code !== 'all')
    .map((c) => `<option value="${c.code}">${esc(t(c.i18n, c.fallback))}</option>`).join('');
  return `
    <form class="p-4 border-bottom border-secondary-subtle" onsubmit="window.KB.submitForm(event)">
      ${errorHtml}
      <div class="row g-2 mb-2">
        <div class="col-md-6">
          <label class="form-label small mb-1" data-i18n="ai_kb_field_key">${esc(t('ai_kb_field_key', 'Key (unique)'))}</label>
          <input type="text" name="key" class="form-control form-control-sm" required maxlength="255">
        </div>
        <div class="col-md-6">
          <label class="form-label small mb-1" data-i18n="ai_kb_field_category">${esc(t('ai_kb_field_category', 'Category'))}</label>
          <select name="category" class="form-select form-select-sm">${options}</select>
        </div>
      </div>
      <div class="mb-2">
        <label class="form-label small mb-1" data-i18n="ai_kb_field_title">${esc(t('ai_kb_field_title', 'Title'))}</label>
        <input type="text" name="title" class="form-control form-control-sm" required maxlength="255">
      </div>
      <div class="mb-3">
        <label class="form-label small mb-1" data-i18n="ai_kb_field_content">${esc(t('ai_kb_field_content', 'Content'))}</label>
        <textarea name="content" class="form-control form-control-sm" rows="3" required></textarea>
      </div>
      <div class="d-flex gap-2">
        <button type="submit" class="btn btn-sm btn-primary" data-i18n="ai_kb_save_btn">${esc(t('ai_kb_save_btn', 'Save Entry'))}</button>
        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window.KB.cancelForm()" data-i18n="ai_kb_cancel_btn">${esc(t('ai_kb_cancel_btn', 'Cancel'))}</button>
      </div>
    </form>
  `;
};

window.KB.renderList = function () {
  const t = window.KB.t;
  const esc = window.KB.escapeHtml;
  const state = window.KB.state;
  if (state.loading) {
    return `<div class="text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>${esc(t('ai_kb_loading', 'Loading knowledge entries...'))}</div>`;
  }
  if (state.entries.length === 0) {
    return `<div class="text-center text-muted py-5" data-i18n="ai_kb_empty">${esc(t('ai_kb_empty', 'No knowledge entries yet. Run a scan or add one manually.'))}</div>`;
  }
  const rows = state.entries.map((e) => `
    <div class="list-group-item px-4 py-3">
      <div class="d-flex justify-content-between align-items-start gap-2 mb-1">
        <div class="fw-semibold text-body">${esc(e.title)}</div>
        ${window.KB.categoryBadge(e.category)}
      </div>
      <div class="small text-muted mb-2">${esc(e.content)}</div>
      <div class="d-flex gap-3 small text-muted">
        <span><i class="bi bi-key me-1"></i>${esc(e.key)}</span>
        <span><i class="bi bi-shield-check me-1"></i>${Math.round((e.confidence || 0) * 100)}%</span>
        <span><i class="bi bi-diagram-3 me-1"></i>${esc(e.source)}</span>
      </div>
    </div>
  `).join('');
  return `<div class="list-group list-group-flush">${rows}</div>`;
};

window.KB.renderBody = function () {
  const body = document.getElementById('kb-modal-body');
  if (!body) return;
  body.innerHTML = `
    <div class="px-4 pt-3 pb-2 d-flex align-items-center gap-2 flex-wrap border-bottom border-secondary-subtle">
      ${window.KB.renderTabs()}
    </div>
    <div class="px-4 pt-3">
      ${window.KB.renderScanResult()}
    </div>
    ${window.KB.renderForm()}
    <div style="max-height: 380px; overflow-y: auto;">
      ${window.KB.renderList()}
    </div>
  `;
  if (window.applyTranslations) window.applyTranslations();
};