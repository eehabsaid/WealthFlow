/**
 * WealthFlow AI Workspace - Dataset Manager: State & API
 * Shared state, translation helpers, and all fetch() calls against /api/ai-platform/datasets/.
 */

'use strict';

window.DM = window.DM || {};

window.DM.state = {
  stats: null,
  loading: false,
  generating: false,
  error: null,
};

window.DM.t = function (key, fallback) {
  return (window.t && window.t(key, fallback)) || fallback || key;
};

window.DM.escapeHtml = function (str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
};

window.DM.loadStats = function () {
  window.DM.state.loading = true;
  window.DM.state.error = null;
  window.DM.renderBody();

  fetch('/api/ai-platform/datasets/', { method: 'GET' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      window.DM.state.stats = data.dataset_stats || null;
      window.DM.state.loading = false;
      window.DM.renderBody();
    })
    .catch(function () {
      window.DM.state.loading = false;
      window.DM.state.error = window.DM.t('ai_dm_error', 'Failed to load dataset stats.');
      window.DM.renderBody();
    });
};

window.DM.generateDataset = function () {
  window.DM.state.generating = true;
  window.DM.renderBody();

  fetch('/api/ai-platform/datasets/', { method: 'POST' })
    .then(function (r) { return r.json(); })
    .then(function () {
      window.DM.state.generating = false;
      showToast(window.DM.t('ai_dm_generated_ok', 'Dataset generated successfully.'), 'success');
      window.DM.loadStats();
    })
    .catch(function () {
      window.DM.state.generating = false;
      showToast(window.DM.t('ai_dm_generate_error', 'Failed to generate dataset.'), 'error');
      window.DM.renderBody();
    });
};
