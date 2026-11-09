"use strict";

/**
 * AI Workspace — attach files to the next message: upload (read by the server), show chips, send their ids with the message.
 * Depends on: ai_core.js
 */

const AIAttach = (() => {
  let pending = [];
  const esc = (t) => (typeof _escapeHtml === "function" ? _escapeHtml(t) : String(t));
  const ICON = {
    table: "bi-file-earmark-spreadsheet",
    text: "bi-file-earmark-text",
    image: "bi-file-earmark-image",
  };

  function chips(files, removable) {
    return files
      .map(
        (f) =>
          `<span class="ai-attach-chip" data-att-id="${f.id}"><i class="bi ${ICON[f.kind] || "bi-paperclip"}"></i> ${esc(f.name)}${
            removable
              ? ` <a href="#" onclick="AIAttach.remove(${f.id}); return false;" aria-label="${esc(_aiT("ai_attach_remove", "Remove"))}">×</a>`
              : ""
          }</span>`
      )
      .join("");
  }

  function paint() {
    const box = document.getElementById("ai-ws-attach-chips");
    if (box) box.innerHTML = chips(pending, true);
  }

  async function upload(input) {
    const box = document.getElementById("ai-ws-attach-chips");
    for (const file of Array.from(input.files || [])) {
      if (pending.length >= 5) break;
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/financial-advisor/ai/attachments/", {
        method: "POST",
        headers: { "X-CSRFToken": window.wfGetCsrfToken?.() || "" },
        body: form,
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) pending.push(data.attachment);
      else if (box)
        box.insertAdjacentHTML(
          "beforeend",
          `<span class="ai-attach-chip text-danger">${esc(file.name)}: ${esc(_aiT("ai_attach_err_" + data.error, data.message || "Upload failed."))}</span>`
        );
    }
    input.value = "";
    if (pending.length) paint();
  }

  function remove(id) {
    fetch(`/api/financial-advisor/ai/attachments/${id}/`, {
      method: "DELETE",
      headers: { "X-CSRFToken": window.wfGetCsrfToken?.() || "" },
    });
    pending = pending.filter((a) => a.id !== id);
    paint();
  }

  const take = () => {
    const out = pending;
    pending = [];
    paint();
    return out;
  };

  function paintLast(files) {
    if (!files.length) return;
    const users = document.querySelectorAll(
      '#ai-ws-messages .ai-ws-msg[data-role="user"] .ai-ws-msg-content'
    );
    users[users.length - 1]?.insertAdjacentHTML(
      "afterend",
      `<div class="ai-attach-chips">${chips(files, false)}</div>`
    );
  }

  return {
    upload,
    remove,
    take,
    paintLast,
    chips: (f) => (f.length ? `<div class="ai-attach-chips">${chips(f, false)}</div>` : ""),
  };
})();

window.AIAttach = AIAttach;
