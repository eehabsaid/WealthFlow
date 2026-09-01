/**
 * WealthFlow AI Workspace - Pinned Chats: State & API
 */

"use strict";

window.PC = window.PC || {};

window.PC.state = {
  conversations: [],
  loading: false,
  error: null,
};

window.PC.t = function (key, fallback) {
  return (window.t && window.t(key, fallback)) || fallback || key;
};

window.PC.escapeHtml = function (str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
};

window.PC.load = function () {
  window.PC.state.loading = true;
  window.PC.state.error = null;
  window.PC.renderBody();

  fetch("/api/financial-advisor/ai/conversations/?pinned=true")
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      window.PC.state.conversations = data.conversations || [];
      window.PC.state.loading = false;
      window.PC.renderBody();
    })
    .catch(function () {
      window.PC.state.loading = false;
      window.PC.state.error = window.PC.t("ai_pc_error", "Failed to load pinned chats.");
      window.PC.renderBody();
    });
};

window.PC.unpin = function (convId) {
  fetch("/api/financial-advisor/ai/conversations/" + convId + "/", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")?.value || "",
    },
    body: JSON.stringify({ is_pinned: false }),
  })
    .then(function () {
      window.PC.state.conversations = window.PC.state.conversations.filter(function (c) {
        return String(c.id) !== String(convId);
      });
      window.PC.renderBody();
      if (window._fetchAIChatConversations) window._fetchAIChatConversations();
    })
    .catch(function () {
      showToast(window.PC.t("ai_pc_unpin_error", "Failed to unpin conversation."), "error");
    });
};
