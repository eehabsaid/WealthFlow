"use strict";

/**
 * AI Workspace — Chat management: rename (inline), search across all chats, edit-and-resend.
 * Every call goes to the owner-scoped endpoints; nothing is stored in the browser.
 * Depends on: ai_core.js, ai_conversations.js, ai_messages.js, ai_chat_submit.js
 */

const AICM = (() => {
  const base = "/api/financial-advisor/ai/";
  const csrf = () => window.wfGetCsrfToken?.() || "";
  const esc = (t) => (typeof _escapeHtml === "function" ? _escapeHtml(t) : String(t));
  let searchTimer = null;

  async function rename(convId) {
    const item = document.querySelector(`.ai-ws-conv-item[data-conv-id="${convId}"]`);
    const titleEl = item && item.querySelector(".ai-ws-conv-title");
    if (!titleEl) return;
    const old = titleEl.textContent.trim();
    titleEl.innerHTML = `<input type="text" class="form-control form-control-sm ai-ws-rename-input" maxlength="80" value="${esc(old)}">`;
    const input = titleEl.querySelector("input");
    input.onclick = (e) => e.stopPropagation();
    input.focus();
    input.select();
    let done = false;
    const finish = async (save) => {
      if (done) return;
      done = true;
      const text = input.value.trim();
      if (save && text && text !== old) {
        await fetch(`${base}conversations/${convId}/`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf(),
          },
          body: JSON.stringify({ title: text }),
        });
      }
      _fetchAIChatConversations();
    };
    input.onkeydown = (e) => {
      if (e.key === "Enter") finish(true);
      if (e.key === "Escape") finish(false);
    };
    input.onblur = () => finish(true);
  }

  function search(text) {
    clearTimeout(searchTimer);
    const q = String(text || "").trim();
    if (q.length < 2) {
      _fetchAIChatConversations();
      return;
    }
    searchTimer = setTimeout(async () => {
      const res = await fetch(`${base}conversations/search/?q=${encodeURIComponent(q)}`);
      if (!res.ok) return;
      const rows = (await res.json()).results || [];
      const list = document.getElementById("ai-ws-conv-list");
      if (!list) return;
      list.innerHTML = rows.length
        ? rows
            .map(
              (
                r
              ) => `<div class="ai-ws-conv-item" data-conv-id="${r.id}" onclick="_switchAIChatConversation('${r.id}')">
                <div class="ai-ws-conv-title">${esc(r.title)}</div>
                ${r.snippet ? `<div class="ai-ws-conv-time ai-ws-search-snippet">${esc(r.snippet)}</div>` : ""}</div>`
            )
            .join("")
        : `<div class="ai-ws-conv-time p-2 ai-ws-search-none">${esc(_aiT("ai_ws_search_none", "No chat matches."))}</div>`;
    }, 250);
  }

  function editButton({ role, messageId }) {
    if (role !== "user" || !messageId) return "";
    return `<button type="button" class="btn btn-sm btn-link p-0 ai-ws-msg-edit-btn" onclick="AICM.edit('${messageId}')" title="${esc(_aiT("ai_ws_edit_resend", "Edit and resend"))}"><i class="bi bi-pencil-square"></i></button>`;
  }

  function tagLastUser(id) {
    if (!id) return;
    const users = [
      ...document.querySelectorAll('#ai-ws-messages .ai-ws-msg[data-role="user"]'),
    ].filter((m) => !m.dataset.msgId);
    const last = users[users.length - 1];
    if (!last) return;
    last.dataset.msgId = id;
    last
      .querySelector(".ai-ws-msg-body")
      ?.insertAdjacentHTML("beforeend", editButton({ role: "user", messageId: id }));
  }

  function edit(messageId) {
    const msg = document.querySelector(`#ai-ws-messages .ai-ws-msg[data-msg-id="${messageId}"]`);
    const box = msg && msg.querySelector(".ai-ws-msg-content");
    if (!box || box.querySelector("textarea")) return;
    const original = box.innerText.trim();
    box.dataset.original = box.innerHTML;
    box.innerHTML = `<textarea class="form-control ai-ws-edit-area" rows="3">${esc(original)}</textarea>
      <div class="small text-muted my-1">${esc(_aiT("ai_ws_edit_note", "The replies after this message are removed."))}</div>
      <button type="button" class="btn btn-sm btn-primary ai-ws-edit-send">${esc(_aiT("ai_ws_edit_send", "Send again"))}</button>
      <button type="button" class="btn btn-sm btn-outline-secondary ai-ws-edit-cancel">${esc(_aiT("ai_mem_cancel", "Cancel"))}</button>`;
    box.querySelector(".ai-ws-edit-cancel").onclick = () => {
      box.innerHTML = box.dataset.original;
    };
    box.querySelector(".ai-ws-edit-send").onclick = async () => {
      const text = box.querySelector("textarea").value.trim();
      if (!text) return;
      const res = await fetch(`${base}messages/${messageId}/rewind/`, {
        method: "POST",
        headers: { "X-CSRFToken": csrf() },
      });
      if (!res.ok) return;
      await _switchAIChatConversation(_aiState.conversationId);
      const input = document.getElementById("ai-ws-input");
      if (input) {
        input.value = text;
        _handleAIChatSubmit();
      }
    };
  }

  (window._aiMessageExtras = window._aiMessageExtras || []).push(editButton);
  return { rename, search, edit, tagLastUser };
})();

window.AICM = AICM;
