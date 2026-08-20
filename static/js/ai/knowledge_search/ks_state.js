/**
 * WealthFlow AI Workspace - Knowledge Search: State & API
 */

'use strict';

window.KS = window.KS || {};

window.KS.state = {
  results: [],
  query: '',
  loading: false,
  searched: false,
  expanded: null,
};

window.KS._debounceTimer = null;

window.KS.t = function (key, fallback) {
  return (window.t && window.t(key, fallback)) || fallback || key;
};

window.KS.escapeHtml = function (str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
};

window.KS.search = function (query) {
  window.KS.state.query = query;
  clearTimeout(window.KS._debounceTimer);

  if (!query.trim()) {
    window.KS.state.results = [];
    window.KS.state.searched = false;
    window.KS.renderBody();
    return;
  }

  window.KS._debounceTimer = setTimeout(function () {
    window.KS.state.loading = true;
    window.KS.renderBody();

    fetch('/api/ai-platform/knowledge/?search=' + encodeURIComponent(query.trim()))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        window.KS.state.results = data.entries || [];
        window.KS.state.loading = false;
        window.KS.state.searched = true;
        window.KS.renderBody();
      })
      .catch(function () {
        window.KS.state.loading = false;
        window.KS.state.searched = true;
        window.KS.renderBody();
      });
  }, 350);
};

window.KS.toggleExpand = function (id) {
  window.KS.state.expanded = window.KS.state.expanded === id ? null : id;
  window.KS.renderBody();
};
