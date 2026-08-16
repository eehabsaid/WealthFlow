'use strict';

/**
 * AI Workspace — Loading & Progress
 * Manages the "thinking" typing bubble and polls the backend investigation-loop
 * progress endpoint to show live step-by-step status (e.g. "Step 2/8: Checking your data...").
 * Depends on: ai_core.js. Uses global _escapeHtml (defined elsewhere in the app bundle).
 */

let _progressPollInterval = null;

function _updateThinkingBubbleText(text) {
  const statusEl = document.getElementById('ai-ws-thinking-status-text');
  if (statusEl) {
    statusEl.textContent = text;
  }
}

function _startProgressPolling(conversationId) {
  if (_progressPollInterval) return;
  _progressPollInterval = setInterval(async () => {
    if (!conversationId) return;
    try {
      const res = await fetch(`/api/financial-advisor/ai/progress/?conversation_id=${encodeURIComponent(conversationId)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === 'running' && data.step && data.tool) {
        const desc = data.label || data.tool.replace(/_/g, ' ');
        _updateThinkingBubbleText(
          `Step ${data.step}/${data.max_steps || 8}: ${desc}\u2026`
        );
      } else if (data.status === 'done') {
        _stopProgressPolling();
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

  const inputEl = document.getElementById('ai-ws-input');
  const sendBtn = document.querySelector('.ai-ws-send-btn');
  const messagesContainer = document.getElementById('ai-ws-messages');

  if (inputEl) {
    inputEl.disabled = loading;
  }

  if (sendBtn) {
    sendBtn.disabled = loading;
    if (loading) {
      sendBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
        <span data-i18n="ai_ws_thinking">${_escapeHtml(_aiT('ai_ws_thinking', 'Thinking...'))}</span>
      `;
    } else {
      sendBtn.innerHTML = `
        <span data-i18n="ai_chat_send_button">${_escapeHtml(_aiT('ai_chat_send_button', 'Send'))}</span>
        <i class="bi bi-send"></i>
      `;
    }
  }

  if (messagesContainer) {
    const existingBubble = document.getElementById('ai-ws-typing-bubble');
    if (loading && !existingBubble) {
      const defaultStatus = _escapeHtml(_aiT('ai_ws_thinking_status', 'WealthFlow AI is thinking...'));
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