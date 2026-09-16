/**
 * WealthFlow AI Workspace - Prompt Library: Modal Shell
 * Modal header/body shell markup.
 * Depends on: pl_state.js
 * Split out of pl_render_list.js (200-line backlog).
 */

"use strict";

window.PromptLib = window.PromptLib || {};

window.PromptLib.renderModalShellHtml = function () {
  const t = window.PromptLib.t;
  const esc = window.PromptLib.escapeHtml;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div class="d-flex align-items-center gap-2">
        <div class="rounded-circle bg-primary bg-opacity-10 p-2 d-flex align-items-center justify-content-center" style="width:38px;height:38px;">
          <i class="bi bi-chat-left-quote fs-5 text-primary"></i>
        </div>
        <div>
          <h5 class="modal-title fw-bold mb-0 text-body" data-i18n="ai_prompt_library_title">${esc(t("ai_prompt_library_title", "Prompt Library"))}</h5>
          <small class="text-muted" data-i18n="ai_prompt_library_subtitle">${esc(t("ai_prompt_library_subtitle", "Reusable prompts for WealthFlow AI Workspace"))}</small>
        </div>
      </div>
      <div class="d-flex align-items-center gap-2 ms-auto">
        <button type="button" class="btn btn-sm btn-primary d-inline-flex align-items-center gap-1" onclick="window._promptLibNewForm()">
          <i class="bi bi-plus-lg"></i> <span data-i18n="ai_prompt_new_btn">${esc(t("ai_prompt_new_btn", "New Prompt"))}</span>
        </button>
        <button type="button" class="btn-close text-reset ms-2" onclick="closeModal()" aria-label="Close"></button>
      </div>
    </div>

    <div class="modal-body p-0" id="prompt-library-modal-body" style="min-height: 520px;">
      <!-- Rendered via JS -->
    </div>
  `;
};
