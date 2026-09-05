/**
 * WealthFlow AI Workspace - Model Management: State & API
 * Shared state, translation helpers, and all fetch() calls against /api/ai-platform/models/.
 */

"use strict";

window.MM = window.MM || {};

window.MM.state = {
  activeModel: null,
  modelVersions: [],
  availableBackends: [],
  liveChatModel: "qwen2.5:3b",
  loading: false,
  busy: false,
  error: null,
};

window.MM.t = function (key, fallback) {
  return (window.t && window.t(key, fallback)) || fallback || key;
};

window.MM.escapeHtml = function (str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
};

window.MM.load = function () {
  window.MM.state.loading = true;
  window.MM.state.error = null;
  window.MM.renderBody();

  fetch("/api/ai-platform/models/", { method: "GET" })
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      window.MM.state.activeModel = data.active_model || null;
      window.MM.state.modelVersions = data.model_versions || [];
      window.MM.state.availableBackends = data.available_backends || [];
      window.MM.state.liveChatModel = data.live_chat_model || "qwen2.5:3b";
      window.MM.state.loading = false;
      window.MM.renderBody();
    })
    .catch(function () {
      window.MM.state.loading = false;
      window.MM.state.error = window.MM.t("ai_mm_error", "Failed to load model versions.");
      window.MM.renderBody();
    });
};

window.MM.fineTune = function () {
  const baseModel = document.getElementById("mm-base-model")?.value?.trim() || "";
  const backend = document.getElementById("mm-backend")?.value?.trim() || "";
  if (!baseModel || !backend) return;

  window.MM.state.busy = true;
  window.MM.renderBody();

  fetch("/api/ai-platform/models/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "fine_tune", base_model: baseModel, backend_name: backend }),
  })
    .then(function (r) {
      return r.json();
    })
    .then(function () {
      window.MM.state.busy = false;
      showToast(window.MM.t("ai_mm_finetune_ok", "Fine-tuning triggered successfully."), "success");
      window.MM.load();
    })
    .catch(function () {
      window.MM.state.busy = false;
      showToast(window.MM.t("ai_mm_finetune_error", "Failed to trigger fine-tuning."), "error");
      window.MM.renderBody();
    });
};

window.MM.promote = function (versionName) {
  window.MM.state.busy = true;
  window.MM.renderBody();

  fetch("/api/ai-platform/models/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "promote", version_name: versionName }),
  })
    .then(function (r) {
      return r.json();
    })
    .then(function () {
      window.MM.state.busy = false;
      showToast(window.MM.t("ai_mm_promote_ok", "Model promoted to production."), "success");
      window.MM.load();
    })
    .catch(function () {
      window.MM.state.busy = false;
      showToast(window.MM.t("ai_mm_promote_error", "Failed to promote model."), "error");
      window.MM.renderBody();
    });
};
