/**
 * WealthFlow AI Workspace - Learned Answers
 * Lists the user's rated answers and lets them clear a rating. Thumbs-up answers to how/where/should
 * questions are reused as examples for similar questions; thumbs-down answers are never reused.
 */

"use strict";

window.LA = window.LA || {};
window.LA.state = { items: [], loading: false, error: null };

window.LA.t = function (key, fallback) {
  return (window.t && window.t(key, fallback)) || fallback || key;
};

window.LA.esc = function (str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
};

window.LA.shell = function () {
  const t = window.LA.t;
  const esc = window.LA.esc;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div>
        <h5 class="modal-title fw-bold mb-0 text-body" data-i18n="ai_la_title">${esc(t("ai_la_title", "Learned Answers"))}</h5>
        <small class="text-muted" data-i18n="ai_la_subtitle">${esc(t("ai_la_subtitle", "Answers you rated. Approved how-to answers are reused for similar questions; rejected ones never are."))}</small>
      </div>
      <button type="button" class="btn-close text-reset ms-auto" onclick="closeModal()" aria-label="Close"></button>
    </div>
    <div class="modal-body p-0" id="la-modal-body" style="min-height: 240px;"></div>
  `;
};

window.LA.render = function () {
  const body = document.getElementById("la-modal-body");
  if (!body) return;
  const t = window.LA.t;
  const esc = window.LA.esc;
  const { items, loading, error } = window.LA.state;
  if (loading) {
    body.innerHTML = `<div class="text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>${esc(t("ai_la_loading", "Loading..."))}</div>`;
    return;
  }
  if (error) {
    body.innerHTML = `<div class="alert alert-danger m-4">${esc(error)}</div>`;
    return;
  }
  if (items.length === 0) {
    body.innerHTML = `<div class="text-center text-muted py-5" id="la-empty"><i class="bi bi-hand-thumbs-up fs-1 d-block mb-2"></i>${esc(t("ai_la_empty", "No rated answers yet. Use the thumbs under an answer."))}</div>`;
    return;
  }
  body.innerHTML = items
    .map((it) => {
      const up = it.rating === 1;
      const icon = up
        ? "bi-hand-thumbs-up-fill text-success"
        : "bi-hand-thumbs-down-fill text-danger";
      const reused = up && it.kind === "workflow";
      return `
      <div class="la-row d-flex align-items-start px-4 py-3 border-bottom border-secondary-subtle" style="gap:12px;" data-msg-id="${esc(it.message_id)}">
        <i class="bi ${icon} mt-1"></i>
        <div class="flex-grow-1">
          <div class="fw-semibold text-body small">${esc(it.question)}</div>
          <div class="text-muted small">${esc((it.answer || "").slice(0, 220))}</div>
          <span class="badge ${reused ? "bg-success" : "bg-secondary"} mt-1">${esc(reused ? t("ai_la_reused", "Reused for similar questions") : t("ai_la_not_reused", "Not reused"))}</span>
        </div>
        <button class="btn btn-sm btn-outline-secondary py-0 px-2" title="${esc(t("ai_la_clear", "Clear rating"))}" onclick="window.LA.clear(${esc(it.message_id)})">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>`;
    })
    .join("");
};

window.LA.load = async function () {
  window.LA.state.loading = true;
  window.LA.state.error = null;
  window.LA.render();
  try {
    const res = await fetch("/api/financial-advisor/ai/feedback/");
    if (!res.ok) throw new Error("load_failed");
    window.LA.state.items = (await res.json()).items || [];
  } catch (_e) {
    window.LA.state.error = window.LA.t("ai_la_error", "Failed to load rated answers.");
  }
  window.LA.state.loading = false;
  window.LA.render();
};

window.LA.clear = async function (messageId) {
  try {
    const res = await fetch(`/api/financial-advisor/ai/messages/${messageId}/feedback/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.wfGetCsrfToken?.() || "",
      },
      body: JSON.stringify({ rating: 0 }),
    });
    if (!res.ok) throw new Error("clear_failed");
    window.LA.state.items = window.LA.state.items.filter((it) => it.message_id !== messageId);
    window.LA.render();
  } catch (_e) {
    showToast(window.LA.t("ai_la_clear_error", "Could not clear the rating."), "error");
  }
};

window.openLearnedAnswersModal = function () {
  window.LA.state = { items: [], loading: false, error: null };
  showModal(window.LA.shell());
  window.LA.load();
  if (window.applyTranslations) window.applyTranslations();
};
