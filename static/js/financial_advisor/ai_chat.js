"use strict";

let _aiChatConversationId = null;
let _aiChatLoading = false;

function loadAIChat() {
  const container = document.getElementById("fa-ai-chat-content");
  if (!container) return;

  container.innerHTML = `
    <div class="card border-0 si-modern-card" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; overflow:hidden;">
      <div class="card-header d-flex align-items-center justify-content-between py-3 px-4" style="background:var(--bg-primary); border-bottom:1px solid var(--border-color);">
        <div class="d-flex align-items-center gap-2">
          <i class="bi bi-robot fs-5" style="color:var(--accent-color, #0d6efd);"></i>
          <div>
            <h6 class="mb-0 fw-semibold" style="color:var(--text-primary);" data-i18n="ai_chat_header_title">AI Financial Advisor</h6>
            <small style="color:var(--text-secondary);" data-i18n="ai_chat_header_subtitle">Ask questions about your financial health, cash flow, goals, and risk</small>
          </div>
        </div>
        <div class="d-flex align-items-center gap-2">
          <span id="ai-chat-status-badge" class="badge rounded-pill bg-secondary" data-i18n="ai_chat_status_disabled">AI Offline</span>
          <button id="ai-chat-clear-btn" class="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1" type="button" title="Clear Conversation">
            <i class="bi bi-trash"></i>
            <span data-i18n="ai_chat_clear_history">Clear</span>
          </button>
        </div>
      </div>
      
      <div class="card-body p-4" style="min-height:380px; max-height:550px; overflow-y:auto;" id="ai-chat-message-list">
        <div class="text-center py-5" id="ai-chat-empty-state">
          <i class="bi bi-chat-left-dots fs-1 mb-3" style="color:var(--text-secondary); opacity:0.5;"></i>
          <p style="color:var(--text-secondary);" data-i18n="ai_chat_empty_state">Start a conversation with AI Financial Advisor! Ask about your net worth, cash flow forecast, risk analysis, or goal progress.</p>
        </div>
      </div>

      <div class="card-footer p-3" style="background:var(--bg-primary); border-top:1px solid var(--border-color);">
        <form id="ai-chat-form" class="d-flex gap-2">
          <input 
            type="text" 
            id="ai-chat-input" 
            class="form-control" 
            style="background:var(--bg-secondary); color:var(--text-primary); border-color:var(--border-color);" 
            placeholder="Ask a financial question..." 
            data-i18n-placeholder="ai_chat_input_placeholder"
            autocomplete="off"
            required
          />
          <button type="submit" id="ai-chat-send-btn" class="btn btn-primary px-4 d-flex align-items-center gap-2">
            <span data-i18n="ai_chat_send_button">Send</span>
            <i class="bi bi-send"></i>
          </button>
        </form>
      </div>
    </div>
  `;

  if (typeof applyTranslations === "function") applyTranslations();

  const form = document.getElementById("ai-chat-form");
  if (form) {
    form.addEventListener("submit", _handleAIChatSubmit);
  }

  const clearBtn = document.getElementById("ai-chat-clear-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", _handleAIChatClear);
  }

  _fetchAIChatConversations();
}

function _fetchAIChatConversations() {
  fetch("/api/financial-advisor/ai/conversations/")
    .then((res) => (res.ok ? res.json() : { conversations: [] }))
    .then((data) => {
      const list = data.conversations || [];
      if (list.length > 0) {
        _aiChatConversationId = list[0].id;
        _loadAIChatMessages(_aiChatConversationId);
      }
    })
    .catch(() => {});
}

function _loadAIChatMessages(convId) {
  if (!convId) return;
  fetch(`/api/financial-advisor/ai/conversations/${convId}/`)
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      if (!data || !data.conversation) return;
      const msgs = data.conversation.messages || [];
      const msgContainer = document.getElementById("ai-chat-message-list");
      if (!msgContainer) return;

      if (msgs.length === 0) return;

      msgContainer.innerHTML = "";
      msgs.forEach((m) => _appendAIChatMessageBubble(m.role, m.content, false, false, m.tool_calls || []));
      _scrollAIChatToBottom();
    })
    .catch(() => {});
}

function _handleAIChatSubmit(e) {
  e.preventDefault();
  if (_aiChatLoading) return;

  const inputEl = document.getElementById("ai-chat-input");
  if (!inputEl) return;

  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = "";
  _appendAIChatMessageBubble("user", text, true);

  _setAIChatLoading(true);

  const payload = {
    message: text,
    conversation_id: _aiChatConversationId,
  };

  fetch("/api/financial-advisor/ai/chat/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": _getAIChatCSRFToken(),
    },
    body: JSON.stringify(payload),
  })
    .then((res) => res.json())
    .then((data) => {
      _setAIChatLoading(false);
      if (data.conversation_id) {
        _aiChatConversationId = data.conversation_id;
      }

      if (!data.ok) {
        const errorKey = data.error_key || "ai_error_generic";
        const fallbackText = data.error || (typeof t === "function" ? t(errorKey) : "An error occurred");
        const localizedMsg = typeof t === "function" ? t(errorKey, fallbackText) : fallbackText;
        _appendAIChatMessageBubble("assistant", localizedMsg, true, true);
        _updateAIChatStatusBadge(false);
      } else if (data.message) {
        _appendAIChatMessageBubble(
          "assistant",
          data.message.content,
          true,
          false,
          data.message.tool_calls || []
        );
        _updateAIChatStatusBadge(true);
      }
    })
    .catch((err) => {
      _setAIChatLoading(false);
      const localizedErr = typeof t === "function" ? t("ai_error_provider_unavailable") : "Unable to connect to AI service.";
      _appendAIChatMessageBubble("assistant", localizedErr, true, true);
      _updateAIChatStatusBadge(false);
    });
}

function _handleAIChatClear() {
  if (!_aiChatConversationId) {
    const msgContainer = document.getElementById("ai-chat-message-list");
    if (msgContainer) {
      msgContainer.innerHTML = `
        <div class="text-center py-5" id="ai-chat-empty-state">
          <i class="bi bi-chat-left-dots fs-1 mb-3" style="color:var(--text-secondary); opacity:0.5;"></i>
          <p style="color:var(--text-secondary);" data-i18n="ai_chat_empty_state">Start a conversation with AI Financial Advisor!</p>
        </div>
      `;
      if (typeof applyTranslations === "function") applyTranslations();
    }
    return;
  }

  fetch(`/api/financial-advisor/ai/conversations/${_aiChatConversationId}/`, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": _getAIChatCSRFToken(),
    },
  })
    .then(() => {
      _aiChatConversationId = null;
      loadAIChat();
    })
    .catch(() => {});
}

function _appendAIChatMessageBubble(role, content, animate = false, isError = false, toolCalls = []) {
  const msgContainer = document.getElementById("ai-chat-message-list");
  if (!msgContainer) return;

  const emptyState = document.getElementById("ai-chat-empty-state");
  if (emptyState) emptyState.remove();

  const isUser = role === "user";
  const wrapper = document.createElement("div");
  wrapper.className = `d-flex mb-3 ${isUser ? "justify-content-end" : "justify-content-start"}`;

  const bubble = document.createElement("div");
  bubble.style.maxWidth = "80%";
  bubble.style.borderRadius = "12px";
  bubble.style.padding = "12px 16px";

  if (isUser) {
    bubble.style.background = "var(--accent-color, #0d6efd)";
    bubble.style.color = "#ffffff";
    bubble.style.borderBottomRightRadius = "2px";
  } else if (isError) {
    bubble.style.background = "rgba(220, 53, 69, 0.15)";
    bubble.style.color = "var(--text-primary)";
    bubble.style.border = "1px solid rgba(220, 53, 69, 0.3)";
    bubble.style.borderBottomLeftRadius = "2px";
  } else {
    bubble.style.background = "var(--bg-primary)";
    bubble.style.color = "var(--text-primary)";
    bubble.style.border = "1px solid var(--border-color)";
    bubble.style.borderBottomLeftRadius = "2px";
  }

  const roleHeader = document.createElement("div");
  roleHeader.className = "small fw-bold mb-1 opacity-75 d-flex align-items-center gap-1";
  roleHeader.innerHTML = isUser
    ? `<i class="bi bi-person"></i> You`
    : `<i class="bi bi-robot"></i> AI Financial Advisor`;

  bubble.appendChild(roleHeader);

  if (toolCalls && Array.isArray(toolCalls) && toolCalls.length > 0) {
    toolCalls.forEach((tc) => {
      if (!tc || typeof tc !== "object") return;
      const toolName = tc.tool || "action";
      const status = tc.status || "success";
      const toolDiv = document.createElement("div");
      toolDiv.className = "small mb-2 px-2 py-1 rounded d-flex align-items-center gap-2";
      toolDiv.style.background = "var(--bg-secondary)";
      toolDiv.style.border = "1px solid var(--border-color)";
      toolDiv.style.color = "var(--text-secondary)";
      toolDiv.style.fontSize = "0.82rem";

      const i18nKey = `ai_tool_activity_${toolName}`;
      let iconClass = "bi-gear-fill text-primary";
      if (status === "rejected") {
        iconClass = "bi-x-circle text-danger";
      } else if (status === "failed") {
        iconClass = "bi-exclamation-triangle text-warning";
      }

      const defaultText =
        toolName === "create_scenario"
          ? "Creating scenario..."
          : toolName === "compare_scenarios"
          ? "Comparing scenarios..."
          : toolName === "summarize_report"
          ? "Summarizing report..."
          : toolName === "explain_chart"
          ? "Explaining chart data..."
          : toolName === "suggest_optimizations"
          ? "Analyzing optimization opportunities..."
          : `Executing ${toolName}...`;

      toolDiv.innerHTML = `<i class="bi ${iconClass}"></i> <span data-i18n="${i18nKey}">${defaultText}</span>`;
      bubble.appendChild(toolDiv);
    });
  }

  const textBody = document.createElement("div");
  textBody.style.whiteSpace = "pre-wrap";
  textBody.style.wordBreak = "break-word";
  textBody.textContent = content;

  bubble.appendChild(textBody);
  wrapper.appendChild(bubble);

  msgContainer.appendChild(wrapper);
  if (typeof applyTranslations === "function") applyTranslations();
  _scrollAIChatToBottom();
}

function _setAIChatLoading(loading) {
  _aiChatLoading = loading;
  const sendBtn = document.getElementById("ai-chat-send-btn");
  const msgContainer = document.getElementById("ai-chat-message-list");

  if (loading) {
    if (sendBtn) sendBtn.disabled = true;

    if (msgContainer) {
      const thinkingEl = document.createElement("div");
      thinkingEl.id = "ai-chat-thinking-indicator";
      thinkingEl.className = "d-flex mb-3 justify-content-start";
      thinkingEl.innerHTML = `
        <div style="background:var(--bg-primary); border:1px solid var(--border-color); border-radius:12px; border-bottom-left-radius:2px; padding:12px 16px;">
          <div class="d-flex align-items-center gap-2" style="color:var(--text-secondary);">
            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            <small data-i18n="ai_chat_thinking">AI Financial Advisor is thinking...</small>
          </div>
        </div>
      `;
      msgContainer.appendChild(thinkingEl);
      if (typeof applyTranslations === "function") applyTranslations();
      _scrollAIChatToBottom();
    }
  } else {
    if (sendBtn) sendBtn.disabled = false;
    const thinkingEl = document.getElementById("ai-chat-thinking-indicator");
    if (thinkingEl) thinkingEl.remove();
  }
}

function _updateAIChatStatusBadge(online) {
  const badge = document.getElementById("ai-chat-status-badge");
  if (!badge) return;

  if (online) {
    badge.className = "badge rounded-pill bg-success";
    badge.setAttribute("data-i18n", "ai_chat_status_active");
    badge.textContent = typeof t === "function" ? t("ai_chat_status_active") : "AI Online";
  } else {
    badge.className = "badge rounded-pill bg-secondary";
    badge.setAttribute("data-i18n", "ai_chat_status_disabled");
    badge.textContent = typeof t === "function" ? t("ai_chat_status_disabled") : "AI Offline";
  }
}

function _scrollAIChatToBottom() {
  const msgContainer = document.getElementById("ai-chat-message-list");
  if (msgContainer) {
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }
}

function _getAIChatCSRFToken() {
  const cookieValue = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
  return cookieValue || "";
}

window.loadAIChat = loadAIChat;
