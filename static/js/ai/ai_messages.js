"use strict";

/**
 * AI Workspace — Messages
 * Renders the empty-state welcome screen, individual chat message bubbles,
 * and appends new messages to the conversation.
 * Depends on: ai_core.js, ai_markdown.js
 */

function _renderEmptyState() {
  const messagesContainer = document.getElementById("ai-ws-messages");
  if (!messagesContainer) return;

  if (_aiState.conversationId) return;

  messagesContainer.innerHTML = `
    <div class="ai-ws-empty-state">
      <div class="ai-ws-empty-hero">
        <i class="bi bi-cpu ai-ws-empty-icon"></i>
        <div class="ai-ws-empty-title" data-i18n="ai_ws_welcome_title">Welcome to WealthFlow AI</div>
        <div class="ai-ws-empty-desc" data-i18n="ai_ws_welcome_desc">Your cross-application intelligence workspace for business data reasoning, financial planning insights, and application architecture understanding.</div>
      </div>

      <div class="ai-ws-suggestions-title" data-i18n="ai_ws_suggestions_title">Suggested Quick Analyses</div>
      <div class="ai-ws-empty-suggestions">
        <div class="ai-ws-suggestion-chip" onclick="_aiSuggestionClick('ai_ws_suggest_networth', 'What is my net worth?')">
          <i class="bi bi-cash-stack"></i>
          <span data-i18n="ai_ws_suggest_networth">What is my net worth?</span>
        </div>
        <div class="ai-ws-suggestion-chip" onclick="_aiSuggestionClick('ai_ws_suggest_portfolio', 'Analyze my portfolio')">
          <i class="bi bi-pie-chart"></i>
          <span data-i18n="ai_ws_suggest_portfolio">Analyze my portfolio</span>
        </div>
        <div class="ai-ws-suggestion-chip" onclick="_aiSuggestionClick('ai_ws_suggest_expenses', 'Show expense trends')">
          <i class="bi bi-graph-up"></i>
          <span data-i18n="ai_ws_suggest_expenses">Show expense trends</span>
        </div>
        <div class="ai-ws-suggestion-chip" onclick="_aiSuggestionClick('ai_ws_suggest_cashflow', 'Review cash flow')">
          <i class="bi bi-arrow-left-right"></i>
          <span data-i18n="ai_ws_suggest_cashflow">Review cash flow</span>
        </div>
      </div>
    </div>
  `;
  _applyTranslations();
}

function _aiSuggestionClick(i18nKey, defaultText) {
  const input = document.getElementById("ai-ws-input");
  if (input) {
    input.value = _aiT(i18nKey, defaultText);
    _handleAIChatSubmit();
  }
}

function _renderMessageHTML(role, content, toolCalls, sources, timestamp, messageId, feedback) {
  const isUser = role === "user";
  const roleI18n = isUser ? "ai_ws_role_you" : "ai_ws_role_assistant";
  const roleName = isUser ? "You" : "WealthFlow AI";
  const icon = isUser ? "bi-person" : "bi-cpu";
  const timeStr = _formatDate(timestamp || new Date().toISOString());

  let toolBadges = "";
  if (toolCalls && toolCalls.length > 0) {
    toolBadges = '<div class="ai-ws-tool-badges">';
    toolCalls.forEach((tc) => {
      const toolName = tc.tool || tc.name || "tool";
      const statusIcon =
        tc.status === "success" || !tc.status ? "bi-check-circle-fill" : "bi-x-circle-fill";
      toolBadges += `<span class="ai-ws-tool-badge"><i class="bi ${statusIcon}"></i> ${toolName}</span>`;
    });
    toolBadges += "</div>";
  }

  const processedContent = _renderMarkdown(content);
  const feedbackBar =
    !isUser && messageId && content ? _renderFeedbackBar(messageId, feedback) : "";

  return `
    <div class="ai-ws-msg">
      <div class="ai-ws-msg-avatar ${isUser ? "user" : "assistant"}">
        <i class="bi ${icon}"></i>
      </div>
      <div class="ai-ws-msg-body">
        <div class="ai-ws-msg-role">
          <span data-i18n="${roleI18n}">${roleName}</span>
          <span class="msg-time">${timeStr}</span>
        </div>
        ${toolBadges}
        <div class="ai-ws-msg-content">${processedContent}</div>
        ${feedbackBar}
      </div>
    </div>
  `;
}

function _appendMessage(role, content, toolCalls, sources, timestamp, messageId, feedback) {
  const container = document.getElementById("ai-ws-messages");
  if (!container) return;

  if (!_aiState.conversationId && container.querySelector(".ai-ws-empty-state")) {
    container.innerHTML = "";
  }

  container.innerHTML += _renderMessageHTML(
    role,
    content,
    toolCalls,
    sources,
    timestamp,
    messageId,
    feedback
  );
  container.scrollTop = container.scrollHeight;
  _applyTranslations();
}

window._aiSuggestionClick = _aiSuggestionClick;
