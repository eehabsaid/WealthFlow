/**
 * WealthFlow AI Workspace - Prompt Library: Prompt List Rendering
 * The scrollable prompt list markup.
 * Depends on: pl_state.js
 * Modal shell and toolbar/content split out to pl_render_modal_shell.js and
 * pl_render_toolbar.js (200-line backlog).
 */

"use strict";

window.PromptLib = window.PromptLib || {};

window.PromptLib.renderPromptListHtml = function () {
  const state = window.PromptLib.state;
  const t = window.PromptLib.t;
  const esc = window.PromptLib.escapeHtml;

  if (state.items.length === 0) {
    return `
      <div class="p-4 text-center text-muted my-auto">
        <i class="bi bi-inbox fs-2 d-block mb-2 text-secondary opacity-50"></i>
        <div class="fw-semibold" data-i18n="ai_prompt_no_results">${esc(t("ai_prompt_no_results", "No prompts found"))}</div>
        <small class="text-secondary" data-i18n="ai_prompt_no_results_sub">${esc(t("ai_prompt_no_results_sub", "Try adjusting your search query or filters."))}</small>
      </div>
    `;
  }

  return `
    <div class="list-group list-group-flush">
      ${state.items
        .map((rawP) => {
          const p = window.PromptLib.getLocalizedPrompt(rawP);
          const isSelected = state.selectedPrompt && state.selectedPrompt.id === p.id;
          return `
          <div class="list-group-item list-group-item-action p-3 ${isSelected ? "active bg-primary bg-opacity-10 border-primary-subtle" : ""}"
            style="cursor: pointer;" onclick="window._promptLibSelectPrompt(${p.id})">
            <div class="d-flex align-items-center justify-content-between mb-1" style="min-width: 0;">
              <h6 class="mb-0 fw-semibold text-truncate text-body ${isSelected ? "text-primary" : ""}"
                style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: calc(100% - 24px);">${esc(p.localizedName)}</h6>
              <button type="button" class="btn btn-link p-0 text-decoration-none ms-2" onclick="event.stopPropagation(); window._promptLibToggleFavorite(${p.id})">
                <i class="bi ${p.is_favorite ? "bi-star-fill text-warning" : "bi-star text-muted"} fs-6"></i>
              </button>
            </div>
            <p class="small text-muted text-truncate mb-2" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;">${esc(p.localizedDesc || p.localizedContent)}</p>
            <div class="d-flex align-items-center justify-content-between gap-2">
              <span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary-subtle font-monospace prompt-lib-cat-badge">
                <i class="bi ${p.category?.icon || "bi-folder"} me-1"></i>${esc(p.localizedCatName)}
              </span>
              ${
                p.usage_count > 0
                  ? `
                <small class="text-muted font-monospace text-nowrap" style="font-size:0.68rem;">
                  <i class="bi bi-arrow-repeat me-1"></i>${p.usage_count} ${esc(t("ai_prompt_uses_label", "uses"))}
                </small>
              `
                  : ""
              }
            </div>
          </div>
        `;
        })
        .join("")}
    </div>
  `;
};
