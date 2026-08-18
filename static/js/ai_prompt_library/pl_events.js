/**
 * WealthFlow AI Workspace - Prompt Library: Entry Point & Event Handlers
 * Public modal-open function, filter/search/sort/pagination/form-toggle
 * handlers, and global window.* exposure wired to onclick attributes.
 * Depends on: pl_state.js, pl_render_list.js, pl_render_detail.js, pl_actions.js
 */

'use strict';

window.PromptLib = window.PromptLib || {};

window.openPromptLibraryModal = function () {
  let container = document.getElementById('modal-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'modal-container';
    document.body.appendChild(container);
  }

  const state = window.PromptLib.state;
  state.isFormOpen = false;
  state.editingPromptId = null;
  state.page = 1;

  showModal(window.PromptLib.renderModalShellHtml());
  window.PromptLib.loadCategoriesAndPrompts();
};

// Event handlers & actions
function _promptLibSearchInput(query) {
  const state = window.PromptLib.state;
  state.searchQuery = query;
  state.page = 1;
  if (state.searchDebounceTimer) clearTimeout(state.searchDebounceTimer);
  state.searchDebounceTimer = setTimeout(() => {
    window.PromptLib.fetchPrompts();
  }, 250);
}

function _promptLibClearSearch() {
  const state = window.PromptLib.state;
  state.searchQuery = '';
  state.page = 1;
  window.PromptLib.fetchPrompts();
}

function _promptLibCategoryChange(catCode) {
  const state = window.PromptLib.state;
  state.activeCategory = catCode;
  state.page = 1;
  window.PromptLib.fetchPrompts();
}

function _promptLibSortChange(sortBy) {
  const state = window.PromptLib.state;
  state.sortBy = sortBy;
  state.page = 1;
  window.PromptLib.fetchPrompts();
}

function _promptLibToggleFavoritesFilter() {
  const state = window.PromptLib.state;
  state.favoritesOnly = !state.favoritesOnly;
  state.page = 1;
  window.PromptLib.fetchPrompts();
}

function _promptLibSelectPrompt(promptId) {
  const state = window.PromptLib.state;
  const found = state.items.find(p => p.id === promptId);
  if (found) {
    state.selectedPrompt = found;
    window.PromptLib.renderModalContent();
  }
}

function _promptLibPageChange(newPage) {
  const state = window.PromptLib.state;
  if (newPage >= 1 && newPage <= state.totalPages) {
    state.page = newPage;
    window.PromptLib.fetchPrompts();
  }
}

// Form toggle
function _promptLibNewForm() {
  const state = window.PromptLib.state;
  state.isFormOpen = true;
  state.editingPromptId = null;
  window.PromptLib.renderModalContent();
}

function _promptLibEditForm(promptId) {
  const state = window.PromptLib.state;
  state.isFormOpen = true;
  state.editingPromptId = promptId;
  window.PromptLib.renderModalContent();
}

function _promptLibCancelForm() {
  const state = window.PromptLib.state;
  state.isFormOpen = false;
  state.editingPromptId = null;
  window.PromptLib.renderModalContent();
}

// Expose global methods
window._promptLibSearchInput = _promptLibSearchInput;
window._promptLibClearSearch = _promptLibClearSearch;
window._promptLibCategoryChange = _promptLibCategoryChange;
window._promptLibSortChange = _promptLibSortChange;
window._promptLibToggleFavoritesFilter = _promptLibToggleFavoritesFilter;
window._promptLibSelectPrompt = _promptLibSelectPrompt;
window._promptLibPageChange = _promptLibPageChange;
window._promptLibToggleFavorite = window.PromptLib.toggleFavorite;
window._promptLibDeletePrompt = window.PromptLib.deletePrompt;
window._promptLibDuplicatePrompt = window.PromptLib.duplicatePrompt;
window._promptLibNewForm = _promptLibNewForm;
window._promptLibEditForm = _promptLibEditForm;
window._promptLibCancelForm = _promptLibCancelForm;
window._promptLibSaveForm = window.PromptLib.saveForm;
window._promptLibInsertPrompt = window.PromptLib.insertPrompt;
