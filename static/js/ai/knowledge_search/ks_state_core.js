/**
 * WealthFlow AI Workspace - Knowledge Search: State & API (core)
 * Split out of ks_state.js (200-line backlog).
 */

"use strict";

window.KS = window.KS || {};

window.KS.state = {
  results: [],
  query: "",
  loading: false,
  searched: false,
  expanded: null,
  editing: null,
  error: null,
};

window.KS._debounceTimer = null;
window.KS._abortController = null;

window.KS.t = function (key, fallback) {
  return (window.t && window.t(key, fallback)) || fallback || key;
};

window.KS.escapeHtml = function (str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
};

window.KS.csrfToken = function () {
  return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
};

window.KS.search = function (query) {
  var queryString = String(query || "");
  window.KS.state.query = queryString;
  clearTimeout(window.KS._debounceTimer);

  if (window.KS._abortController) {
    window.KS._abortController.abort();
    window.KS._abortController = null;
  }

  var trimmed = queryString.trim();

  window.KS._debounceTimer = setTimeout(
    async function () {
      window.KS.state.loading = true;
      window.KS.state.error = null;
      window.KS.renderBody();

      var controller = new AbortController();
      window.KS._abortController = controller;

      try {
        var url = trimmed
          ? "/api/ai-platform/knowledge/?search=" + encodeURIComponent(trimmed)
          : "/api/ai-platform/knowledge/";
        var res = await fetch(url, { signal: controller.signal });
        if (res.ok) {
          var data = await res.json();
          window.KS.state.results = data.entries || [];
          window.KS.state.searched = true;
        } else {
          window.KS.state.results = [];
          window.KS.state.searched = true;
          window.KS.state.error = window.KS.t("ai_ks_error", "Search failed. Please try again.");
        }
      } catch (e) {
        if (e.name === "AbortError") return;
        window.KS.state.results = [];
        window.KS.state.searched = true;
        window.KS.state.error = window.KS.t("ai_ks_error", "Search failed. Please try again.");
      } finally {
        if (!controller.signal.aborted) {
          window.KS.state.loading = false;
          window.KS._abortController = null;
          window.KS.renderBody();
        }
      }
    },
    trimmed ? 300 : 0
  );
};
