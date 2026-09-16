/**
 * WealthFlow AI Workspace - Prompt Library: Toolbar & Modal Content
 * Toolbar (search/category/sort/favorites) and the list/detail two-pane
 * modal content.
 * Depends on: pl_state.js, pl_render_modal_shell.js, pl_render_list.js,
 * pl_render_detail.js
 * Split out of pl_render_list.js (200-line backlog).
 */

"use strict";

window.PromptLib = window.PromptLib || {};

window.PromptLib.renderModalContent = function () {
  const body = document.getElementById("prompt-library-modal-body");
  if (!body) return;

  const state = window.PromptLib.state;
  const t = window.PromptLib.t;
  const esc = window.PromptLib.escapeHtml;

  if (state.isFormOpen) {
    body.innerHTML = window.PromptLib.renderFormHtml();
    return;
  }

  const localizedCategories = state.categories.map(window.PromptLib.getLocalizedCategory);

  body.innerHTML = `
    <div class="prompt-lib-toolbar border-bottom p-3 bg-body-tertiary">
      <div class="row g-2 align-items-center">
        <div class="col-12 col-md-5">
          <div class="input-group input-group-sm">
            <span class="input-group-text bg-body text-muted"><i class="bi bi-search"></i></span>
            <input type="text" class="form-control" id="prompt-search-input"
              placeholder="${esc(t("ai_prompt_search_placeholder", "Search prompts by name, content, description..."))}"
              value="${esc(state.searchQuery)}"
              oninput="window._promptLibSearchInput(this.value)">
            ${
              state.searchQuery
                ? `
              <button class="btn btn-outline-secondary" type="button" onclick="window._promptLibClearSearch()">
                <i class="bi bi-x-lg"></i>
              </button>
            `
                : ""
            }
          </div>
        </div>

        <div class="col-6 col-md-3">
          <select class="form-select form-select-sm" id="prompt-category-select" onchange="window._promptLibCategoryChange(this.value)">
            <option value="all" ${state.activeCategory === "all" ? "selected" : ""}>
              ${esc(t("ai_prompt_cat_all", "All Categories"))}
            </option>
            ${localizedCategories
              .map(
                (c) => `
              <option value="${esc(c.code)}" ${state.activeCategory === c.code ? "selected" : ""}>
                ${esc(c.localizedName)} (${c.prompts_count || 0})
              </option>
            `
              )
              .join("")}
          </select>
        </div>

        <div class="col-6 col-md-4 d-flex align-items-center justify-content-end gap-2">
          <select class="form-select form-select-sm" style="max-width: 140px;" onchange="window._promptLibSortChange(this.value)">
            <option value="favorites" ${state.sortBy === "favorites" ? "selected" : ""}>${esc(t("ai_prompt_sort_favorites", "Favorites First"))}</option>
            <option value="recently_used" ${state.sortBy === "recently_used" ? "selected" : ""}>${esc(t("ai_prompt_sort_recently_used", "Recently Used"))}</option>
            <option value="most_used" ${state.sortBy === "most_used" ? "selected" : ""}>${esc(t("ai_prompt_sort_most_used", "Most Used"))}</option>
            <option value="name" ${state.sortBy === "name" ? "selected" : ""}>${esc(t("ai_prompt_sort_name", "Alphabetical"))}</option>
          </select>

          <button type="button" class="btn btn-sm ${state.favoritesOnly ? "btn-warning text-dark" : "btn-outline-secondary"} d-inline-flex align-items-center gap-1"
            onclick="window._promptLibToggleFavoritesFilter()" title="${esc(t("ai_prompt_filter_fav_tooltip", "Show Favorites Only"))}">
            <i class="bi ${state.favoritesOnly ? "bi-star-fill" : "bi-star"}"></i>
          </button>
        </div>
      </div>
    </div>

    <div class="row g-0 flex-grow-1" style="min-height: 440px;">
      <!-- Left Prompt List (Independent Scrollable Container) -->
      <div class="col-12 col-md-5 border-end d-flex flex-column" style="max-height: 480px; overflow-y: auto;">
        ${window.PromptLib.renderPromptListHtml()}

        <!-- Pagination Footer -->
        ${
          state.totalPages > 1
            ? `
          <div class="mt-auto p-2 border-top bg-body-tertiary d-flex align-items-center justify-content-between">
            <button class="btn btn-sm btn-outline-secondary" ${state.page <= 1 ? "disabled" : ""} onclick="window._promptLibPageChange(${state.page - 1})">
              <i class="bi bi-chevron-left"></i>
            </button>
            <small class="text-muted font-monospace" style="font-size:0.75rem;">
              ${state.page} / ${state.totalPages}
            </small>
            <button class="btn btn-sm btn-outline-secondary" ${state.page >= state.totalPages ? "disabled" : ""} onclick="window._promptLibPageChange(${state.page + 1})">
              <i class="bi bi-chevron-right"></i>
            </button>
          </div>
        `
            : ""
        }
      </div>

      <!-- Right Prompt Details / Preview (Independent Scrollable Container) -->
      <div class="col-12 col-md-7 p-4 d-flex flex-column bg-body" style="max-height: 480px; overflow-y: auto;">
        ${
          state.selectedPrompt
            ? window.PromptLib.renderPromptDetailPaneHtml(
                window.PromptLib.getLocalizedPrompt(state.selectedPrompt)
              )
            : `
          <div class="text-center text-muted my-auto py-5">
            <i class="bi bi-chat-left-text fs-1 opacity-25 d-block mb-3"></i>
            <span data-i18n="ai_prompt_select_prompt_hint">${esc(t("ai_prompt_select_prompt_hint", "Select a prompt from the list to preview details."))}</span>
          </div>
        `
        }
      </div>
    </div>
  `;

  if (window._applyTranslations) {
    window._applyTranslations();
  }
};
