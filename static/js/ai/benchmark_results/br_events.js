/**
 * WealthFlow AI Workspace - Benchmark Results: Entry Point
 * Public modal-open function. Depends on br_state.js and br_render.js.
 */

"use strict";

window.BR = window.BR || {};

window.openBenchmarkResultsModal = function () {
  window.BR.state.reports = [];
  window.BR.state.loading = false;
  window.BR.state.running = false;
  window.BR.state.error = null;

  showModal(window.BR.renderModalShell());
  window.BR.load();
};
