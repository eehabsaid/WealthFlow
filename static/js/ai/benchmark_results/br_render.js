/**
 * WealthFlow AI Workspace - Benchmark Results: Rendering
 * Modal shell HTML and dynamic body rendering.
 */

'use strict';

window.BR = window.BR || {};

window.BR.SCORE_DIMS = [
  ['business_analysis',      'ai_br_score_business',      'Business Analysis'],
  ['financial_reasoning',    'ai_br_score_financial',     'Financial Reasoning'],
  ['architecture',           'ai_br_score_architecture',  'Architecture'],
  ['code_understanding',     'ai_br_score_code',          'Code Understanding'],
  ['feature_suggestions',    'ai_br_score_features',      'Feature Suggestions'],
  ['hallucination_resistance','ai_br_score_hallucination','Hallucination Resistance'],
  ['instruction_following',  'ai_br_score_instructions',  'Instruction Following'],
];

window.BR.renderModalShell = function () {
  const t = window.BR.t;
  const esc = window.BR.escapeHtml;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div class="d-flex align-items-center gap-2">
        <div class="rounded-circle bg-primary bg-opacity-10 p-2 d-flex align-items-center justify-content-center" style="width:38px;height:38px;">
          <i class="bi bi-graph-up-arrow fs-5 text-primary"></i>
        </div>
        <div>
          <h5 class="modal-title fw-bold mb-0 text-body">${esc(t('ai_br_title', 'Benchmark Results'))}</h5>
          <small class="text-muted">${esc(t('ai_br_subtitle', '7-Dimension Model Evaluation'))}</small>
        </div>
      </div>
      <div class="d-flex align-items-center gap-2 ms-auto">
        <button type="button" class="btn btn-sm btn-primary d-inline-flex align-items-center gap-1" onclick="window.BR.runBenchmark()">
          <i class="bi bi-play-fill"></i> <span>${esc(t('ai_br_run_btn', 'Run Benchmark'))}</span>
        </button>
        <button type="button" class="btn-close text-reset ms-2" onclick="closeModal()" aria-label="Close"></button>
      </div>
    </div>
    <div class="modal-body p-0" id="br-modal-body" style="min-height: 380px;"></div>
  `;
};

window.BR.renderScoreBars = function (scores) {
  const t = window.BR.t;
  const esc = window.BR.escapeHtml;
  return window.BR.SCORE_DIMS.map(function (dim) {
    const key = dim[0];
    const i18nKey = dim[1];
    const fallback = dim[2];
    const val = scores[key] ?? 0;
    const pct = Math.round(val * 100);
    const color = pct >= 70 ? 'bg-success' : pct >= 40 ? 'bg-warning' : 'bg-danger';
    return `<div class="mb-2">
      <div class="d-flex justify-content-between small mb-1">
        <span class="text-muted">${esc(t(i18nKey, fallback))}</span>
        <span class="fw-semibold">${pct}%</span>
      </div>
      <div class="progress" style="height:6px;">
        <div class="progress-bar ${color}" style="width:${pct}%"></div>
      </div>
    </div>`;
  }).join('');
};

window.BR.renderBody = function () {
  const body = document.getElementById('br-modal-body');
  if (!body) return;
  const t = window.BR.t;
  const esc = window.BR.escapeHtml;
  const state = window.BR.state;

  if (state.loading || state.running) {
    const msg = state.running
      ? t('ai_br_run_btn', 'Running benchmark...')
      : t('ai_br_loading', 'Loading benchmark reports...');
    body.innerHTML = `<div class="text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>${esc(msg)}</div>`;
    return;
  }

  if (state.error) {
    body.innerHTML = `<div class="alert alert-danger m-4">${esc(state.error)}</div>`;
    return;
  }

  if (state.reports.length === 0) {
    body.innerHTML = `<div class="text-center text-muted py-5">${esc(t('ai_br_empty', 'No benchmark reports yet.'))}</div>`;
    return;
  }

  const cards = state.reports.map(function (r) {
    const passed = r.passed_promotion_gate;
    const badgeClass = passed ? 'bg-success' : 'bg-danger';
    const badgeLabel = passed ? t('ai_br_passed', 'Passed') : t('ai_br_failed', 'Failed');
    const overall = Math.round((r.overall_score ?? 0) * 100);
    const date = r.created_at ? r.created_at.substring(0, 10) : '';
    return `<div class="border rounded p-3 mb-3">
      <div class="d-flex justify-content-between align-items-start mb-3">
        <div>
          <div class="fw-semibold text-body">${esc(r.model_version)}</div>
          <div class="small text-muted">${esc(date)}</div>
        </div>
        <div class="d-flex align-items-center gap-2">
          <span class="fw-bold fs-5 text-primary">${overall}%</span>
          <span class="badge ${badgeClass}">${esc(badgeLabel)}</span>
        </div>
      </div>
      ${window.BR.renderScoreBars(r.scores || {})}
    </div>`;
  }).join('');

  body.innerHTML = `<div class="p-4" style="max-height:520px;overflow-y:auto;">${cards}</div>`;
  if (window.applyTranslations) window.applyTranslations();
};
