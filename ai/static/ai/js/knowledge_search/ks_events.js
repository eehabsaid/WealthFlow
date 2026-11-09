/**
 * WealthFlow AI Workspace - Knowledge Search: Entry Point
 */

"use strict";

window.KS = window.KS || {};

window.openKnowledgeSearchModal = function () {
  window.KS.state.results = [];
  window.KS.state.query = "";
  window.KS.state.loading = false;
  window.KS.state.searched = false;
  window.KS.state.expanded = null;
  window.KS.state.editing = null;
  window.KS.state.error = null;

  showModal(window.KS.renderModalShell());
  window.KS.renderBody();

  // Focus the input and perform initial search/load after modal renders
  setTimeout(function () {
    const input = document.getElementById("ks-search-input");
    if (input) {
      input.focus();
      const val = input.value.trim();
      window.KS.search(val);
    } else {
      window.KS.search("");
    }
  }, 50);
};
