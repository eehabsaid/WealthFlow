/**
 * WealthFlow AI Workspace - Knowledge Base: Entry Point & Event Handlers
 * Public modal-open function and thin handlers wired to onclick attributes.
 * Depends on kb_state.js and kb_render.js being loaded first.
 */

'use strict';

window.KB = window.KB || {};

window.openKnowledgeBaseModal = function () {
  let container = document.getElementById('modal-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'modal-container';
    document.body.appendChild(container);
  }

  window.KB.state.isFormOpen = false;
  window.KB.state.scanResult = null;
  window.KB.formError = null;

  showModal(window.KB.renderModalShell());
  window.KB.loadEntries();
};

window.KB.categoryChange = function (catCode) {
  window.KB.state.activeCategory = catCode;
  window.KB.loadEntries();
};

window.KB.newForm = function () {
  window.KB.formError = null;
  window.KB.state.isFormOpen = true;
  window.KB.renderBody();
};

window.KB.cancelForm = function () {
  window.KB.formError = null;
  window.KB.state.isFormOpen = false;
  window.KB.renderBody();
};