/**
 * WealthFlow AI Workspace - Model Management: Entry Point
 * Public modal-open function. Depends on mm_state.js and mm_render.js.
 */

'use strict';

window.MM = window.MM || {};

window.openModelManagementModal = function () {
  window.MM.state.activeModel = null;
  window.MM.state.modelVersions = [];
  window.MM.state.availableBackends = [];
  window.MM.state.loading = false;
  window.MM.state.busy = false;
  window.MM.state.error = null;

  showModal(window.MM.renderModalShell());
  window.MM.load();
};
