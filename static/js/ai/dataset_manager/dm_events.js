/**
 * WealthFlow AI Workspace - Dataset Manager: Entry Point
 * Public modal-open function. Depends on dm_state.js and dm_render.js.
 */

'use strict';

window.DM = window.DM || {};

window.openDatasetManagerModal = function () {
  window.DM.state.stats = null;
  window.DM.state.loading = false;
  window.DM.state.generating = false;
  window.DM.state.error = null;

  showModal(window.DM.renderModalShell());
  window.DM.loadStats();
};
