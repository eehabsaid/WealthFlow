"use strict";

/**
 * AI Workspace — Loading & Progress
 * Manages the "thinking" typing bubble and polls the backend investigation-loop
 * progress endpoint to show live step-by-step status (e.g. "Step 2/8: Checking your data...").
 * Depends on: ai_core.js. Uses global _escapeHtml (defined elsewhere in the app bundle).
 */

let _progressPollInterval = null;

function _formatElapsed(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

function _updateThinkingBubbleText(text) {
  const statusEl = document.getElementById("ai-ws-thinking-status-text");
  if (statusEl) {
    statusEl.textContent = text;
  }
}

function _startProgressPolling(conversationId) {
  if (_progressPollInterval) {
    clearInterval(_progressPollInterval);
    _progressPollInterval = null;
  }
  _progressPollInterval = setInterval(async () => {
    if (!conversationId) return;
    try {
      const res = await fetch(
        `/api/financial-advisor/ai/progress/?conversation_id=${encodeURIComponent(conversationId)}`
      );
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === "running") {
        const desc =
          data.label ||
          (data.tool
            ? data.tool.replace(/_/g, " ")
            : _aiT("ai_ws_thinking_status", "WealthFlow AI is thinking..."));
        const elapsedStr =
          data.elapsed_s != null ? ` (${_formatElapsed(data.elapsed_s)})` : "";
        let statusText = "";
        if (data.step && data.step > 0) {
          statusText = `Step ${data.step}/${data.max_steps || 8}: ${desc}${elapsedStr}`;
        } else {
          statusText = `${desc}${elapsedStr}`;
        }
        _updateThinkingBubbleText(statusText);
      } else if (data.status === "done") {
        _stopProgressPolling();
        _setLoadingUI(false);
        if (typeof window._refreshActiveConversation === "function") {
          window._refreshActiveConversation(conversationId);
        }
        if (typeof window._fetchAIChatConversations === "function") {
          window._fetchAIChatConversations();
        }
      } else if (data.status === "error") {
        _stopProgressPolling();
        _setLoadingUI(false);
        if (typeof window._refreshActiveConversation === "function") {
          window._refreshActiveConversation(conversationId);
        }
        if (typeof window._fetchAIChatConversations === "function") {
          window._fetchAIChatConversations();
        }
      }
    } catch (_e) {
      // Polling errors are silent — the user still gets the final answer
    }
  }, 2000);
}

function _stopProgressPolling() {
  if (_progressPollInterval) {
    clearInterval(_progressPollInterval);
    _progressPollInterval = null;
  }
}

function _setLoadingUI(loading, conversationId) {
  _aiState.loading = loading;

  const inputEl = document.getElementById("ai-ws-input");
  const sendBtn = document.querySelector(".ai-ws-send-btn");
  const messagesContainer = document.getElementById("ai-ws-messages");

  if (inputEl) {
    inputEl.disabled = loading;
  }

  if (sendBtn) {
    sendBtn.disabled = loading;
    if (loading) {
      sendBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
        <span data-i18n="ai_ws_thinking">${_escapeHtml(_aiT("ai_ws_thinking", "Thinking..."))}</span>
      `;
    } else {
      sendBtn.innerHTML = `
        <span data-i18n="ai_chat_send_button">${_escapeHtml(_aiT("ai_chat_send_button", "Send"))}</span>
        <i class="bi bi-send"></i>
      `;
    }
  }

  if (messagesContainer) {
    const existingBubble = document.getElementById("ai-ws-typing-bubble");
    if (loading) {
      if (!existingBubble) {
        const defaultStatus = _escapeHtml(
          _aiT("ai_ws_thinking_status", "WealthFlow AI is thinking...")
        );
        const bubbleHtml = `
          <div class="ai-ws-msg" id="ai-ws-typing-bubble">
            <div class="ai-ws-msg-avatar assistant">
              <i class="bi bi-robot"></i>
            </div>
            <div class="ai-ws-msg-body">
              <div class="ai-ws-msg-role">
                <span data-i18n="ai_role_assistant">WealthFlow AI</span>
              </div>
              <div class="ai-ws-msg-content text-muted d-flex align-items-center gap-2 pt-1">
                <span class="spinner-grow spinner-grow-sm text-primary" role="status" aria-hidden="true"></span>
                <span class="font-monospace small" id="ai-ws-thinking-status-text">${defaultStatus}</span>
              </div>
            </div>
          </div>
        `;
        messagesContainer.innerHTML += bubbleHtml;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
      if (conversationId) {
        _startProgressPolling(conversationId);
      }
    } else if (!loading && existingBubble) {
      _stopProgressPolling();
      existingBubble.remove();
    }
  }

  if (window._applyTranslations) {
    window._applyTranslations();
  }
}

window._startProgressPolling = _startProgressPolling;
window._stopProgressPolling = _stopProgressPolling;
window._setLoadingUI = _setLoadingUI;
window._updateThinkingBubbleText = _updateThinkingBubbleText;
