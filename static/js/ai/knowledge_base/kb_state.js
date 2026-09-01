/**
 * WealthFlow AI Workspace - Knowledge Base: State & API
 * Shared state object, category metadata, translation/escape helpers,
 * and all fetch() calls against /api/ai-platform/knowledge/.
 */

"use strict";

window.KB = window.KB || {};

window.KB.state = {
  entries: [],
  activeCategory: "all",
  loading: false,
  scanning: false,
  isFormOpen: false,
  scanResult: null,
};

window.KB.CATEGORIES = [
  { code: "all", i18n: "ai_kb_cat_all", fallback: "All" },
  { code: "business_rule", i18n: "ai_kb_cat_business_rule", fallback: "Business Rule" },
  {
    code: "codebase_architecture",
    i18n: "ai_kb_cat_codebase",
    fallback: "Codebase & Architecture",
  },
  { code: "user_preference", i18n: "ai_kb_cat_preference", fallback: "User Preference" },
  { code: "app_evolution", i18n: "ai_kb_cat_evolution", fallback: "App Evolution" },
];

window.KB.t = function (key, fallback) {
  if (window.t) {
    const translated = window.t(key);
    if (translated && translated !== key) return translated;
  }
  return fallback;
};

window.KB.escapeHtml = function (str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
};

window.KB.csrfToken = function () {
  return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
};

window.KB.loadEntries = async function () {
  const state = window.KB.state;
  state.loading = true;
  window.KB.renderBody();
  try {
    const category =
      state.activeCategory === "all" ? "" : `?category=${encodeURIComponent(state.activeCategory)}`;
    const res = await fetch(`/api/ai-platform/knowledge/${category}`);
    if (res.ok) {
      const data = await res.json();
      state.entries = data.entries || [];
    } else {
      state.entries = [];
    }
  } catch (_e) {
    state.entries = [];
  } finally {
    state.loading = false;
    window.KB.renderBody();
  }
};

window.KB.triggerScan = async function () {
  const state = window.KB.state;
  if (state.scanning) return;
  state.scanning = true;
  const btn = document.getElementById("kb-scan-btn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${window.KB.escapeHtml(window.KB.t("ai_kb_scanning", "Scanning..."))}`;
  }
  try {
    const res = await fetch("/api/ai-platform/knowledge/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.KB.csrfToken(),
      },
      body: JSON.stringify({ action: "scan" }),
    });
    state.scanResult = res.ok ? await res.json() : { ok: false, error: true };
  } catch (_e) {
    state.scanResult = { ok: false, error: true };
  } finally {
    state.scanning = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-radar"></i> <span data-i18n="ai_kb_scan_btn">${window.KB.escapeHtml(window.KB.t("ai_kb_scan_btn", "Run Autonomous Scan"))}</span>`;
    }
    await window.KB.loadEntries();
  }
};

window.KB.submitForm = async function (event) {
  event.preventDefault();
  const form = event.target;
  const key = form.querySelector("[name=key]").value.trim();
  const title = form.querySelector("[name=title]").value.trim();
  const content = form.querySelector("[name=content]").value.trim();
  const category = form.querySelector("[name=category]").value;

  if (!key || !title || !content) return;

  const submitBtn = form.querySelector("button[type=submit]");
  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch("/api/ai-platform/knowledge/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.KB.csrfToken(),
      },
      body: JSON.stringify({ action: "create", key, title, content, category }),
    });
    if (res.ok) {
      window.KB.state.isFormOpen = false;
      await window.KB.loadEntries();
    } else {
      const err = await res.json().catch(() => ({}));
      window.KB.formError = err.error || "Save failed";
      window.KB.renderBody();
    }
  } catch (_e) {
    window.KB.formError = "Save failed";
    window.KB.renderBody();
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
};
