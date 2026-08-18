/**
 * WealthFlow AI Workspace - Prompt Library: Form Save & Insert Actions
 * Form save (create/update) and inserting prompt content into the AI
 * Workspace input.
 * Depends on: pl_state.js, pl_render_list.js, pl_actions_optimistic.js (for _csrfToken)
 */

'use strict';

window.PromptLib = window.PromptLib || {};

window.PromptLib.saveForm = async function (event) {
  event.preventDefault();
  const state = window.PromptLib.state;
  const t = window.PromptLib.t;
  const errAlert = document.getElementById('prompt-form-error-alert');
  if (errAlert) errAlert.classList.add('d-none');

  const name = document.getElementById('prompt-field-name')?.value.trim();
  const catCode = document.getElementById('prompt-field-category')?.value;
  const description = document.getElementById('prompt-field-description')?.value.trim();
  const content = document.getElementById('prompt-field-content')?.value; // EXACT whitespace & markdown preserved
  const isFavorite = document.getElementById('prompt-field-favorite')?.checked;

  if (!name || !content) {
    if (errAlert) {
      errAlert.textContent = t('ai_prompt_err_required', 'Name and content are required.');
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

  const isEdit = !!state.editingPromptId;
  const url = isEdit ? `/api/ai-platform/prompts/${state.editingPromptId}/` : '/api/ai-platform/prompts/';
  const method = isEdit ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': _csrfToken(),
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (res.ok && data.prompt) {
      state.isFormOpen = false;
      state.editingPromptId = null;
      state.selectedPrompt = data.prompt;
      await window.PromptLib.fetchPrompts();
    } else {
      if (errAlert) {
        const detailMsg = data.details?.name || data.details?.content || data.error || t('ai_prompt_err_save', 'Failed to save prompt.');
        errAlert.textContent = detailMsg;
        errAlert.classList.remove('d-none');
      }
    }
  } catch (e) {
    if (errAlert) {
      errAlert.textContent = t('ai_prompt_err_save', 'Network error occurred while saving prompt.');
      errAlert.classList.remove('d-none');
    }
  }
};

// Exact formatting preservation insertion into #ai-ws-input
window.PromptLib.insertPrompt = async function (promptId) {
  const state = window.PromptLib.state;
  const rawP = state.items.find(p => p.id === promptId) || state.selectedPrompt;
  const promptObj = window.PromptLib.getLocalizedPrompt(rawP);
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
        'X-CSRFToken': _csrfToken(),
      },
    });
  } catch (e) {
    // Silent error
  }

  closeModal();
};
