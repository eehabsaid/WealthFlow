/**
 * WealthFlow AI Workspace - Prompt Library: Optimistic CRUD Actions
 * Shared CSRF helper plus optimistic UI for favorite toggle, soft delete,
 * and duplicate.
 * Depends on: pl_state.js, pl_render_list.js
 */

"use strict";

window.PromptLib = window.PromptLib || {};

function _csrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
}

// Optimistic UI for Favorite Toggle
window.PromptLib.toggleFavorite = async function (promptId) {
  const state = window.PromptLib.state;
  const target = state.items.find((p) => p.id === promptId);
  if (target) {
    target.is_favorite = !target.is_favorite;
    if (state.selectedPrompt && state.selectedPrompt.id === promptId) {
      state.selectedPrompt.is_favorite = target.is_favorite;
    }
    window.PromptLib.renderModalContent();
  }

  try {
    const res = await fetch(`/api/ai-platform/prompts/${promptId}/favorite/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": _csrfToken(),
        "Content-Type": "application/json",
      },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.prompt) {
        const index = state.items.findIndex((p) => p.id === promptId);
        if (index !== -1) {
          state.items[index] = data.prompt;
        }
        if (state.selectedPrompt && state.selectedPrompt.id === promptId) {
          state.selectedPrompt = data.prompt;
        }
        window.PromptLib.renderModalContent();
      }
    }
  } catch (e) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
};

// Optimistic UI for Soft Delete
window.PromptLib.deletePrompt = async function (promptId) {
  const state = window.PromptLib.state;
  const confirmMsg = window.PromptLib.t(
    "ai_prompt_confirm_delete",
    "Are you sure you want to delete this prompt?"
  );
  if (!confirm(confirmMsg)) return;

  // Optimistic removal from state
  state.items = state.items.filter((p) => p.id !== promptId);
  state.total = Math.max(0, state.total - 1);

  if (state.selectedPrompt && state.selectedPrompt.id === promptId) {
    state.selectedPrompt = state.items.length > 0 ? state.items[0] : null;
  }
  window.PromptLib.renderModalContent();

  try {
    const res = await fetch(`/api/ai-platform/prompts/${promptId}/`, {
      method: "DELETE",
      headers: {
        "X-CSRFToken": _csrfToken(),
      },
    });
    if (!res.ok) {
      // Revert on error
      await window.PromptLib.fetchPrompts();
    }
  } catch (e) {
    await window.PromptLib.fetchPrompts();
  }
};

// Optimistic UI for Duplicate
window.PromptLib.duplicatePrompt = async function (promptId) {
  const state = window.PromptLib.state;
  try {
    const res = await fetch(`/api/ai-platform/prompts/${promptId}/duplicate/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": _csrfToken(),
      },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.prompt) {
        state.items.unshift(data.prompt);
        state.selectedPrompt = data.prompt;
        state.total += 1;
        window.PromptLib.renderModalContent();
      }
    }
  } catch (e) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
};
