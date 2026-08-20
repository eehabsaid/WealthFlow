/**
 * WealthFlow AI Workspace - Knowledge Search: Rendering
 */

'use strict';

window.KS = window.KS || {};

window.KS.CATEGORY_COLORS = {
  business_rule: 'bg-primary',
  codebase_architecture: 'bg-info',
  user_preference: 'bg-success',
  app_evolution: 'bg-warning text-dark',
};

window.KS.renderModalShell = function () {
  const t = window.KS.t;
  const esc = window.KS.escapeHtml;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div class="d-flex align-items-center gap-2">
        <div class="rounded-circle bg-primary bg-opacity-10 p-2 d-flex align-items-center justify-content-center" style="width:38px;height:38px;">
          <i class="bi bi-search fs-5 text-primary"></i>
        </div>
        <div>
          <h5 class="modal-title fw-bold mb-0 text-body">${esc(t('ai_ks_title', 'Knowledge Search'))}</h5>
          <small class="text-muted">${esc(t('ai_ks_subtitle', 'Search your AI knowledge base'))}</small>
        </div>
      </div>
      <button type="button" class="btn-close text-reset ms-auto" onclick="closeModal()" aria-label="Close"></button>
    </div>
    <div class="px-4 pt-3 pb-2 border-bottom border-secondary-subtle">
      <div class="input-group">
        <span class="input-group-text"><i class="bi bi-search"></i></span>
        <input
          id="ks-search-input"
          type="text"
          class="form-control"
          placeholder="${esc(t('ai_ks_placeholder', 'Search by title or content...'))}"
          oninput="window.KS.search(this.value)"
          autofocus
        />
      </div>
    </div>
    <div class="modal-body p-0" id="ks-modal-body" style="min-height: 320px; max-height: 520px; overflow-y: auto;"></div>
  `;
};

window.KS.renderBody = function () {
  const body = document.getElementById('ks-modal-body');
  if (!body) return;
  const t = window.KS.t;
  const esc = window.KS.escapeHtml;
  const state = window.KS.state;

  if (state.loading) {
    body.innerHTML = `<div class="text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>${esc(t('ai_ks_searching', 'Searching...'))}</div>`;
    return;
  }

  if (!state.searched) {
    body.innerHTML = `<div class="text-center text-muted py-5"><i class="bi bi-search fs-1 d-block mb-2"></i>${esc(t('ai_ks_prompt', 'Type to search your knowledge base.'))}</div>`;
    return;
  }

  if (state.results.length === 0) {
    body.innerHTML = `<div class="text-center text-muted py-5">${esc(t('ai_ks_no_results', 'No entries found for that query.'))}</div>`;
    return;
  }

  const items = state.results.map(function (e) {
    const isExpanded = state.expanded === e.id;
    const catColor = window.KS.CATEGORY_COLORS[e.category] || 'bg-secondary';
    const catLabel = (e.category || '').replace(/_/g, ' ');
    const preview = (e.content || '').substring(0, 120) + ((e.content || '').length > 120 ? '…' : '');
    return `
      <div class="px-4 py-3 border-bottom border-secondary-subtle" style="cursor:pointer;" onclick="window.KS.toggleExpand(${e.id})">
        <div class="d-flex align-items-start gap-2">
          <div class="flex-grow-1">
            <div class="fw-semibold text-body small">${esc(e.title)}</div>
            <span class="badge ${catColor} me-1" style="font-size:0.65rem;">${esc(catLabel)}</span>
            <span class="text-muted" style="font-size:0.75rem;">${esc(t('ai_ks_confidence', 'Confidence'))}: ${Math.round((e.confidence || 1) * 100)}%</span>
          </div>
          <i class="bi bi-chevron-${isExpanded ? 'up' : 'down'} text-muted small"></i>
        </div>
        ${isExpanded ? `<div class="mt-2 text-body small border-start border-primary ps-3" style="white-space:pre-wrap;">${esc(e.content)}</div>` : `<div class="text-muted mt-1" style="font-size:0.8rem;">${esc(preview)}</div>`}
      </div>`;
  }).join('');

  body.innerHTML = `<div class="small text-muted px-4 py-2">${state.results.length} ${esc(t('ai_ks_results_found', 'results found'))}</div>${items}`;
  if (window.applyTranslations) window.applyTranslations();
};
