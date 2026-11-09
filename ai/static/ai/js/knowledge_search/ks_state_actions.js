/**
 * WealthFlow AI Workspace - Knowledge Search: State & API (copy/inject)
 * Split out of ks_state.js (200-line backlog).
 */

"use strict";

window.KS = window.KS || {};

window.KS.copyEntry = function (id) {
  var entry = window.KS.state.results.find(function (e) {
    return e.id === id;
  });
  if (!entry) return;
  navigator.clipboard.writeText(entry.content).then(function () {
    if (window.showToast)
      window.showToast(window.KS.t("ai_ks_copy_ok", "Copied to clipboard."), "success");
  });
};

window.KS.injectEntry = function (id) {
  var entry = window.KS.state.results.find(function (e) {
    return e.id === id;
  });
  if (!entry) return;
  var inputEl = document.getElementById("ai-ws-input");
  if (!inputEl) {
    if (window.showToast)
      window.showToast(window.KS.t("ai_ks_inject_no_input", "Open the AI chat first."), "error");
    return;
  }
  var prefix = "[Knowledge: " + entry.title + "]\n" + entry.content + "\n\n";
  inputEl.value = prefix + inputEl.value;
  inputEl.focus();
  if (window.closeModal) window.closeModal();
  if (window.showToast)
    window.showToast(window.KS.t("ai_ks_inject_ok", "Knowledge injected into chat."), "success");
};
