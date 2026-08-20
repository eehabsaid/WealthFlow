/**
 * WealthFlow AI Workspace - Knowledge Search: Entry Point
 */

'use strict';

window.KS = window.KS || {};

window.openKnowledgeSearchModal = function () {
  window.KS.state.results = [];
  window.KS.state.query = '';
  window.KS.state.loading = false;
  window.KS.state.searched = false;
  window.KS.state.expanded = null;
  window.KS.state.error = null;

  showModal(window.KS.renderModalShell());
  window.KS.renderBody();

  // Focus the input after modal renders
  setTimeout(function () {
    const input = document.getElementById('ks-search-input');
    if (input) input.focus();
  }, 100);
};
