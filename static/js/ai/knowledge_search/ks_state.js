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
  editing: null,   // { id, title, content, category }
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
  window.KS.state.editing = null;
  window.KS.renderBody();
};

window.KS.startEdit = function (id) {
  const entry = window.KS.state.results.find(function (e) { return e.id === id; });
  if (!entry) return;
  window.KS.state.editing = { id: entry.id, title: entry.title, content: entry.content, category: entry.category };
  window.KS.state.expanded = id;
  window.KS.renderBody();
};

window.KS.cancelEdit = function () {
  window.KS.state.editing = null;
  window.KS.renderBody();
};

window.KS.saveEdit = function (id) {
  const titleEl = document.getElementById('ks-edit-title-' + id);
  const contentEl = document.getElementById('ks-edit-content-' + id);
  const categoryEl = document.getElementById('ks-edit-category-' + id);
  if (!titleEl || !contentEl) return;

  fetch('/api/ai-platform/knowledge/' + id + '/', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: titleEl.value, content: contentEl.value, category: categoryEl ? categoryEl.value : undefined }),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      const idx = window.KS.state.results.findIndex(function (e) { return e.id === id; });
      if (idx !== -1) window.KS.state.results[idx] = data.entry;
      window.KS.state.editing = null;
      showToast(window.KS.t('ai_ks_edit_ok', 'Entry updated.'), 'success');
      window.KS.renderBody();
    })
    .catch(function () {
      showToast(window.KS.t('ai_ks_edit_error', 'Failed to update entry.'), 'error');
    });
};

window.KS.deleteEntry = function (id) {
  if (!confirm(window.KS.t('ai_ks_delete_confirm', 'Delete this knowledge entry?'))) return;
  fetch('/api/ai-platform/knowledge/' + id + '/', { method: 'DELETE' })
    .then(function () {
      window.KS.state.results = window.KS.state.results.filter(function (e) { return e.id !== id; });
      showToast(window.KS.t('ai_ks_delete_ok', 'Entry deleted.'), 'success');
      window.KS.renderBody();
    })
    .catch(function () {
      showToast(window.KS.t('ai_ks_delete_error', 'Failed to delete entry.'), 'error');
    });
};

window.KS.copyEntry = function (id) {
  const entry = window.KS.state.results.find(function (e) { return e.id === id; });
  if (!entry) return;
  navigator.clipboard.writeText(entry.content).then(function () {
    showToast(window.KS.t('ai_ks_copy_ok', 'Copied to clipboard.'), 'success');
  });
};

window.KS.injectEntry = function (id) {
  const entry = window.KS.state.results.find(function (e) { return e.id === id; });
  if (!entry) return;
  const inputEl = document.getElementById('ai-ws-input');
  if (!inputEl) {
    showToast(window.KS.t('ai_ks_inject_no_input', 'Open the AI chat first.'), 'error');
    return;
  }
  const prefix = '[Knowledge: ' + entry.title + ']\n' + entry.content + '\n\n';
  inputEl.value = prefix + inputEl.value;
  inputEl.focus();
  closeModal();
  showToast(window.KS.t('ai_ks_inject_ok', 'Knowledge injected into chat.'), 'success');
};
