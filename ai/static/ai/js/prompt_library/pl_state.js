/**
 * WealthFlow AI Workspace - Prompt Library: State, Helpers & API
 * Shared state object, translation/escape/localization helpers, and all
 * fetch() calls against /api/ai-platform/prompts/.
 * Depended on by pl_render.js and pl_events.js.
 */

"use strict";

window.PromptLib = window.PromptLib || {};

window.PromptLib.state = {
  categories: [],
  items: [],
  selectedPrompt: null,
  activeCategory: "all",
  searchQuery: "",
  favoritesOnly: false,
  sortBy: "favorites",
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 1,
  isFormOpen: false,
  editingPromptId: null,
  searchDebounceTimer: null,
};

window.PromptLib.t = function (key, fallback) {
  if (window.t) {
    const translated = window.t(key);
    if (translated && translated !== key) return translated;
  }
  return fallback;
};

window.PromptLib.escapeHtml = function (str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
};

window.PromptLib.getLocalizedCategory = function (c) {
  if (!c) return { name: "", description: "", code: "" };
  const t = window.PromptLib.t;
  const nameKey = `ai_prompt_cat_${c.code}_name`;
  const descKey = `ai_prompt_cat_${c.code}_desc`;
  const locName = t(nameKey, c.name);
  const locDesc = t(descKey, c.description);
  return {
    ...c,
    localizedName: locName,
    localizedDesc: locDesc,
  };
};

window.PromptLib.getLocalizedPrompt = function (p) {
  if (!p) return null;
  const t = window.PromptLib.t;
  let locName = p.name;
  let locDesc = p.description;
  let locContent = p.content;

  if (p.translation_key) {
    const nameKey = `ai_prompt_seed_${p.translation_key}_name`;
    const descKey = `ai_prompt_seed_${p.translation_key}_desc`;
    const contentKey = `ai_prompt_seed_${p.translation_key}_content`;

    locName = t(nameKey, p.name);
    locDesc = t(descKey, p.description);
    locContent = t(contentKey, p.content);
  }

  const catObj = p.category ? window.PromptLib.getLocalizedCategory(p.category) : null;
  const catName = catObj ? catObj.localizedName : p.category_name || p.category_code || "";

  return {
    ...p,
    localizedName: locName,
    localizedDesc: locDesc,
    localizedContent: locContent,
    localizedCatName: catName,
  };
};

window.PromptLib.loadCategoriesAndPrompts = async function () {
  const state = window.PromptLib.state;
  try {
    const catRes = await fetch("/api/ai-platform/prompts/categories/");
    if (catRes.ok) {
      const catData = await catRes.json();
      state.categories = catData.categories || [];
    }
  } catch (e) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }
  await window.PromptLib.fetchPrompts();
};

window.PromptLib.fetchPrompts = async function () {
  const state = window.PromptLib.state;
  const params = new URLSearchParams();
  if (state.activeCategory && state.activeCategory !== "all") {
    params.append("category_code", state.activeCategory);
  }
  if (state.searchQuery) {
    params.append("search", state.searchQuery);
  }
  if (state.favoritesOnly) {
    params.append("favorites_only", "true");
  }
  params.append("sort_by", state.sortBy);
  params.append("page", state.page);
  params.append("page_size", state.pageSize);

  try {
    const res = await fetch(`/api/ai-platform/prompts/?${params.toString()}`);
    if (res.ok) {
      const data = await res.json();
      state.items = data.items || [];
      state.total = data.total || 0;
      state.page = data.page || 1;
      state.totalPages = data.total_pages || 1;

      if (state.selectedPrompt) {
        const updated = state.items.find((p) => p.id === state.selectedPrompt.id);
        if (updated) {
          state.selectedPrompt = updated;
        } else if (state.items.length > 0) {
          state.selectedPrompt = state.items[0];
        } else {
          state.selectedPrompt = null;
        }
      } else if (state.items.length > 0) {
        state.selectedPrompt = state.items[0];
      } else {
        state.selectedPrompt = null;
      }
    }
  } catch (err) {
    // Non-fatal: error already surfaced to the user via UI feedback.
  }

  window.PromptLib.renderModalContent();
};
