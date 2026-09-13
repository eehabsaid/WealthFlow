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
        const isRunning = Boolean(conv.is_running);
        const runningBadge = isRunning
          ? `<span class="spinner-grow spinner-grow-sm text-primary me-1" style="width:0.65rem;height:0.65rem;" role="status" title="${_escapeHtml(_aiT("ai_ws_generating", "Generating..."))}"></span>`
          : "";
        html += `
          <div class="ai-ws-conv-item ${isActive}" onclick="_switchAIChatConversation('${conv.id}')">
            <div class="ai-ws-conv-header-row">
              <div class="ai-ws-conv-title">${runningBadge}${_escapeHtml(conv.title || _aiT("ai_ws_untitled", "Untitled"))}</div>
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
  localStorage.removeItem("wf_active_ai_conv");
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

