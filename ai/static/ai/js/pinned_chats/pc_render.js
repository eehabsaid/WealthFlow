/**
 * WealthFlow AI Workspace - Pinned Chats: Rendering
 */

"use strict";

window.PC = window.PC || {};

window.PC.renderModalShell = function () {
  const t = window.PC.t;
  const esc = window.PC.escapeHtml;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div class="d-flex align-items-center gap-2">
        <div class="rounded-circle bg-primary bg-opacity-10 p-2 d-flex align-items-center justify-content-center" style="width:38px;height:38px;">
          <i class="bi bi-pin-angle-fill fs-5 text-primary"></i>
        </div>
        <div>
          <h5 class="modal-title fw-bold mb-0 text-body">${esc(t("ai_pc_title", "Pinned Chats"))}</h5>
          <small class="text-muted">${esc(t("ai_pc_subtitle", "Your bookmarked conversations"))}</small>
        </div>
      </div>
      <button type="button" class="btn-close text-reset ms-auto" onclick="closeModal()" aria-label="Close"></button>
    </div>
    <div class="modal-body p-0" id="pc-modal-body" style="min-height: 300px;"></div>
  `;
};

window.PC.renderBody = function () {
  const body = document.getElementById("pc-modal-body");
  if (!body) return;
  const t = window.PC.t;
  const esc = window.PC.escapeHtml;
  const state = window.PC.state;

  if (state.loading) {
    body.innerHTML = `<div class="text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>${esc(t("ai_pc_loading", "Loading pinned chats..."))}</div>`;
    return;
  }

  if (state.error) {
    body.innerHTML = `<div class="alert alert-danger m-4">${esc(state.error)}</div>`;
    return;
  }

  if (state.conversations.length === 0) {
    body.innerHTML = `
      <div class="text-center text-muted py-5">
        <i class="bi bi-pin-angle fs-1 d-block mb-2"></i>
        ${esc(t("ai_pc_empty", "No pinned chats yet. Pin a conversation using the pin icon."))}
      </div>`;
    return;
  }

  const items = state.conversations
    .map(function (c) {
      const date = c.updated_at ? c.updated_at.substring(0, 10) : "";
      return `
      <div class="d-flex align-items-center px-4 py-3 border-bottom border-secondary-subtle" style="gap:12px;">
        <div class="flex-grow-1" style="cursor:pointer;" onclick="closeModal(); window._switchAIChatConversation('${esc(c.id)}')">
          <div class="fw-semibold text-body small">${esc(c.title || t("ai_ws_untitled", "Untitled"))}</div>
          <div class="text-muted" style="font-size:0.75rem;">${esc(date)}</div>
        </div>
        <button class="btn btn-sm btn-outline-secondary py-0 px-2" title="${esc(t("ai_pc_unpin", "Unpin"))}" onclick="window.PC.unpin('${esc(c.id)}')">
          <i class="bi bi-pin-angle-fill"></i>
        </button>
      </div>`;
    })
    .join("");

  body.innerHTML = `<div>${items}</div>`;
  if (window.applyTranslations) window.applyTranslations();
};
