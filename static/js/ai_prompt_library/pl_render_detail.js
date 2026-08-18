/**
 * WealthFlow AI Workspace - Prompt Library: Detail Pane & Form Rendering
 * Right-hand prompt preview pane and the create/edit prompt form.
 * Depends on: pl_state.js
 */

'use strict';

window.PromptLib = window.PromptLib || {};

window.PromptLib.renderPromptDetailPaneHtml = function (p) {
  const t = window.PromptLib.t;
  const esc = window.PromptLib.escapeHtml;
  const formattedDate = window.formatDate && p.updated_at ? window.formatDate(p.updated_at) : (p.updated_at ? p.updated_at.split('T')[0] : '');

  return `
    <div class="d-flex align-items-start justify-content-between mb-3 border-bottom pb-3">
      <div>
        <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
          <span class="badge bg-primary bg-opacity-10 text-primary border border-primary-subtle px-2 py-1 prompt-lib-cat-badge">
            <i class="bi ${p.category?.icon || 'bi-folder'} me-1"></i>${esc(p.localizedCatName)}
          </span>
          ${p.is_favorite ? `
            <span class="badge bg-warning bg-opacity-20 text-dark px-2 py-1">
              <i class="bi bi-star-fill text-warning me-1"></i>${esc(t('ai_prompt_fav_badge', 'Favorite'))}
            </span>
          ` : ''}
        </div>
        <h5 class="fw-bold mb-1 text-body">${esc(p.localizedName)}</h5>
        ${p.localizedDesc ? `<p class="text-muted small mb-0">${esc(p.localizedDesc)}</p>` : ''}
      </div>

      <div class="d-flex align-items-center gap-1">
        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibToggleFavorite(${p.id})" title="${esc(t('ai_prompt_fav_btn', 'Favorite'))}">
          <i class="bi ${p.is_favorite ? 'bi-star-fill text-warning' : 'bi-star'}"></i>
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibDuplicatePrompt(${p.id})" title="${esc(t('ai_prompt_dup_btn', 'Duplicate'))}">
          <i class="bi bi-copy"></i>
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibEditForm(${p.id})" title="${esc(t('ai_prompt_edit_btn', 'Edit'))}">
          <i class="bi bi-pencil"></i>
        </button>
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="window._promptLibDeletePrompt(${p.id})" title="${esc(t('ai_prompt_delete_btn', 'Delete'))}">
          <i class="bi bi-trash"></i>
        </button>
      </div>
    </div>

    <!-- Prompt Text Content Box preserving formatting -->
    <div class="mb-3 flex-grow-1">
      <label class="form-label font-monospace text-muted small mb-1" data-i18n="ai_prompt_content_label">${esc(t('ai_prompt_content_label', 'Prompt Template Content:'))}</label>
      <div class="p-3 rounded border bg-body-tertiary text-body font-monospace"
        style="white-space: pre-wrap; word-break: break-word; font-size: 0.88rem; max-height: 240px; overflow-y: auto;">${esc(p.localizedContent)}</div>
    </div>

    <div class="d-flex align-items-center justify-content-between pt-2 border-top">
      <small class="text-muted font-monospace" style="font-size:0.75rem;">
        ${formattedDate ? `<i class="bi bi-clock-history me-1"></i>${formattedDate}` : ''}
      </small>
      <button type="button" class="btn btn-primary px-4 d-inline-flex align-items-center gap-2" onclick="window._promptLibInsertPrompt(${p.id})">
        <i class="bi bi-box-arrow-in-down-left"></i>
        <span data-i18n="ai_prompt_insert_btn">${esc(t('ai_prompt_insert_btn', 'Insert Prompt'))}</span>
      </button>
    </div>
  `;
};

window.PromptLib.renderFormHtml = function () {
  const state = window.PromptLib.state;
  const t = window.PromptLib.t;
  const esc = window.PromptLib.escapeHtml;
  const isEdit = !!state.editingPromptId;
  const rawP = isEdit ? state.selectedPrompt : { name: '', content: '', description: '', category_code: state.activeCategory !== 'all' ? state.activeCategory : 'general', is_favorite: false };
  const p = window.PromptLib.getLocalizedPrompt(rawP);
  const localizedCategories = state.categories.map(window.PromptLib.getLocalizedCategory);

  return `
    <div class="p-4">
      <div class="d-flex align-items-center justify-content-between mb-3 pb-2 border-bottom">
        <h6 class="fw-bold mb-0 text-body">
          <i class="bi ${isEdit ? 'bi-pencil-square' : 'bi-plus-circle'} me-2 text-primary"></i>
          ${isEdit ? esc(t('ai_prompt_edit_title', 'Edit Prompt')) : esc(t('ai_prompt_create_title', 'Create New Prompt'))}
        </h6>
        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibCancelForm()">
          <i class="bi bi-x-lg me-1"></i>${esc(t('btn_cancel', 'Cancel'))}
        </button>
      </div>

      <form id="prompt-editor-form" onsubmit="window._promptLibSaveForm(event)">
        <div id="prompt-form-error-alert" class="alert alert-danger d-none py-2 px-3 mb-3 small"></div>

        <div class="row g-3">
          <div class="col-12 col-md-8">
            <label class="form-label small fw-semibold text-body" data-i18n="ai_prompt_field_name">${esc(t('ai_prompt_field_name', 'Prompt Name *'))}</label>
            <input type="text" class="form-control form-control-sm" id="prompt-field-name" required max-length="255"
              placeholder="${esc(t('ai_prompt_name_placeholder', 'e.g. Monthly Wealth Audit'))}"
              value="${esc(p ? p.localizedName : '')}">
          </div>

          <div class="col-12 col-md-4">
            <label class="form-label small fw-semibold text-body" data-i18n="ai_prompt_field_category">${esc(t('ai_prompt_field_category', 'Category *'))}</label>
            <select class="form-select form-select-sm" id="prompt-field-category" required>
              ${localizedCategories.map(c => `
                <option value="${esc(c.code)}" ${p && (p.category_code === c.code || p.category?.code === c.code) ? 'selected' : ''}>
                  ${esc(c.localizedName)}
                </option>
              `).join('')}
            </select>
          </div>

          <div class="col-12">
            <label class="form-label small fw-semibold text-body" data-i18n="ai_prompt_field_description">${esc(t('ai_prompt_field_description', 'Short Description (Optional)'))}</label>
            <input type="text" class="form-control form-control-sm" id="prompt-field-description"
              placeholder="${esc(t('ai_prompt_desc_placeholder', 'Brief summary of what this prompt is used for'))}"
              value="${esc(p ? p.localizedDesc : '')}">
          </div>

          <div class="col-12">
            <label class="form-label small fw-semibold text-body" data-i18n="ai_prompt_field_content">${esc(t('ai_prompt_field_content', 'Prompt Content *'))}</label>
            <textarea class="form-control form-control-sm font-monospace" id="prompt-field-content" rows="6" required
              placeholder="${esc(t('ai_prompt_content_placeholder', 'Enter the reusable prompt text here...'))}">${esc(p ? p.localizedContent : '')}</textarea>
          </div>

          <div class="col-12 d-flex align-items-center justify-content-between pt-2">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" id="prompt-field-favorite" ${p && p.is_favorite ? 'checked' : ''}>
              <label class="form-check-label small text-body" for="prompt-field-favorite" data-i18n="ai_prompt_field_favorite">
                ${esc(t('ai_prompt_field_favorite', 'Mark as Favorite'))}
              </label>
            </div>

            <div class="d-flex align-items-center gap-2">
              <button type="button" class="btn btn-sm btn-outline-secondary" onclick="window._promptLibCancelForm()">
                ${esc(t('btn_cancel', 'Cancel'))}
              </button>
              <button type="submit" class="btn btn-sm btn-primary px-3" id="prompt-save-btn">
                <i class="bi bi-check-lg me-1"></i>
                ${isEdit ? esc(t('btn_save', 'Save Changes')) : esc(t('ai_prompt_create_submit', 'Create Prompt'))}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  `;
};
