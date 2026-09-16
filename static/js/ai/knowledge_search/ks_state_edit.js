/**
 * WealthFlow AI Workspace - Knowledge Search: State & API (edit/delete)
 * Split out of ks_state.js (200-line backlog).
 */

"use strict";

window.KS = window.KS || {};

window.KS.toggleExpand = function (id) {
  window.KS.state.expanded = window.KS.state.expanded === id ? null : id;
  window.KS.state.editing = null;
  window.KS.renderBody();
};

window.KS.startEdit = function (id) {
  var entry = window.KS.state.results.find(function (e) {
    return e.id === id;
  });
  if (!entry) return;
  window.KS.state.editing = {
    id: entry.id,
    title: entry.title,
    content: entry.content,
    category: entry.category,
  };
  window.KS.state.expanded = id;
  window.KS.renderBody();
};

window.KS.cancelEdit = function () {
  window.KS.state.editing = null;
  window.KS.renderBody();
};

window.KS.saveEdit = async function (id) {
  var titleEl = document.getElementById("ks-edit-title-" + id);
  var contentEl = document.getElementById("ks-edit-content-" + id);
  var categoryEl = document.getElementById("ks-edit-category-" + id);
  if (!titleEl || !contentEl) return;

  try {
    const res = await fetch("/api/ai-platform/knowledge/" + id + "/", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.KS.csrfToken(),
      },
      body: JSON.stringify({
        title: titleEl.value,
        content: contentEl.value,
        category: categoryEl ? categoryEl.value : undefined,
      }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    var idx = window.KS.state.results.findIndex(function (e) {
      return e.id === id;
    });
    if (idx !== -1) window.KS.state.results[idx] = data.entry;
    window.KS.state.editing = null;
    if (window.showToast)
      window.showToast(window.KS.t("ai_ks_edit_ok", "Entry updated."), "success");
    window.KS.renderBody();
  } catch (e) {
    if (window.showToast)
      window.showToast(window.KS.t("ai_ks_edit_error", "Failed to update entry."), "error");
  }
};

window.KS.deleteEntry = async function (id) {
  if (!confirm(window.KS.t("ai_ks_delete_confirm", "Delete this knowledge entry?"))) return;
  try {
    const res = await fetch("/api/ai-platform/knowledge/" + id + "/", {
      method: "DELETE",
      headers: {
        "X-CSRFToken": window.KS.csrfToken(),
      },
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    window.KS.state.results = window.KS.state.results.filter(function (e) {
      return e.id !== id;
    });
    if (window.showToast)
      window.showToast(window.KS.t("ai_ks_delete_ok", "Entry deleted."), "success");
    window.KS.renderBody();
  } catch (e) {
    if (window.showToast)
      window.showToast(window.KS.t("ai_ks_delete_error", "Failed to delete entry."), "error");
  }
};
