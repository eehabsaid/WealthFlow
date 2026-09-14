/**
 * WealthFlow AI Workspace - Prompt Library: Modal Shell & List Rendering
 * Modal header/body shell, toolbar (search/category/sort/favorites), and the
 * scrollable prompt list with pagination footer.
 * Depends on: pl_state.js
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
