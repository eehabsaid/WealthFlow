/**
 * WealthFlow AI Workspace - Prompt Library Module
 * Handles Prompt Library Modal, CRUD Operations, Category Filtering, Live Search,
 * Optimistic UI Updates, Pagination, Internationalization, and Inserting Text into AI Workspace Input.
 */

'use strict';

(function () {
  let _promptsState = {
    categories: [],
    items: [],
    selectedPrompt: null,
    activeCategory: 'all',
    searchQuery: '',
    favoritesOnly: false,
    sortBy: 'favorites',
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    isFormOpen: false,
    editingPromptId: null,
    searchDebounceTimer: null,
  };

  function _promptT(key, fallback) {
    if (window.t) {
      const translated = window.t(key);
      if (translated && translated !== key) return translated;
    }
    return fallback;
  }

  function _escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function _getLocalizedCategory(c) {
    if (!c) return { name: '', description: '', code: '' };
    const nameKey = `ai_prompt_cat_${c.code}_name`;
    const descKey = `ai_prompt_cat_${c.code}_desc`;
    const locName = _promptT(nameKey, c.name);
    const locDesc = _promptT(descKey, c.description);
    return {
      ...c,
      localizedName: locName,
      localizedDesc: locDesc,
    };
  }

  function _getLocalizedPrompt(p) {
    if (!p) return null;
    let locName = p.name;
    let locDesc = p.description;
    let locContent = p.content;

    if (p.translation_key) {
      const nameKey = `ai_prompt_seed_${p.translation_key}_name`;
      const descKey = `ai_prompt_seed_${p.translation_key}_desc`;
      const contentKey = `ai_prompt_seed_${p.translation_key}_content`;

      locName = _promptT(nameKey, p.name);
      locDesc = _promptT(descKey, p.description);
      locContent = _promptT(contentKey, p.content);
    }

    const catObj = p.category ? _getLocalizedCategory(p.category) : null;
    const catName = catObj ? catObj.localizedName : (p.category_name || p.category_code || '');

    return {
      ...p,
      localizedName: locName,
      localizedDesc: locDesc,
      localizedContent: locContent,
      localizedCatName: catName,
    };
  }

  function openPromptLibraryModal() {
    let container = document.getElementById('modal-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'modal-container';
      document.body.appendChild(container);
    }

    _promptsState.isFormOpen = false;
    _promptsState.editingPromptId = null;
    _promptsState.page = 1;

    showModal(_renderPromptLibraryModalHtml());
    _loadCategoriesAndPrompts();
  }

  function _renderPromptLibraryModalHtml() {
    return `
      <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
        <div class="d-flex align-items-center gap-2">
          <div class="rounded-circle bg-primary bg-opacity-10 p-2 d-flex align-items-center justify-content-center" style="width:38px;height:38px;">
            <i class="bi bi-chat-left-quote fs-5 text-primary"></i>
          </div>
          <div>
            <h5 class="modal-title fw-bold mb-0 text-body" data-i18n="ai_prompt_library_title">${_escapeHtml(_promptT('ai_prompt_library_title', 'Prompt Library'))}</h5>
            <small class="text-muted" data-i18n="ai_prompt_library_subtitle">${_escapeHtml(_promptT('ai_prompt_library_subtitle', 'Reusable prompts for WealthFlow AI Workspace'))}</small>
          </div>
        </div>
        <div class="d-flex align-items-center gap-2 ms-auto">
          <button type="button" class="btn btn-sm btn-primary d-inline-flex align-items-center gap-1" onclick="window._promptLibNewForm()">
            <i class="bi bi-plus-lg"></i> <span data-i18n="ai_prompt_new_btn">${_escapeHtml(_promptT('ai_prompt_new_btn', 'New Prompt'))}</span>
          </button>
          <button type="button" class="btn-close text-reset ms-2" onclick="closeModal()" aria-label="Close"></button>
        </div>
      </div>

      <div class="modal-body p-0" id="prompt-library-modal-body" style="min-height: 520px;">
        <!-- Rendered via JS -->
      </div>
    `;
  }

  async function _loadCategoriesAndPrompts() {
    try {
      const catRes = await fetch('/api/ai-platform/prompts/categories/');
      if (catRes.ok) {
        const catData = await catRes.json();
        _promptsState.categories = catData.categories || [];
      }
    } catch (e) {
      console.warn('Failed to load prompt categories', e);
    }
    await _fetchPrompts();
  }

  async function _fetchPrompts() {
    const params = new URLSearchParams();
    if (_promptsState.activeCategory && _promptsState.activeCategory !== 'all') {
      params.append('category_code', _promptsState.activeCategory);
    }
    if (_promptsState.searchQuery) {
      params.append('search', _promptsState.searchQuery);
    }
    if (_promptsState.favoritesOnly) {
      params.append('favorites_only', 'true');
    }
    params.append('sort_by', _promptsState.sortBy);
    params.append('page', _promptsState.page);
    params.append('page_size', _promptsState.pageSize);

    try {
      const res = await fetch(`/api/ai-platform/prompts/?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        _promptsState.items = data.items || [];
        _promptsState.total = data.total || 0;
        _promptsState.page = data.page || 1;
        _promptsState.totalPages = data.total_pages || 1;

        if (_promptsState.selectedPrompt) {
          const updated = _promptsState.items.find(p => p.id === _promptsState.selectedPrompt.id);
          if (updated) {
            _promptsState.selectedPrompt = updated;
          } else if (_promptsState.items.length > 0) {
            _promptsState.selectedPrompt = _promptsState.items[0];
          } else {
            _promptsState.selectedPrompt = null;
          }
        } else if (_promptsState.items.length > 0) {
          _promptsState.selectedPrompt = _promptsState.items[0];
        } else {
          _promptsState.selectedPrompt = null;
        }
      }
    } catch (err) {
      console.error('Error fetching prompts', err);
    }

    _renderModalContent();
  }

  function _renderModalContent() {
    const body = document.getElementById('prompt-library-modal-body');
    if (!body) return;

    if (_promptsState.isFormOpen) {
      body.innerHTML = _renderFormHtml();
      return;
    }

    const localizedCategories = _promptsState.categories.map(_getLocalizedCategory);

    body.innerHTML = `
      <div class="prompt-lib-toolbar border-bottom p-3 bg-body-tertiary">
        <div class="row g-2 align-items-center">
          <div class="col-12 col-md-5">
            <div class="input-group input-group-sm">
              <span class="input-group-text bg-body text-muted"><i class="bi bi-search"></i></span>
              <input type="text" class="form-control" id="prompt-search-input"
                placeholder="${_escapeHtml(_promptT('ai_prompt_search_placeholder', 'Search prompts by name, content, description...'))}"
                value="${_escapeHtml(_promptsState.searchQuery)}"
                oninput="window._promptLibSearchInput(this.value)">
              ${_promptsState.searchQuery ? `
                <button class="btn btn-outline-secondary" type="button" onclick="window._promptLibClearSearch()">
                  <i class="bi bi-x-lg"></i>
                </button>
              ` : ''}
            </div>
          </div>

          <div class="col-6 col-md-3">
            <select class="form-select form-select-sm" id="prompt-category-select" onchange="window._promptLibCategoryChange(this.value)">
              <option value="all" ${_promptsState.activeCategory === 'all' ? 'selected' : ''}>
                ${_escapeHtml(_promptT('ai_prompt_cat_all', 'All Categories'))}
              </option>
              ${localizedCategories.map(c => `
                <option value="${_escapeHtml(c.code)}" ${_promptsState.activeCategory === c.code ? 'selected' : ''}>
                  ${_escapeHtml(c.localizedName)} (${c.prompts_count || 0})
                </option>
              `).join('')}
            </select>
          </div>

          <div class="col-6 col-md-4 d-flex align-items-center justify-content-end gap-2">
            <select class="form-select form-select-sm" style="max-width: 140px;" onchange="window._promptLibSortChange(this.value)">
              <option value="favorites" ${_promptsState.sortBy === 'favorites' ? 'selected' : ''}>${_escapeHtml(_promptT('ai_prompt_sort_favorites', 'Favorites First'))}</option>
              <option value="recently_used" ${_promptsState.sortBy === 'recently_used' ? 'selected' : ''}>${_escapeHtml(_promptT('ai_prompt_sort_recently_used', 'Recently Used'))}</option>
              <option value="most_used" ${_promptsState.sortBy === 'most_used' ? 'selected' : ''}>${_escapeHtml(_promptT('ai_prompt_sort_most_used', 'Most Used'))}</option>
              <option value="name" ${_promptsState.sortBy === 'name' ? 'selected' : ''}>${_escapeHtml(_promptT('ai_prompt_sort_name', 'Alphabetical'))}</option>
            </select>

            <button type="button" class="btn btn-sm ${_promptsState.favoritesOnly ? 'btn-warning text-dark' : 'btn-outline-secondary'} d-inline-flex align-items-center gap-1"
              onclick="window._promptLibToggleFavoritesFilter()" title="${_escapeHtml(_promptT('ai_prompt_filter_fav_tooltip', 'Show Favorites Only'))}">
              <i class="bi ${_promptsState.favoritesOnly ? 'bi-star-fill' : 'bi-star'}"></i>
            </button>
          </div>
        </div>
      </div>

      <div class="row g-0 flex-grow-1" style="min-height: 440px;">
        <!-- Left Prompt List (Independent Scrollable Container) -->
        <div class="col-12 col-md-5 border-end d-flex flex-column" style="max-height: 480px; overflow-y: auto;">
          ${_promptsState.items.length === 0 ? `
            <div class="p-4 text-center text-muted my-auto">
              <i class="bi bi-inbox fs-2 d-block mb-2 text-secondary opacity-50"></i>
              <div class="fw-semibold" data-i18n="ai_prompt_no_results">${_escapeHtml(_promptT('ai_prompt_no_results', 'No prompts found'))}</div>
              <small class="text-secondary" data-i18n="ai_prompt_no_results_sub">${_escapeHtml(_promptT('ai_prompt_no_results_sub', 'Try adjusting your search query or filters.'))}</small>
            </div>
          ` : `
            <div class="list-group list-group-flush">
              ${_promptsState.items.map(rawP => {
                const p = _getLocalizedPrompt(rawP);
                const isSelected = _promptsState.selectedPrompt && _promptsState.selectedPrompt.id === p.id;
                return `
                  <div class="list-group-item list-group-item-action p-3 ${isSelected ? 'active bg-primary bg-opacity-10 border-primary-subtle' : ''}"
                    style="cursor: pointer;" onclick="window._promptLibSelectPrompt(${p.id})">
                    <div class="d-flex align-items-center justify-content-between mb-1" style="min-width: 0;">
                      <h6 class="mb-0 fw-semibold text-truncate text-body ${isSelected ? 'text-primary' : ''}"
                        style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: calc(100% - 24px);">${_escapeHtml(p.localizedName)}</h6>
                      <button type="button" class="btn btn-link p-0 text-decoration-none ms-2" onclick="event.stopPropagation(); window._promptLibToggleFavorite(${p.id})">
                        <i class="bi ${p.is_favorite ? 'bi-star-fill text-warning' : 'bi-star text-muted'} fs-6"></i>
                      </button>
                    </div>
                    <p class="small text-muted text-truncate mb-2" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;">${_escapeHtml(p.localizedDesc || p.localizedContent)}</p>
                    <div class="d-flex align-items-center justify-content-between gap-2">
                      <span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary-subtle font-monospace prompt-lib-cat-badge">
                        <i class="bi ${p.category?.icon || 'bi-folder'} me-1"></i>${_escapeHtml(p.localizedCatName)}
                      </span>
                      ${p.usage_count > 0 ? `
                        <small class="text-muted font-monospace text-nowrap" style="font-size:0.68rem;">
                          <i class="bi bi-arrow-repeat me-1"></i>${p.usage_count} ${_escapeHtml(_promptT('ai_prompt_uses_label', 'uses'))}
                        </small>
                      ` : ''}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          `}

          <!-- Pagination Footer -->
          ${_promptsState.totalPages > 1 ? `
            <div class="mt-auto p-2 border-top bg-body-tertiary d-flex align-items-center justify-content-between">
              <button class="btn btn-sm btn-outline-secondary" ${_promptsState.page <= 1 ? 'disabled' : ''} onclick="window._promptLibPageChange(${_promptsState.page - 1})">
                <i class="bi bi-chevron-left"></i>
              </button>
              <small class="text-muted font-monospace" style="font-size:0.75rem;">
                ${_promptsState.page} / ${_promptsState.totalPages}
              </small>
              <button class="btn btn-sm btn-outline-secondary" ${_promptsState.page >= _promptsState.totalPages ? 'disabled' : ''} onclick="window._promptLibPageChange(${_promptsState.page + 1})">
                <i class="bi bi-chevron-right"></i>
              </button>
            </div>
          ` : ''}
        </div>

        <!-- Right Prompt Details / Preview (Independent Scrollable Container) -->
        <div class="col-12 col-md-7 p-4 d-flex flex-column bg-body" style="max-height: 480px; overflow-y: auto;">
          ${_promptsState.selectedPrompt ? _renderPromptDetailPaneHtml(_getLocalizedPrompt(_promptsState.selectedPrompt)) : `
            <div class="text-center text-muted my-auto py-5">
              <i class="bi bi-chat-left-text fs-1 opacity-25 d-block mb-3"></i>
              <span data-i18n="ai_prompt_select_prompt_hint">${_escapeHtml(_promptT('ai_prompt_select_prompt_hint', 'Select a prompt from the list to preview details.'))}</span>
            </div>
          `}
        </div>
      </div>
    `;

    if (window._applyTranslations) {
      window._applyTranslations();
    }
  }

  function _renderPromptDetailPaneHtml(p) {
    const formattedDate = window.formatDate && p.updated_at ? window.formatDate(p.updated_at) : (p.updated_at ? p.updated_at.split('T')[0] : '');

    return `
      <div class="d-flex align-items-start justify-content-between mb-3 border-bottom pb-3">
        <div>
          <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
            <span class="badge bg-primary bg-opacity-10 text-primary border border-primary-subtle px-2 py-1 prompt-lib-cat-badge">
              <i class="bi ${p.category?.icon || 'bi-folder'} me-1"></i>${_escapeHtml(p.localizedCatName)}
            </span>
            ${p.is_favorite ? `
              <span class="badge bg-warning bg-opacity-20 text-dark px-2 py-1">
                <i class="bi bi-star-fill text-warning me-1"></i>${_escapeHtml(_promptT('ai_prompt_fav_badge', 'Favorite'))}
              </span>
            ` : ''}
          </div>
          <h5 class="fw-bold mb-1 text-body">${_escapeHtml(p.localizedName)}</h5>
          ${p.localizedDesc ? `<p class="text-muted small mb-0">${_escapeHtml(p.localizedDesc)}</p>` : ''}
        </div>

        <div class="d-flex align-items-center gap-1">
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibToggleFavorite(${p.id})" title="${_escapeHtml(_promptT('ai_prompt_fav_btn', 'Favorite'))}">
            <i class="bi ${p.is_favorite ? 'bi-star-fill text-warning' : 'bi-star'}"></i>
          </button>
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibDuplicatePrompt(${p.id})" title="${_escapeHtml(_promptT('ai_prompt_dup_btn', 'Duplicate'))}">
            <i class="bi bi-copy"></i>
          </button>
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibEditForm(${p.id})" title="${_escapeHtml(_promptT('ai_prompt_edit_btn', 'Edit'))}">
            <i class="bi bi-pencil"></i>
          </button>
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="window._promptLibDeletePrompt(${p.id})" title="${_escapeHtml(_promptT('ai_prompt_delete_btn', 'Delete'))}">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>

      <!-- Prompt Text Content Box preserving formatting -->
      <div class="mb-3 flex-grow-1">
        <label class="form-label font-monospace text-muted small mb-1" data-i18n="ai_prompt_content_label">${_escapeHtml(_promptT('ai_prompt_content_label', 'Prompt Template Content:'))}</label>
        <div class="p-3 rounded border bg-body-tertiary text-body font-monospace"
          style="white-space: pre-wrap; word-break: break-word; font-size: 0.88rem; max-height: 240px; overflow-y: auto;">${_escapeHtml(p.localizedContent)}</div>
      </div>

      <div class="d-flex align-items-center justify-content-between pt-2 border-top">
        <small class="text-muted font-monospace" style="font-size:0.75rem;">
          ${formattedDate ? `<i class="bi bi-clock-history me-1"></i>${formattedDate}` : ''}
        </small>
        <button type="button" class="btn btn-primary px-4 d-inline-flex align-items-center gap-2" onclick="window._promptLibInsertPrompt(${p.id})">
          <i class="bi bi-box-arrow-in-down-left"></i>
          <span data-i18n="ai_prompt_insert_btn">${_escapeHtml(_promptT('ai_prompt_insert_btn', 'Insert Prompt'))}</span>
        </button>
      </div>
    `;
  }

  function _renderFormHtml() {
    const isEdit = !!_promptsState.editingPromptId;
    const rawP = isEdit ? _promptsState.selectedPrompt : { name: '', content: '', description: '', category_code: _promptsState.activeCategory !== 'all' ? _promptsState.activeCategory : 'general', is_favorite: false };
    const p = _getLocalizedPrompt(rawP);
    const localizedCategories = _promptsState.categories.map(_getLocalizedCategory);

    return `
      <div class="p-4">
        <div class="d-flex align-items-center justify-content-between mb-3 pb-2 border-bottom">
          <h6 class="fw-bold mb-0 text-body">
            <i class="bi ${isEdit ? 'bi-pencil-square' : 'bi-plus-circle'} me-2 text-primary"></i>
            ${isEdit ? _escapeHtml(_promptT('ai_prompt_edit_title', 'Edit Prompt')) : _escapeHtml(_promptT('ai_prompt_create_title', 'Create New Prompt'))}
          </h6>
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibCancelForm()">
            <i class="bi bi-x-lg me-1"></i>${_escapeHtml(_promptT('btn_cancel', 'Cancel'))}
          </button>
        </div>

        <form id="prompt-editor-form" onsubmit="window._promptLibSaveForm(event)">
          <div id="prompt-form-error-alert" class="alert alert-danger d-none py-2 px-3 mb-3 small"></div>

          <div class="row g-3">
            <div class="col-12 col-md-8">
              <label class="form-label small fw-semibold text-body" data-i18n="ai_prompt_field_name">${_escapeHtml(_promptT('ai_prompt_field_name', 'Prompt Name *'))}</label>
              <input type="text" class="form-control form-control-sm" id="prompt-field-name" required max-length="255"
                placeholder="${_escapeHtml(_promptT('ai_prompt_name_placeholder', 'e.g. Monthly Wealth Audit'))}"
                value="${_escapeHtml(p ? p.localizedName : '')}">
            </div>

            <div class="col-12 col-md-4">
              <label class="form-label small fw-semibold text-body" data-i18n="ai_prompt_field_category">${_escapeHtml(_promptT('ai_prompt_field_category', 'Category *'))}</label>
              <select class="form-select form-select-sm" id="prompt-field-category" required>
                ${localizedCategories.map(c => `
                  <option value="${_escapeHtml(c.code)}" ${p && (p.category_code === c.code || p.category?.code === c.code) ? 'selected' : ''}>
                    ${_escapeHtml(c.localizedName)}
                  </option>
                `).join('')}
              </select>
            </div>

            <div class="col-12">
              <label class="form-label small fw-semibold text-body" data-i18n="ai_prompt_field_description">${_escapeHtml(_promptT('ai_prompt_field_description', 'Short Description (Optional)'))}</label>
              <input type="text" class="form-control form-control-sm" id="prompt-field-description"
                placeholder="${_escapeHtml(_promptT('ai_prompt_desc_placeholder', 'Brief summary of what this prompt is used for'))}"
                value="${_escapeHtml(p ? p.localizedDesc : '')}">
            </div>

            <div class="col-12">
              <label class="form-label small fw-semibold text-body" data-i18n="ai_prompt_field_content">${_escapeHtml(_promptT('ai_prompt_field_content', 'Prompt Content *'))}</label>
              <textarea class="form-control form-control-sm font-monospace" id="prompt-field-content" rows="6" required
                placeholder="${_escapeHtml(_promptT('ai_prompt_content_placeholder', 'Enter the reusable prompt text here...'))}">${_escapeHtml(p ? p.localizedContent : '')}</textarea>
            </div>

            <div class="col-12 d-flex align-items-center justify-content-between pt-2">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="prompt-field-favorite" ${p && p.is_favorite ? 'checked' : ''}>
                <label class="form-check-label small text-body" for="prompt-field-favorite" data-i18n="ai_prompt_field_favorite">
                  ${_escapeHtml(_promptT('ai_prompt_field_favorite', 'Mark as Favorite'))}
                </label>
              </div>

              <div class="d-flex align-items-center gap-2">
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibCancelForm()">
                  ${_escapeHtml(_promptT('btn_cancel', 'Cancel'))}
                </button>
                <button type="submit" class="btn btn-sm btn-primary px-3" id="prompt-save-btn">
                  <i class="bi bi-check-lg me-1"></i>
                  ${isEdit ? _escapeHtml(_promptT('btn_save', 'Save Changes')) : _escapeHtml(_promptT('ai_prompt_create_submit', 'Create Prompt'))}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    `;
  }

  // Event handlers & actions
  function _promptLibSearchInput(query) {
    _promptsState.searchQuery = query;
    _promptsState.page = 1;
    if (_promptsState.searchDebounceTimer) clearTimeout(_promptsState.searchDebounceTimer);
    _promptsState.searchDebounceTimer = setTimeout(() => {
      _fetchPrompts();
    }, 250);
  }

  function _promptLibClearSearch() {
    _promptsState.searchQuery = '';
    _promptsState.page = 1;
    _fetchPrompts();
  }

  function _promptLibCategoryChange(catCode) {
    _promptsState.activeCategory = catCode;
    _promptsState.page = 1;
    _fetchPrompts();
  }

  function _promptLibSortChange(sortBy) {
    _promptsState.sortBy = sortBy;
    _promptsState.page = 1;
    _fetchPrompts();
  }

  function _promptLibToggleFavoritesFilter() {
    _promptsState.favoritesOnly = !_promptsState.favoritesOnly;
    _promptsState.page = 1;
    _fetchPrompts();
  }

  function _promptLibSelectPrompt(promptId) {
    const found = _promptsState.items.find(p => p.id === promptId);
    if (found) {
      _promptsState.selectedPrompt = found;
      _renderModalContent();
    }
  }

  function _promptLibPageChange(newPage) {
    if (newPage >= 1 && newPage <= _promptsState.totalPages) {
      _promptsState.page = newPage;
      _fetchPrompts();
    }
  }

  // Optimistic UI for Favorite Toggle
  async function _promptLibToggleFavorite(promptId) {
    const target = _promptsState.items.find(p => p.id === promptId);
    if (target) {
      target.is_favorite = !target.is_favorite;
      if (_promptsState.selectedPrompt && _promptsState.selectedPrompt.id === promptId) {
        _promptsState.selectedPrompt.is_favorite = target.is_favorite;
      }
      _renderModalContent();
    }

    try {
      const res = await fetch(`/api/ai-platform/prompts/${promptId}/favorite/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.prompt) {
          const index = _promptsState.items.findIndex(p => p.id === promptId);
          if (index !== -1) {
            _promptsState.items[index] = data.prompt;
          }
          if (_promptsState.selectedPrompt && _promptsState.selectedPrompt.id === promptId) {
            _promptsState.selectedPrompt = data.prompt;
          }
          _renderModalContent();
        }
      }
    } catch (e) {
      console.error('Failed to toggle favorite', e);
    }
  }

  // Optimistic UI for Soft Delete
  async function _promptLibDeletePrompt(promptId) {
    const target = _promptsState.items.find(p => p.id === promptId);
    const confirmMsg = _promptT('ai_prompt_confirm_delete', 'Are you sure you want to delete this prompt?');
    if (!confirm(confirmMsg)) return;

    // Optimistic removal from state
    _promptsState.items = _promptsState.items.filter(p => p.id !== promptId);
    _promptsState.total = Math.max(0, _promptsState.total - 1);

    if (_promptsState.selectedPrompt && _promptsState.selectedPrompt.id === promptId) {
      _promptsState.selectedPrompt = _promptsState.items.length > 0 ? _promptsState.items[0] : null;
    }
    _renderModalContent();

    try {
      const res = await fetch(`/api/ai-platform/prompts/${promptId}/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        },
      });
      if (!res.ok) {
        // Revert on error
        await _fetchPrompts();
      }
    } catch (e) {
      console.error('Failed to delete prompt', e);
      await _fetchPrompts();
    }
  }

  // Optimistic UI for Duplicate
  async function _promptLibDuplicatePrompt(promptId) {
    try {
      const res = await fetch(`/api/ai-platform/prompts/${promptId}/duplicate/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.prompt) {
          _promptsState.items.unshift(data.prompt);
          _promptsState.selectedPrompt = data.prompt;
          _promptsState.total += 1;
          _renderModalContent();
        }
      }
    } catch (e) {
      console.error('Failed to duplicate prompt', e);
    }
  }

  // Form toggle
  function _promptLibNewForm() {
    _promptsState.isFormOpen = true;
    _promptsState.editingPromptId = null;
    _renderModalContent();
  }

  function _promptLibEditForm(promptId) {
    _promptsState.isFormOpen = true;
    _promptsState.editingPromptId = promptId;
    _renderModalContent();
  }

  function _promptLibCancelForm() {
    _promptsState.isFormOpen = false;
    _promptsState.editingPromptId = null;
    _renderModalContent();
  }

  async function _promptLibSaveForm(event) {
    event.preventDefault();
    const errAlert = document.getElementById('prompt-form-error-alert');
    if (errAlert) errAlert.classList.add('d-none');

    const name = document.getElementById('prompt-field-name')?.value.trim();
    const catCode = document.getElementById('prompt-field-category')?.value;
    const description = document.getElementById('prompt-field-description')?.value.trim();
    const content = document.getElementById('prompt-field-content')?.value; // EXACT whitespace & markdown preserved
    const isFavorite = document.getElementById('prompt-field-favorite')?.checked;

    if (!name || !content) {
      if (errAlert) {
        errAlert.textContent = _promptT('ai_prompt_err_required', 'Name and content are required.');
        errAlert.classList.remove('d-none');
      }
      return;
    }

    const payload = {
      name: name,
      category_code: catCode,
      description: description,
      content: content,
      is_favorite: isFavorite,
    };

    const isEdit = !!_promptsState.editingPromptId;
    const url = isEdit ? `/api/ai-platform/prompts/${_promptsState.editingPromptId}/` : '/api/ai-platform/prompts/';
    const method = isEdit ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok && data.prompt) {
        _promptsState.isFormOpen = false;
        _promptsState.editingPromptId = null;
        _promptsState.selectedPrompt = data.prompt;
        await _fetchPrompts();
      } else {
        if (errAlert) {
          const detailMsg = data.details?.name || data.details?.content || data.error || _promptT('ai_prompt_err_save', 'Failed to save prompt.');
          errAlert.textContent = detailMsg;
          errAlert.classList.remove('d-none');
        }
      }
    } catch (e) {
      if (errAlert) {
        errAlert.textContent = _promptT('ai_prompt_err_save', 'Network error occurred while saving prompt.');
        errAlert.classList.remove('d-none');
      }
    }
  }

  // Exact formatting preservation insertion into #ai-ws-input
  async function _promptLibInsertPrompt(promptId) {
    const rawP = _promptsState.items.find(p => p.id === promptId) || _promptsState.selectedPrompt;
    const promptObj = _getLocalizedPrompt(rawP);
    if (!promptObj) return;

    const textarea = document.getElementById('ai-ws-input');
    if (textarea) {
      // PRESERVE exact line breaks, Markdown formatting, and whitespace!
      textarea.value = promptObj.localizedContent;
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';
      textarea.focus();
    }

    // Record usage asynchronously in backend
    try {
      fetch(`/api/ai-platform/prompts/${promptId}/use/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        },
      });
    } catch (e) {
      // Silent error
    }

    closeModal();
  }

  // Expose global methods
  window.openPromptLibraryModal = openPromptLibraryModal;
  window._promptLibSearchInput = _promptLibSearchInput;
  window._promptLibClearSearch = _promptLibClearSearch;
  window._promptLibCategoryChange = _promptLibCategoryChange;
  window._promptLibSortChange = _promptLibSortChange;
  window._promptLibToggleFavoritesFilter = _promptLibToggleFavoritesFilter;
  window._promptLibSelectPrompt = _promptLibSelectPrompt;
  window._promptLibPageChange = _promptLibPageChange;
  window._promptLibToggleFavorite = _promptLibToggleFavorite;
  window._promptLibDeletePrompt = _promptLibDeletePrompt;
  window._promptLibDuplicatePrompt = _promptLibDuplicatePrompt;
  window._promptLibNewForm = _promptLibNewForm;
  window._promptLibEditForm = _promptLibEditForm;
  window._promptLibCancelForm = _promptLibCancelForm;
  window._promptLibSaveForm = _promptLibSaveForm;
  window._promptLibInsertPrompt = _promptLibInsertPrompt;
})();
