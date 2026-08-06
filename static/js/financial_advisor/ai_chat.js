"use strict";

let _aiChatConversationId = null;
let _aiChatLoading = false;

function loadAIChat() {
  const container = document.getElementById("fa-ai-chat-content");
  if (!container) return;

  container.innerHTML = `
    <div class="card border-0 si-modern-card" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; overflow:hidden;">
      <div class="card-body p-0">
        <div class="row g-0">
          <!-- Sidebar: Threads & New Chat -->
          <div class="col-md-4 col-lg-3 p-3 border-end d-flex flex-column" style="border-color:var(--border-color) !important; background:var(--bg-primary); min-height:550px;">
            <button id="ai-chat-new-thread-btn" class="btn btn-primary w-100 mb-3 d-flex align-items-center justify-content-center gap-2" type="button">
              <i class="bi bi-plus-lg"></i>
              <span data-i18n="ai_chat_new_chat_btn">New Chat</span>
            </button>
            <div class="d-flex align-items-center justify-content-between mb-2">
              <small class="fw-bold text-uppercase" style="color:var(--text-secondary); font-size:0.75rem;" data-i18n="ai_chat_sidebar_conversations">Conversations</small>
            </div>
            <div id="ai-chat-thread-list" class="flex-grow-1 overflow-y-auto pe-1" style="max-height:450px;">
              <!-- Dynamic thread items -->
            </div>
          </div>

          <!-- Main Chat Panel -->
          <div class="col-md-8 col-lg-9 d-flex flex-column" style="min-height:550px;">
            <!-- Header -->
            <div class="card-header d-flex align-items-center justify-content-between py-3 px-4" style="background:var(--bg-primary); border-bottom:1px solid var(--border-color);">
              <div class="d-flex align-items-center gap-2">
                <i class="bi bi-robot fs-5" style="color:var(--accent-color, #0d6efd);"></i>
                <div>
                  <h6 id="ai-chat-active-title" class="mb-0 fw-semibold" style="color:var(--text-primary);" data-i18n="ai_chat_header_title">AI Financial Advisor</h6>
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
            
            <!-- Message List -->
            <div class="card-body p-4 flex-grow-1" style="min-height:380px; max-height:480px; overflow-y:auto;" id="ai-chat-message-list">
              <div class="text-center py-5" id="ai-chat-empty-state">
                <i class="bi bi-chat-left-dots fs-1 mb-3" style="color:var(--text-secondary); opacity:0.5;"></i>
                <p style="color:var(--text-secondary);" data-i18n="ai_chat_empty_state">Start a conversation with AI Financial Advisor! Ask about your net worth, cash flow forecast, risk analysis, or goal progress.</p>
              </div>
            </div>

            <!-- Footer / Input -->
            <div class="card-footer p-3" style="background:var(--bg-primary); border-top:1px solid var(--border-color);">
              <form id="ai-chat-form" class="d-flex gap-2 flex-wrap">
                <select 
                  id="ai-chat-domain-select" 
                  class="form-select form-select-sm" 
                  style="max-width:240px; background:var(--bg-secondary); color:var(--text-primary); border-color:var(--border-color);"
                  aria-label="Question Domain"
                >
                  <option value="business_data_analysis" selected data-i18n="ai_domain_business_data">Business / Data Analysis</option>
                  <option value="app_features_architecture" data-i18n="ai_domain_app_features">Application Features & Architecture</option>
                </select>
                <textarea 
                  id="ai-chat-input" 
                  class="form-control flex-grow-1" 
                  rows="1"
                  style="background:var(--bg-secondary); color:var(--text-primary); border-color:var(--border-color); resize:none; overflow-y:auto; max-height:120px;" 
                  placeholder="Ask a financial or business data question..." 
                  data-i18n-placeholder="ai_chat_input_placeholder_business"
                  required
                ></textarea>
                <button type="submit" id="ai-chat-send-btn" class="btn btn-primary px-4 d-flex align-items-center gap-2">
                  <span data-i18n="ai_chat_send_button">Send</span>
                  <i class="bi bi-send"></i>
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  if (typeof applyTranslations === "function") applyTranslations();

  const newBtn = document.getElementById("ai-chat-new-thread-btn");
  if (newBtn) {
    newBtn.addEventListener("click", _startNewAIChatConversation);
  }

  const inputEl = document.getElementById("ai-chat-input");
  if (inputEl) {
    inputEl.addEventListener("keydown", function(e) {
      if (e.key === "Enter") {
        if (e.shiftKey) {
          return;
        }
        e.preventDefault();
        const form = document.getElementById("ai-chat-form");
        if (form) {
          form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        }
      }
    });

    inputEl.addEventListener("input", function() {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 120) + "px";
    });
  }

  const domainSelect = document.getElementById("ai-chat-domain-select");
  if (domainSelect) {
    domainSelect.addEventListener("change", function() {
      _updateAIChatInputPlaceholder(this.value);
    });
    _updateAIChatInputPlaceholder(domainSelect.value);
  }

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

function _startNewAIChatConversation() {
  _aiChatConversationId = null;
  const msgContainer = document.getElementById("ai-chat-message-list");
  if (msgContainer) {
    msgContainer.innerHTML = `
      <div class="text-center py-5" id="ai-chat-empty-state">
        <i class="bi bi-chat-left-dots fs-1 mb-3" style="color:var(--text-secondary); opacity:0.5;"></i>
        <p style="color:var(--text-secondary);" data-i18n="ai_chat_empty_state">Start a conversation with AI Financial Advisor!</p>
      </div>
    `;
  }
  const inputEl = document.getElementById("ai-chat-input");
  if (inputEl) inputEl.value = "";

  const titleEl = document.getElementById("ai-chat-active-title");
  if (titleEl) titleEl.textContent = typeof t === "function" ? t("ai_chat_header_title") : "AI Financial Advisor";

  _fetchAIChatConversations();
}

function _fetchAIChatConversations() {
  fetch("/api/financial-advisor/ai/conversations/")
    .then((res) => res.json())
    .then((data) => {
      const threadList = document.getElementById("ai-chat-thread-list");
      if (!threadList) return;

      const conversations = (data && data.conversations) || [];
      if (conversations.length === 0) {
        threadList.innerHTML = `<small class="text-muted text-center d-block py-3" data-i18n="ai_chat_no_conversations">No past conversations</small>`;
        if (typeof applyTranslations === "function") applyTranslations();
        return;
      }

      let html = "";
      conversations.forEach((conv) => {
        const activeClass = conv.id === _aiChatConversationId ? "btn-secondary active" : "btn-outline-secondary";
        html += `
          <div class="d-flex align-items-center justify-content-between mb-1 group-hover">
            <button class="btn ${activeClass} btn-sm text-start text-truncate flex-grow-1 me-1" style="font-size:0.85rem;" type="button" onclick="_switchAIChatConversation(${conv.id})">
              <i class="bi bi-chat-text me-1"></i> ${conv.title || "Conversation"}
            </button>
            <button class="btn btn-sm btn-link text-danger p-0 ms-1" type="button" title="Delete" onclick="_deleteAIChatConversation(${conv.id})">
              <i class="bi bi-x-circle"></i>
            </button>
          </div>
        `;
      });
      threadList.innerHTML = html;
    })
    .catch(() => {});
}

function _switchAIChatConversation(id) {
  _aiChatConversationId = id;
  _fetchAIChatConversations();

  fetch(`/api/financial-advisor/ai/conversations/${id}/`)
    .then((res) => res.json())
    .then((data) => {
      const conv = data && data.conversation;
      if (!conv) return;

      const titleEl = document.getElementById("ai-chat-active-title");
      if (titleEl) titleEl.textContent = conv.title || "AI Financial Advisor";

      const msgContainer = document.getElementById("ai-chat-message-list");
      if (!msgContainer) return;
      msgContainer.innerHTML = "";

      const messages = conv.messages || [];
      if (messages.length === 0) {
        msgContainer.innerHTML = `
          <div class="text-center py-5" id="ai-chat-empty-state">
            <i class="bi bi-chat-left-dots fs-1 mb-3" style="color:var(--text-secondary); opacity:0.5;"></i>
            <p style="color:var(--text-secondary);" data-i18n="ai_chat_empty_state">Start a conversation with AI Financial Advisor!</p>
          </div>
        `;
        return;
      }

      messages.forEach((msg) => {
        _appendAIChatMessageBubble(msg.role, msg.content, false, false, msg.tool_calls || []);
      });
    })
    .catch(() => {});
}

function _deleteAIChatConversation(id) {
  fetch(`/api/financial-advisor/ai/conversations/${id}/`, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": _getAIChatCSRFToken(),
    },
  })
    .then(() => {
      if (_aiChatConversationId === id) {
        _startNewAIChatConversation();
      } else {
        _fetchAIChatConversations();
      }
    })
    .catch(() => {});
}

function _handleAIChatSubmit(e) {
  e.preventDefault();
  if (_aiChatLoading) return;

  const inputEl = document.getElementById("ai-chat-input");
  if (!inputEl) return;

  const userText = inputEl.value.trim();
  if (!userText) return;

  const domainSelect = document.getElementById("ai-chat-domain-select");
  const questionDomain = domainSelect ? domainSelect.value : "business_data_analysis";

  inputEl.value = "";
  inputEl.style.height = "auto";
  _appendAIChatMessageBubble("user", userText);
  _setAIChatLoading(true);

  fetch("/api/financial-advisor/ai/chat/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": _getAIChatCSRFToken(),
    },
    body: JSON.stringify({
      message: userText,
      conversation_id: _aiChatConversationId,
      question_domain: questionDomain,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      _setAIChatLoading(false);
      if (!data.ok && data.error_key === "ai_chat_disabled_desc") {
        _appendAIChatMessageBubble("assistant", typeof t === "function" ? t("ai_chat_disabled_desc") : "AI Assistant is disabled.", true, true);
        _updateAIChatStatusBadge(false);
        return;
      }

      if (data.conversation_id) {
        _aiChatConversationId = data.conversation_id;
        _fetchAIChatConversations();
      }

      if (data.message && data.message.content) {
        _appendAIChatMessageBubble("assistant", data.message.content, true, false, data.message.tool_calls || []);
        _updateAIChatStatusBadge(true);
      } else if (data.error) {
        _appendAIChatMessageBubble("assistant", data.error, true, true);
      }
    })
    .catch((err) => {
      _setAIChatLoading(false);
      const localizedErr = typeof t === "function" ? t("ai_error_provider_unavailable") : "Unable to connect to AI service.";
      const displayMsg = err && err.message ? `${localizedErr}\n(${err.message})` : localizedErr;
      _appendAIChatMessageBubble("assistant", displayMsg, true, true);
      _updateAIChatStatusBadge(false);
    });
}

function _handleAIChatClear() {
  if (!_aiChatConversationId) {
    _startNewAIChatConversation();
    return;
  }
  _deleteAIChatConversation(_aiChatConversationId);
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
    bubble.style.background = "rgba(13, 110, 253, 0.12)";
    bubble.style.color = "var(--text-primary)";
    bubble.style.border = "1px solid rgba(13, 110, 253, 0.35)";
    bubble.style.backdropFilter = "blur(8px)";
    bubble.style.borderBottomRightRadius = "2px";
  } else if (isError) {
    bubble.style.background = "rgba(220, 53, 69, 0.12)";
    bubble.style.color = "var(--text-primary)";
    bubble.style.border = "1px solid rgba(220, 53, 69, 0.35)";
    bubble.style.backdropFilter = "blur(8px)";
    bubble.style.borderBottomLeftRadius = "2px";
  } else {
    bubble.style.background = "rgba(255, 255, 255, 0.04)";
    bubble.style.color = "var(--text-primary)";
    bubble.style.border = "1px solid var(--border-color)";
    bubble.style.backdropFilter = "blur(8px)";
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

      const defaultText = `Executing ${toolName}...`;
      toolDiv.innerHTML = `<i class="bi ${iconClass}"></i> <span data-i18n="${i18nKey}">${defaultText}</span>`;
      bubble.appendChild(toolDiv);
    });
  }

  const textBody = document.createElement("div");
  textBody.style.wordBreak = "break-word";
  textBody.innerHTML = _renderAIChatFormattedContent(content);

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

function _renderAIChatFormattedContent(content) {
  if (!content) return "";
  let text = String(content);

  text = text
    .replace(/portfolio_optimizer_asset_cash/g, typeof t === "function" ? t("portfolio_optimizer_asset_cash", "Cash") : "Cash")
    .replace(/portfolio_optimizer_asset_certificates/g, typeof t === "function" ? t("portfolio_optimizer_asset_certificates", "Bank Certificates") : "Bank Certificates")
    .replace(/portfolio_optimizer_asset_gold/g, typeof t === "function" ? t("portfolio_optimizer_asset_gold", "Gold") : "Gold")
    .replace(/portfolio_optimizer_asset_real_estate/g, typeof t === "function" ? t("portfolio_optimizer_asset_real_estate", "Real Estate") : "Real Estate")
    .replace(/portfolio_optimizer_asset_vehicles/g, typeof t === "function" ? t("portfolio_optimizer_asset_vehicles", "Vehicles") : "Vehicles")
    .replace(/portfolio_optimizer_asset_other_assets/g, typeof t === "function" ? t("portfolio_optimizer_asset_other_assets", "Other Assets") : "Other Assets");

  let safe = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  safe = safe.replace(/(?:(?:\|.+?\|\r?\n)+)/g, function(tableBlock) {
    const lines = tableBlock.trim().split(/\r?\n/);
    if (lines.length < 2) return tableBlock;
    let html = '<div class="table-responsive my-2"><table class="table table-sm table-bordered align-middle text-start mb-0" style="border-color:var(--border-color); background:transparent;">';
    let isHeader = true;
    lines.forEach(line => {
      if (line.includes('---')) return;
      const cells = line.split('|').filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      if (cells.length === 0) return;
      if (isHeader) {
        html += '<thead><tr style="background:rgba(255,255,255,0.05);">';
        cells.forEach(c => html += `<th class="px-2 py-1">${c.trim()}</th>`);
        html += '</tr></thead><tbody>';
        isHeader = false;
      } else {
        html += '<tr>';
        cells.forEach(c => html += `<td class="px-2 py-1">${c.trim()}</td>`);
        html += '</tr>';
      }
    });
    html += '</tbody></table></div>';
    return html;
  });

  safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  safe = safe.replace(/\*(.*?)\*/g, 'em>$1</em>');
  safe = safe.replace(/^###\s+(.*$)/gim, '<h6 class="fw-bold mt-2 mb-1" style="color:var(--text-primary);">$1</h6>');
  safe = safe.replace(/^##\s+(.*$)/gim, '<h5 class="fw-bold mt-2 mb-1" style="color:var(--text-primary);">$1</h5>');
  safe = safe.replace(/^\s*[\-\*]\s+(.*$)/gim, '<li class="ms-3 mb-1">$1</li>');
  safe = safe.replace(/\n/g, '<br>');

  return safe;
}

function _updateAIChatInputPlaceholder(domain) {
  const inputEl = document.getElementById("ai-chat-input");
  if (!inputEl) return;

  const key = domain === "app_features_architecture"
    ? "ai_chat_input_placeholder_app_features"
    : "ai_chat_input_placeholder_business";

  inputEl.setAttribute("data-i18n-placeholder", key);
  const fallback = domain === "app_features_architecture"
    ? "Ask about application features, codebase, or architecture..."
    : "Ask a financial or business data question...";

  inputEl.placeholder = typeof t === "function" ? t(key, fallback) : fallback;
}

window.loadAIChat = loadAIChat;
window._switchAIChatConversation = _switchAIChatConversation;
window._deleteAIChatConversation = _deleteAIChatConversation;
