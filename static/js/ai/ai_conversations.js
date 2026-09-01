"use strict";

/**
 * AI Workspace — Conversations
 * Fetches, groups, and renders the conversation list; handles switching,
 * deleting, and starting new conversations.
 * Depends on: ai_core.js, ai_messages.js (render/empty state), ai_context_panel.js (right panel)
 */

async function _fetchAIChatConversations() {
  try {
    const res = await fetch("/api/financial-advisor/ai/conversations/");
    if (!res.ok) return;
    const data = await res.json();

    const container = document.getElementById("ai-ws-conv-list");
    if (!container) return;

    container.innerHTML = "";

    if (!data.conversations || data.conversations.length === 0) {
      return;
    }

    const groups = {
      today: [],
      yesterday: [],
      thisWeek: [],
      older: [],
    };

    const now = new Date();
    data.conversations.forEach((conv) => {
      const date = new Date(conv.created_at || conv.updated_at);
      const diffTime = Math.abs(now - date);
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

      if (diffDays === 0 && date.getDate() === now.getDate()) {
        groups.today.push(conv);
      } else if (diffDays <= 1) {
        groups.yesterday.push(conv);
      } else if (diffDays <= 7) {
        groups.thisWeek.push(conv);
      } else {
        groups.older.push(conv);
      }
    });

    const renderGroup = (groupData, i18nKey, defaultTitle) => {
      if (groupData.length === 0) return "";
      let html = `<div class="ai-ws-conv-group"><div class="ai-ws-conv-group-title" data-i18n="${i18nKey}">${defaultTitle}</div>`;
      groupData.forEach((conv) => {
        const isActive = String(_aiState.conversationId) === String(conv.id) ? "active" : "";
        const timeAgo = _relativeTime(conv.updated_at || conv.created_at);
        const isPinned = conv.is_pinned || false;
        html += `
          <div class="ai-ws-conv-item ${isActive}" onclick="_switchAIChatConversation('${conv.id}')">
            <div class="ai-ws-conv-header-row">
              <div class="ai-ws-conv-title">${conv.title || _aiT("ai_ws_untitled", "Untitled")}</div>
              <button class="ai-ws-btn-delete" onclick="event.stopPropagation(); togglePinConversation('${conv.id}', ${isPinned})" title="${isPinned ? "Unpin" : "Pin"}" style="opacity:${isPinned ? 1 : 0.4};">
                <i class="bi bi-pin-angle${isPinned ? "-fill" : ""}"></i>
              </button>
              <button class="ai-ws-btn-delete" onclick="event.stopPropagation(); _deleteAIChatConversation('${conv.id}')" title="Delete">
                <i class="bi bi-trash"></i>
              </button>
            </div>
            <div class="ai-ws-conv-time">${timeAgo}</div>
          </div>
        `;
      });
      html += `</div>`;
      return html;
    };

    container.innerHTML += renderGroup(groups.today, "ai_ws_group_today", "Today");
    container.innerHTML += renderGroup(groups.yesterday, "ai_ws_group_yesterday", "Yesterday");
    container.innerHTML += renderGroup(groups.thisWeek, "ai_ws_group_this_week", "This Week");
    container.innerHTML += renderGroup(groups.older, "ai_ws_group_older", "Older");

    _applyTranslations();
  } catch (err) {
    // Handle error gracefully
  }
}

function _startNewAIChatConversation() {
  _aiState.conversationId = null;
  _aiState.lastResponseMeta = null;
  const container = document.getElementById("ai-ws-messages");
  if (container) container.innerHTML = "";
  _renderEmptyState();
  _renderRightPanel();
  _fetchAIChatConversations();
  const inputEl = document.getElementById("ai-ws-input");
  if (inputEl) {
    inputEl.value = "";
    inputEl.focus();
  }
}

async function _switchAIChatConversation(convId) {
  _aiState.conversationId = convId;
  _aiState.lastResponseMeta = null;

  const container = document.getElementById("ai-ws-messages");
  if (container) {
    container.innerHTML = "";
  }

  _fetchAIChatConversations();

  try {
    const res = await fetch(`/api/financial-advisor/ai/conversations/${convId}/`);
    if (!res.ok) throw new Error("Failed to fetch conversation");
    const data = await res.json();

    const conv = data.conversation || data;
    const messages = conv.messages || [];
    if (messages.length > 0) {
      messages.forEach((msg) => {
        _appendMessage(msg.role, msg.content, msg.tool_calls, msg.sources, msg.created_at);
      });
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === "assistant") {
        _aiState.lastResponseMeta = {
          sources: lastMsg.sources || [],
          tool_calls: lastMsg.tool_calls || [],
        };
      }
    } else {
      _renderEmptyState();
    }

    _renderRightPanel();

    // Resume thinking state if backend is still processing for this conversation
    try {
      const progressRes = await fetch(
        `/api/financial-advisor/ai/progress/?conversation_id=${encodeURIComponent(convId)}`
      );
      if (progressRes.ok) {
        const progressData = await progressRes.json();
        if (progressData.status === "running") {
          _setLoadingUI(true, convId);
        }
      }
    } catch (_e) {
      // Non-critical — ignore
    }
  } catch (err) {
    _renderEmptyState();
  }
}

async function _deleteAIChatConversation(convId) {
  if (
    !confirm(_aiT("ai_ws_confirm_delete", "Are you sure you want to delete this conversation?"))
  ) {
    return;
  }

  try {
    const res = await fetch(`/api/financial-advisor/ai/conversations/${convId}/`, {
      method: "DELETE",
      headers: {
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")?.value || "",
      },
    });

    if (res.ok) {
      if (String(_aiState.conversationId) === String(convId)) {
        _aiState.conversationId = null;
        _aiState.lastResponseMeta = null;
        const container = document.getElementById("ai-ws-messages");
        if (container) container.innerHTML = "";
        _renderEmptyState();
        _renderRightPanel();
      }
      _fetchAIChatConversations();
    }
  } catch (err) {
    // Handle error
  }
}

window._startNewAIChatConversation = _startNewAIChatConversation;
window._switchAIChatConversation = _switchAIChatConversation;
window._deleteAIChatConversation = _deleteAIChatConversation;
