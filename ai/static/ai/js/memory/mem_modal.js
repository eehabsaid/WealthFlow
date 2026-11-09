/**
 * WealthFlow AI Workspace - AI Memory
 * Lists the notes the AI wrote for itself from earlier chats and lets the user edit or delete them.
 * The AI saves notes on its own; this page is optional and needs no setup.
 */

"use strict";

window.AIMem = window.AIMem || {};
window.AIMem.state = { items: [], loading: false, error: null, editing: null, confirming: null };

window.AIMem.t = function (key, fallback) {
  return (window.t && window.t(key, fallback)) || fallback || key;
};

window.AIMem.esc = function (str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
};

window.AIMem.headers = function () {
  return { "Content-Type": "application/json", "X-CSRFToken": window.wfGetCsrfToken?.() || "" };
};

window.AIMem.shell = function () {
  const { t, esc } = window.AIMem;
  return `
    <div class="modal-header border-bottom border-secondary-subtle px-4 py-3 align-items-center">
      <div>
        <h5 class="modal-title fw-bold mb-0 text-body" data-i18n="ai_mem_title">${esc(t("ai_mem_title", "AI Memory"))}</h5>
        <small class="text-muted" data-i18n="ai_mem_subtitle">${esc(t("ai_mem_subtitle", "Notes the AI wrote for itself from your earlier chats."))}</small>
      </div>
      <button type="button" class="btn-close text-reset ms-auto" onclick="closeModal()" aria-label="Close"></button>
    </div>
    <div class="modal-body p-0" id="mem-modal-body" style="min-height: 240px;"></div>
  `;
};

window.AIMem.row = function (it) {
  const { t, esc, state } = window.AIMem;
  const date = String(it.updated_at || "").slice(0, 10);
  if (state.editing === it.id) {
    return `
      <div class="mem-row px-4 py-3 border-bottom border-secondary-subtle" data-note-id="${esc(it.id)}">
        <label class="form-label small mb-1" for="mem-edit-title">${esc(t("ai_mem_title_label", "Title"))}</label>
        <input class="form-control form-control-sm mb-2" id="mem-edit-title" maxlength="120" value="${esc(it.title)}">
        <label class="form-label small mb-1" for="mem-edit-body">${esc(t("ai_mem_body_label", "Note"))}</label>
        <textarea class="form-control form-control-sm mb-2" id="mem-edit-body" rows="4" maxlength="700">${esc(it.body)}</textarea>
        <div class="form-check mb-2"><input class="form-check-input" type="checkbox" id="mem-edit-always"${it.always ? " checked" : ""}><label class="form-check-label small" for="mem-edit-always">${esc(t("ai_mem_always", "Always applied"))}</label></div>
        <button class="btn btn-sm btn-primary me-1" id="mem-save" onclick="window.AIMem.save(${esc(it.id)})">${esc(t("ai_mem_save", "Save"))}</button>
        <button class="btn btn-sm btn-outline-secondary" onclick="window.AIMem.edit(null)">${esc(t("ai_mem_cancel", "Cancel"))}</button>
      </div>`;
  }
  const confirming = state.confirming === it.id;
  return `
    <div class="mem-row d-flex align-items-start px-4 py-3 border-bottom border-secondary-subtle" style="gap:12px;" data-note-id="${esc(it.id)}">
      <i class="bi bi-journal-text mt-1 text-primary"></i>
      <div class="flex-grow-1">
        <div class="fw-semibold text-body small">${esc(it.title)}${it.always ? ` <span class="badge bg-primary ms-1 mem-always">${esc(t("ai_mem_always", "Always applied"))}</span>` : ""}</div>
        <div class="text-body small">${esc(it.body)}</div>
        <div class="text-muted" style="font-size:0.75rem;">${esc(t("ai_mem_updated", "Updated"))} ${esc(date)}</div>
      </div>
      <div class="text-nowrap">
        ${
          confirming
            ? `<span class="small me-1">${esc(t("ai_mem_confirm_delete", "Delete this note?"))}</span>
               <button class="btn btn-sm btn-danger py-0 px-2 mem-delete-yes" onclick="window.AIMem.remove(${esc(it.id)})">${esc(t("ai_mem_delete", "Delete"))}</button>
               <button class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="window.AIMem.ask(null)">${esc(t("ai_mem_cancel", "Cancel"))}</button>`
            : `<button class="btn btn-sm btn-outline-secondary py-0 px-2 mem-edit" title="${esc(t("ai_mem_edit", "Edit"))}" onclick="window.AIMem.edit(${esc(it.id)})"><i class="bi bi-pencil"></i></button>
               <button class="btn btn-sm btn-outline-danger py-0 px-2 mem-delete" title="${esc(t("ai_mem_delete", "Delete"))}" onclick="window.AIMem.ask(${esc(it.id)})"><i class="bi bi-trash"></i></button>`
        }
      </div>
    </div>`;
};

window.AIMem.render = function () {
  const body = document.getElementById("mem-modal-body");
  if (!body) return;
  const { t, esc, state } = window.AIMem;
  if (state.loading) {
    body.innerHTML = `<div class="text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>${esc(t("ai_mem_loading", "Loading..."))}</div>`;
  } else if (state.error) {
    body.innerHTML = `<div class="alert alert-danger m-4">${esc(state.error)}</div>`;
  } else if (state.items.length === 0) {
    body.innerHTML = `<div class="text-center text-muted py-5" id="mem-empty"><i class="bi bi-journal fs-1 d-block mb-2"></i>${esc(t("ai_mem_empty", "Nothing remembered yet."))}</div>`;
  } else {
    body.innerHTML = state.items.map(window.AIMem.row).join("");
  }
};

window.AIMem.load = async function () {
  window.AIMem.state.loading = true;
  window.AIMem.state.error = null;
  window.AIMem.render();
  try {
    const res = await fetch("/api/financial-advisor/ai/memory/");
    if (!res.ok) throw new Error("load_failed");
    window.AIMem.state.items = (await res.json()).items || [];
  } catch (_e) {
    window.AIMem.state.error = window.AIMem.t("ai_mem_error", "Failed to load memory.");
  }
  window.AIMem.state.loading = false;
  window.AIMem.render();
};

window.AIMem.edit = function (id) {
  window.AIMem.state.editing = id;
  window.AIMem.state.confirming = null;
  window.AIMem.render();
};

window.AIMem.ask = function (id) {
  window.AIMem.state.confirming = id;
  window.AIMem.render();
};

window.AIMem.save = async function (id) {
  const title = document.getElementById("mem-edit-title")?.value || "";
  const body = document.getElementById("mem-edit-body")?.value || "";
  const always = !!document.getElementById("mem-edit-always")?.checked;
  try {
    const res = await fetch(`/api/financial-advisor/ai/memory/${id}/`, {
      method: "PATCH",
      headers: window.AIMem.headers(),
      body: JSON.stringify({ title, body, always }),
    });
    if (!res.ok) throw new Error("save_failed");
    const item = (await res.json()).item;
    window.AIMem.state.items = window.AIMem.state.items.map((it) => (it.id === id ? item : it));
    window.AIMem.state.editing = null;
    window.AIMem.render();
  } catch (_e) {
    showToast(window.AIMem.t("ai_mem_save_error", "Could not save the note."), "error");
  }
};

window.AIMem.remove = async function (id) {
  try {
    const res = await fetch(`/api/financial-advisor/ai/memory/${id}/`, {
      method: "DELETE",
      headers: window.AIMem.headers(),
    });
    if (!res.ok) throw new Error("delete_failed");
    window.AIMem.state.items = window.AIMem.state.items.filter((it) => it.id !== id);
    window.AIMem.state.confirming = null;
    window.AIMem.render();
  } catch (_e) {
    showToast(window.AIMem.t("ai_mem_delete_error", "Could not delete the note."), "error");
  }
};

window.openAIMemoryModal = function () {
  window.AIMem.state = { items: [], loading: false, error: null, editing: null, confirming: null };
  showModal(window.AIMem.shell());
  window.AIMem.load();
  if (window.applyTranslations) window.applyTranslations();
};
