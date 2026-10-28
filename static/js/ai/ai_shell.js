"use strict";

/**
 * AI Workspace — Shell & Input
 * Renders the two-panel workspace layout (conversations on the left, chat in the center) and wires the message textarea.
 * Depends on: ai_core.js, ai_status.js, ai_conversations.js, ai_messages.js,
 * ai_chat_submit.js
 */

async function renderAI() {
  const mainContent = document.getElementById("main-content");
  if (!mainContent) return;

  mainContent.innerHTML = `
    <div class="ai-workspace" si-modern-card>
      <!-- Dashboard Header -->
      <div class="ai-ws-header" id="ai-ws-header">
        <div class="ai-ws-header-left">
          <div class="ai-ws-header-brand">
            <i class="bi bi-cpu"></i>
            <span data-i18n="nav_wealthflow_ai">WealthFlow AI</span>
          </div>
          <div class="ai-ws-header-divider"></div>
          <div class="ai-ws-header-stats" id="ai-ws-header-stats">
            <div class="ai-ws-stat-chip" id="ai-ws-chip-status-container"><i class="bi bi-circle-fill"></i> <span class="stat-value" id="ai-ws-chip-status">—</span></div>
          </div>
        </div>
        <div class="ai-ws-header-actions">
          <button class="btn btn-sm btn-outline-secondary align-items-center gap-1 ai-ws-sidebar-toggle" onclick="_toggleAISidebar()" title="${_aiT("ai_ws_toggle_sidebar", "Toggle Sidebar")}">
            <i class="bi bi-list"></i>
          </button>
        </div>
      </div>

      <!-- Sidebar overlay (mobile) -->
      <div id="ai-ws-sidebar-overlay" class="ai-ws-overlay" onclick="_toggleAISidebar()"></div>

      <!-- Body -->
      <div class="ai-ws-body">
        <!-- Left Panel -->
        <div class="ai-ws-left">
          <div class="ai-ws-left-actions">
            <button class="ai-ws-new-chat-btn" onclick="_startNewAIChatConversation()">
              <i class="bi bi-plus-lg"></i>
              <span data-i18n="ai_chat_new_chat_btn">New Chat</span>
            </button>
          </div>
          <div class="ai-ws-conv-scroll" id="ai-ws-conv-list">
            <!-- Populated via JS -->
          </div>
          <div class="ai-ws-left-future">
            <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-pinned-chats" onclick="openPinnedChatsModal()" style="cursor: pointer;">
              <div class="ai-ws-future-card-left">
                <i class="bi bi-pin-angle-fill text-primary"></i>
                <span data-i18n="ai_ws_pinned_chats">Pinned Chats</span>
              </div>
              <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
            </div>
            <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-learned-answers" onclick="openLearnedAnswersModal()" style="cursor: pointer;">
              <div class="ai-ws-future-card-left">
                <i class="bi bi-hand-thumbs-up text-primary"></i>
                <span data-i18n="ai_la_card">Learned Answers</span>
              </div>
              <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
            </div>
            <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-memory" onclick="openAIMemoryModal()" style="cursor: pointer;">
              <div class="ai-ws-future-card-left">
                <i class="bi bi-journal-text text-primary"></i>
                <span data-i18n="ai_mem_card">AI Memory</span>
              </div>
              <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
            </div>
            <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-saved-prompts" onclick="openPromptLibraryModal()" style="cursor: pointer;">
              <div class="ai-ws-future-card-left">
                <i class="bi bi-bookmark text-primary"></i>
                <span data-i18n="ai_ws_saved_prompts">Saved Prompts</span>
              </div>
              <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
            </div>
            <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-knowledge-search" onclick="openKnowledgeSearchModal()" style="cursor: pointer;">
              <div class="ai-ws-future-card-left">
                <i class="bi bi-search text-primary"></i>
                <span data-i18n="ai_ws_knowledge_search">Knowledge Search</span>
              </div>
              <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
            </div>
          </div>
          <div id="ai-ws-ext-left"></div>
        </div>

        <!-- Center Workspace -->
        <div class="ai-ws-center">
          <!-- Messages / Platform Workspace area -->
          <div class="ai-ws-messages" id="ai-ws-messages">
            <!-- Populated via JS -->
          </div>

          <!-- Workspace Command Center Input Area -->
          <div class="ai-ws-input-area">
            <div class="ai-ws-input-box">
              <div class="ai-ws-input-topbar">
                <select id="ai-ws-domain-select" class="ai-ws-domain-select">
                  <option value="business_data_analysis" data-i18n="ai_domain_business_data">Business / Data Analysis</option>
                  <option value="app_features_architecture" data-i18n="ai_domain_app_features">Application Features &amp; Architecture</option>
                </select>
                <div class="btn-group btn-group-sm ai-ws-mode-switch" role="group" id="ai-ws-mode-switch" aria-label="${_aiT("ai_mode_label", "Chat mode")}">
                  <button type="button" class="btn btn-outline-primary" id="ai-ws-mode-ask" data-mode="ask" aria-pressed="true" onclick="_aiSetChatMode('ask')" data-i18n="ai_mode_ask">Ask</button>
                  <button type="button" class="btn btn-outline-primary" id="ai-ws-mode-agent" data-mode="agent" aria-pressed="false" onclick="_aiSetChatMode('agent')" data-i18n="ai_mode_agent">Agent</button>
                </div>
                <small class="text-muted ai-ws-mode-hint" id="ai-ws-mode-hint"></small>
                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2 ms-auto me-2" id="ai-ws-btn-prompt-lib" onclick="openPromptLibraryModal()" title="Prompt Library">
                  <i class="bi bi-chat-left-quote me-1"></i> <span data-i18n="ai_ws_prompt_library_title">Prompt Library</span>
                </button>
              </div>

              <textarea id="ai-ws-input" class="ai-ws-textarea" rows="1" placeholder="${_aiT("ai_chat_input_placeholder_business", "Ask WealthFlow AI a question about business metrics, financial planning, or architecture...")}" onkeydown="_handleInputKeydown(event)"></textarea>
              <div class="ai-ws-input-bottombar">
                <div class="ai-ws-input-hints">
                  <span><kbd>Enter</kbd> send</span>
                  <span><kbd>Shift+Enter</kbd> newline</span>
                </div>
                <button type="button" class="btn btn-sm btn-outline-secondary" id="ai-ws-stt-btn" hidden onclick="window.WFSpeech.toggleRecording()" title="${_aiT("speech_dictate", "Dictate")}" aria-label="${_aiT("speech_dictate", "Dictate")}"><i class="bi bi-mic"></i></button>
                <button type="button" class="btn btn-sm btn-outline-secondary" id="ai-ws-tts-btn" hidden onclick="window.WFSpeech.speakLast()" title="${_aiT("speech_read_answer", "Read latest answer aloud")}" aria-label="${_aiT("speech_read_answer", "Read latest answer aloud")}"><i class="bi bi-volume-up"></i></button>
                <button class="ai-ws-send-btn" onclick="_handleAIChatSubmit()" title="${_aiT("ai_chat_send_button", "Send")}">
                  <span data-i18n="ai_chat_send_button">Send</span>
                  <i class="bi bi-send"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  _applyTranslations();
  _initTextareaAutogrow();
  _renderExtensions();
  window.WFSpeech?.init();
  _aiLoadChatMode();

  await _fetchAIWorkspaceStatus();
  await _fetchAIChatConversations();

  const savedConvId = localStorage.getItem("wf_active_ai_conv");
  if (savedConvId) {
    await _switchAIChatConversation(savedConvId);
  } else {
    _renderEmptyState();
  }
}

function _initTextareaAutogrow() {
  const textarea = document.getElementById("ai-ws-input");
  if (!textarea) return;
  textarea.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 140) + "px";
  });
}

function _handleInputKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    _handleAIChatSubmit();
  }
}

function loadAIChat() {
  renderAI();
}

function _toggleAISidebar() {
  const left = document.querySelector(".ai-ws-left");
  const overlay = document.getElementById("ai-ws-sidebar-overlay");
  if (!left || !overlay) return;
  const isOpen = left.classList.contains("ai-ws-left--open");
  if (isOpen) {
    left.classList.remove("ai-ws-left--open");
    overlay.classList.remove("ai-ws-overlay--visible");
  } else {
    left.classList.add("ai-ws-left--open");
    overlay.classList.add("ai-ws-overlay--visible");
  }
}

window.renderAI = renderAI;
window.loadAIChat = loadAIChat;
window._handleInputKeydown = _handleInputKeydown;
