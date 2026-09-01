/**
 * WealthFlow AI Workspace - Benchmark Results: State & API
 * Shared state, translation helpers, and all fetch() calls against /api/ai-platform/benchmarks/.
 */

"use strict";

window.BR = window.BR || {};

window.BR.state = {
  reports: [],
  loading: false,
  running: false,
  error: null,
};

window.BR.t = function (key, fallback) {
  return (window.t && window.t(key, fallback)) || fallback || key;
};

window.BR.escapeHtml = function (str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
};

window.BR.load = function () {
  window.BR.state.loading = true;
  window.BR.state.error = null;
  window.BR.renderBody();

  fetch("/api/ai-platform/benchmarks/", { method: "GET" })
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      window.BR.state.reports = data.benchmark_reports || [];
      window.BR.state.loading = false;
      window.BR.renderBody();
    })
    .catch(function () {
      window.BR.state.loading = false;
      window.BR.state.error = window.BR.t("ai_br_error", "Failed to load benchmarks.");
      window.BR.renderBody();
    });
};

window.BR.runBenchmark = function () {
  window.BR.state.running = true;
  window.BR.renderBody();

  fetch("/api/ai-platform/benchmarks/", { method: "POST" })
    .then(function (r) {
      return r.json();
    })
    .then(function () {
      window.BR.state.running = false;
      showToast(window.BR.t("ai_br_run_ok", "Benchmark complete."), "success");
      window.BR.load();
    })
    .catch(function () {
      window.BR.state.running = false;
      showToast(window.BR.t("ai_br_run_error", "Failed to run benchmark."), "error");
      window.BR.renderBody();
    });
};
