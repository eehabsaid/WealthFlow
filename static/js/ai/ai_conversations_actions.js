"use strict";

/**
 * AI Workspace — Conversations: switch/delete/refresh + window exports
 */

async function _refreshActiveConversation(convId) {
  if (!convId || String(_aiState.conversationId) !== String(convId)) return;
  try {
    const res = await fetch(`/api/financial-advisor/ai/conversations/${convId}/`);
    if (!res.ok) return;
    const data = await res.json();
    const conv = data.conversation || data;
    const messages = conv.messages || [];
    const container = document.getElementById("ai-ws-messages");
    if (!container) return;

    const typingBubble = document.getElementById("ai-ws-typing-bubble");
    if (typingBubble) typingBubble.remove();

    container.innerHTML = "";
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
  } catch (_err) {
    // Non-critical
  }
}

async function _switchAIChatConversation(convId) {
  _aiState.conversationId = convId;
  _aiState.lastResponseMeta = null;
  localStorage.setItem("wf_active_ai_conv", convId);

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

    // Check progress endpoint or conv.is_running to resume live thinking bubble
    try {
      const progressRes = await fetch(
        `/api/financial-advisor/ai/progress/?conversation_id=${encodeURIComponent(convId)}`
      );
      if (progressRes.ok) {
        const progressData = await progressRes.json();
        if (progressData.status === "running") {
          _setLoadingUI(true, convId);
        } else if (conv.is_running) {
          _setLoadingUI(true, convId);
        }
      } else if (conv.is_running) {
        _setLoadingUI(true, convId);
      }
    } catch (_e) {
      if (conv.is_running) {
        _setLoadingUI(true, convId);
      }
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
        localStorage.removeItem("wf_active_ai_conv");
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
window._refreshActiveConversation = _refreshActiveConversation;
