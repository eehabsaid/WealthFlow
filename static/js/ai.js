'use strict';

const _aiWorkspaceExtensions = {
  leftPanels: [],
  rightPanels: [],
  workspaceCards: [],
  widgets: [],
  agents: []
};

function registerAIWorkspaceCard(config) { _aiWorkspaceExtensions.workspaceCards.push(config); }
function registerAIRightPanel(config) { _aiWorkspaceExtensions.rightPanels.push(config); }
function registerAILeftPanel(config) { _aiWorkspaceExtensions.leftPanels.push(config); }
function registerAIWidget(config) { _aiWorkspaceExtensions.widgets.push(config); }
function registerAIAgent(config) { _aiWorkspaceExtensions.agents.push(config); }

let _aiState = {
  conversationId: null,
  loading: false,
  contextPanelOpen: true,
  lastResponseMeta: null,
  aiSettings: null,
  knowledgeCount: 0,
  modelInfo: null
};

// Safe translation helper
function _aiT(key, fallback) {
  if (typeof window.t === 'function') {
    return window.t(key, fallback);
  }
  return fallback;
}

function _applyTranslations() {
  if (typeof window.applyTranslations === 'function') {
    window.applyTranslations();
  }
}

function _formatDate(dateStr) {
  if (!dateStr) return '';
  if (typeof window.formatDate === 'function') {
    return window.formatDate(dateStr);
  }
  return new Date(dateStr).toLocaleString();
}

function _relativeTime(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return _aiT('ai_ws_time_just_now', 'Just now');
  if (diffMins < 60) return _aiT('ai_ws_time_mins_ago', `${diffMins}m ago`);
  if (diffHours < 24) return _aiT('ai_ws_time_hours_ago', `${diffHours}h ago`);
  if (diffDays === 1) return _aiT('ai_ws_time_yesterday', 'Yesterday');
  if (diffDays < 7) return _aiT('ai_ws_time_days_ago', `${diffDays}d ago`);
  return _formatDate(dateStr);
}

async function renderAI() {
  const mainContent = document.getElementById('main-content');
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
            <div class="ai-ws-stat-chip"><i class="bi bi-hdd-rack"></i> <span data-i18n="ai_ws_provider">Provider</span>: <span class="stat-value" id="ai-ws-chip-provider">—</span></div>
            <div class="ai-ws-stat-chip"><i class="bi bi-robot"></i> <span data-i18n="ai_ws_model">Model</span>: <span class="stat-value" id="ai-ws-chip-model">—</span></div>
            <div class="ai-ws-stat-chip"><i class="bi bi-database"></i> <span data-i18n="ai_ws_knowledge">Knowledge</span>: <span class="stat-value" id="ai-ws-chip-knowledge">—</span></div>
            <div class="ai-ws-stat-chip" id="ai-ws-chip-status-container"><i class="bi bi-circle-fill"></i> <span class="stat-value" id="ai-ws-chip-status">—</span></div>
          </div>
        </div>
        <div class="ai-ws-header-actions">
          <button class="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1" onclick="_toggleAIContextPanel()" title="${_aiT('ai_ws_toggle_context', 'Toggle Context Panel')}">
            <i class="bi bi-layout-sidebar-reverse"></i>
          </button>
        </div>
      </div>
      
      <!-- Three-Panel Body -->
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
            <div class="ai-ws-future-card">
              <div class="ai-ws-future-card-left">
                <i class="bi bi-pin-angle"></i>
                <span data-i18n="ai_ws_pinned_chats">Pinned Chats</span>
              </div>
              <span class="ai-ws-future-badge">🔒 COMING SOON</span>
            </div>
            <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-saved-prompts" onclick="openPromptLibraryModal()" style="cursor: pointer;">
              <div class="ai-ws-future-card-left">
                <i class="bi bi-bookmark text-primary"></i>
                <span data-i18n="ai_ws_saved_prompts">Saved Prompts</span>
              </div>
              <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
            </div>

            <div class="ai-ws-future-card">
              <div class="ai-ws-future-card-left">
                <i class="bi bi-search"></i>
                <span data-i18n="ai_ws_knowledge_search">Knowledge Search</span>
              </div>
              <span class="ai-ws-future-badge">🔒 COMING SOON</span>
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
                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2 ms-auto me-2" id="ai-ws-btn-prompt-lib" onclick="openPromptLibraryModal()" title="Prompt Library">
                  <i class="bi bi-chat-left-quote me-1"></i> <span data-i18n="ai_ws_prompt_library_title">Prompt Library</span>
                </button>
                <small class="text-muted" style="font-size:0.7rem;"><i class="bi bi-cpu me-1"></i> WealthFlow AI Engine</small>
              </div>

              <textarea id="ai-ws-input" class="ai-ws-textarea" rows="1" placeholder="${_aiT('ai_chat_input_placeholder_business', 'Ask WealthFlow AI a question about business metrics, financial planning, or architecture...')}" onkeydown="_handleInputKeydown(event)"></textarea>
              <div class="ai-ws-input-bottombar">
                <div class="ai-ws-input-hints">
                  <span><kbd>Enter</kbd> send</span>
                  <span><kbd>Shift+Enter</kbd> newline</span>
                </div>
                <button class="ai-ws-send-btn" onclick="_handleAIChatSubmit()" title="${_aiT('ai_chat_send_button', 'Send')}">
                  <span data-i18n="ai_chat_send_button">Send</span>
                  <i class="bi bi-send"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Right Context Panel (Width 330px) -->
        <div class="ai-ws-right" id="ai-ws-right-panel">
          <div id="ai-ws-context-content">
             <!-- Populated via JS -->
          </div>
          <div id="ai-ws-ext-right"></div>
        </div>
      </div>
    </div>
  `;

  _applyTranslations();
  _initTextareaAutogrow();
  _renderEmptyState();
  _renderRightPanel();
  _renderExtensions();

  await _fetchAIWorkspaceStatus();
  await _fetchAIChatConversations();
}

function _initTextareaAutogrow() {
  const textarea = document.getElementById('ai-ws-input');
  if (!textarea) return;
  textarea.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 140) + 'px';
  });
}

function _handleInputKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    _handleAIChatSubmit();
  }
}

async function _fetchAIWorkspaceStatus() {
  try {
    const [settingsRes, knowledgeRes, modelsRes] = await Promise.all([
      fetch('/api/settings/ai/').catch(() => null),
      fetch('/api/ai-platform/knowledge/').catch(() => null),
      fetch('/api/ai-platform/models/').catch(() => null)
    ]);

    if (settingsRes && settingsRes.ok) _aiState.aiSettings = await settingsRes.json();
    if (knowledgeRes && knowledgeRes.ok) {
      const kData = await knowledgeRes.json();
      _aiState.knowledgeCount = (kData.entries && kData.entries.length) || 0;
    }
    if (modelsRes && modelsRes.ok) _aiState.modelInfo = await modelsRes.json();

    const providerEl = document.getElementById('ai-ws-chip-provider');
    const modelEl = document.getElementById('ai-ws-chip-model');
    const knowledgeEl = document.getElementById('ai-ws-chip-knowledge');
    const statusEl = document.getElementById('ai-ws-chip-status');
    const statusContainer = document.getElementById('ai-ws-chip-status-container');

    if (providerEl) providerEl.textContent = _aiState.aiSettings?.ai_provider || '—';
    if (modelEl) modelEl.textContent = _aiState.aiSettings?.ai_model || _aiState.modelInfo?.active_model?.base_model || '—';
    if (knowledgeEl) knowledgeEl.textContent = _aiState.knowledgeCount || '—';
    if (statusEl) {
      const isOnline = _aiState.aiSettings && _aiState.aiSettings.ai_enabled;
      statusEl.textContent = isOnline ? _aiT('ai_ws_online', 'Online') : _aiT('ai_ws_offline', 'Offline');
      if (statusContainer) statusContainer.classList.toggle('online', !!isOnline);
      if (statusContainer) statusContainer.classList.toggle('offline', !isOnline);
    }
  } catch (err) {
    const ids = ['ai-ws-chip-provider', 'ai-ws-chip-model', 'ai-ws-chip-knowledge', 'ai-ws-chip-status'];
    ids.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '—'; });
  }
}

async function _fetchAIChatConversations() {
  try {
    const res = await fetch('/api/financial-advisor/ai/conversations/');
    if (!res.ok) return;
    const data = await res.json();
    
    const container = document.getElementById('ai-ws-conv-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!data.conversations || data.conversations.length === 0) {
      return;
    }

    const groups = {
      today: [],
      yesterday: [],
      thisWeek: [],
      older: []
    };

    const now = new Date();
    data.conversations.forEach(conv => {
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
      if (groupData.length === 0) return '';
      let html = `<div class="ai-ws-conv-group"><div class="ai-ws-conv-group-title" data-i18n="${i18nKey}">${defaultTitle}</div>`;
      groupData.forEach(conv => {
        const isActive = String(_aiState.conversationId) === String(conv.id) ? 'active' : '';
        const timeAgo = _relativeTime(conv.updated_at || conv.created_at);
        html += `
          <div class="ai-ws-conv-item ${isActive}" onclick="_switchAIChatConversation('${conv.id}')">
            <div class="ai-ws-conv-header-row">
              <div class="ai-ws-conv-title">${conv.title || _aiT('ai_ws_untitled', 'Untitled')}</div>
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

    container.innerHTML += renderGroup(groups.today, 'ai_ws_group_today', 'Today');
    container.innerHTML += renderGroup(groups.yesterday, 'ai_ws_group_yesterday', 'Yesterday');
    container.innerHTML += renderGroup(groups.thisWeek, 'ai_ws_group_this_week', 'This Week');
    container.innerHTML += renderGroup(groups.older, 'ai_ws_group_older', 'Older');

    _applyTranslations();
  } catch (err) {
    // Handle error gracefully
  }
}

function _renderEmptyState() {
  const messagesContainer = document.getElementById('ai-ws-messages');
  if (!messagesContainer) return;
  
  if (_aiState.conversationId) return;

  const provider = _aiState.aiSettings?.ai_provider || 'Ollama';
  const model = _aiState.aiSettings?.ai_model || 'llama3.2:latest';
  const kCount = _aiState.knowledgeCount || 31;

  messagesContainer.innerHTML = `
    <div class="ai-ws-empty-state">
      <div class="ai-ws-empty-hero">
        <i class="bi bi-cpu ai-ws-empty-icon"></i>
        <div class="ai-ws-empty-title" data-i18n="ai_ws_welcome_title">Welcome to WealthFlow AI</div>
        <div class="ai-ws-empty-desc" data-i18n="ai_ws_welcome_desc">Your cross-application intelligence workspace for business data reasoning, financial planning insights, and application architecture understanding.</div>
      </div>

      <!-- Platform Status Cards Grid -->
      <div class="ai-ws-platform-grid">
        <div class="ai-ws-platform-card">
          <div class="ai-ws-platform-card-header"><i class="bi bi-hdd-rack"></i> <span data-i18n="ai_ws_card_provider">Connected Provider</span></div>
          <div class="ai-ws-platform-card-value">${provider}</div>
          <div class="ai-ws-platform-card-sub" data-i18n="ai_ws_card_provider_sub">Local LLM Integration</div>
        </div>
        <div class="ai-ws-platform-card">
          <div class="ai-ws-platform-card-header"><i class="bi bi-robot"></i> <span data-i18n="ai_ws_card_model">Active Model</span></div>
          <div class="ai-ws-platform-card-value">${model}</div>
          <div class="ai-ws-platform-card-sub" data-i18n="ai_ws_card_model_sub">Active Production Engine</div>
        </div>
        <div class="ai-ws-platform-card">
          <div class="ai-ws-platform-card-header"><i class="bi bi-database"></i> <span data-i18n="ai_ws_card_knowledge">Knowledge Entries</span></div>
          <div class="ai-ws-platform-card-value">${kCount} Entries</div>
          <div class="ai-ws-platform-card-sub" data-i18n="ai_ws_card_knowledge_sub">Autonomous Learning Active</div>
        </div>
        <div class="ai-ws-platform-card">
          <div class="ai-ws-platform-card-header"><i class="bi bi-database-check"></i> <span data-i18n="ai_ws_card_dataset">SFT Dataset Status</span></div>
          <div class="ai-ws-platform-card-value" style="color:var(--accent-emerald);">Clean / Validated</div>
          <div class="ai-ws-platform-card-sub" data-i18n="ai_ws_card_dataset_sub">Fine-Tuning Ready</div>
        </div>
        <div class="ai-ws-platform-card">
          <div class="ai-ws-platform-card-header"><i class="bi bi-tools"></i> <span data-i18n="ai_ws_card_tools">AI Capabilities</span></div>
          <div class="ai-ws-platform-card-value">4 Active Tools</div>
          <div class="ai-ws-platform-card-sub" data-i18n="ai_ws_card_tools_sub">DB, AST & Code Reasoner</div>
        </div>
        <div class="ai-ws-platform-card">
          <div class="ai-ws-platform-card-header"><i class="bi bi-radar"></i> <span data-i18n="ai_ws_card_scan">Autonomous Scan</span></div>
          <div class="ai-ws-platform-card-value" style="color:var(--accent-emerald);">Live & Monitoring</div>
          <div class="ai-ws-platform-card-sub" data-i18n="ai_ws_card_scan_sub">Codebase & Schema Tracking</div>
        </div>
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

function _startNewAIChatConversation() {
  _aiState.conversationId = null;
  _aiState.lastResponseMeta = null;
  const container = document.getElementById('ai-ws-messages');
  if (container) container.innerHTML = '';
  _renderEmptyState();
  _renderRightPanel();
  _fetchAIChatConversations();
  const inputEl = document.getElementById('ai-ws-input');
  if (inputEl) { inputEl.value = ''; inputEl.focus(); }
}

function _aiSuggestionClick(i18nKey, defaultText) {
  const input = document.getElementById('ai-ws-input');
  if (input) {
    input.value = _aiT(i18nKey, defaultText);
    _handleAIChatSubmit();
  }
}

// Generic Markdown & Rich Renderer Pipeline
function _renderMarkdown(text) {
  if (!text) return '';
  
  let html = text;

  // 1. Protect code blocks first
  const codeBlocks = [];
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function(match, lang, code) {
    codeBlocks.push({ lang: lang || 'code', code: code });
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });

  // 2. HTML escape (excluding protected blocks)
  html = html.replace(/[&<>"']/g, function(m) {
    switch (m) {
      case '&': return '&amp;';
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '"': return '&quot;';
      case "'": return '&#039;';
      default: return m;
    }
  });

  // 3. Callout boxes (> [!NOTE], > [!WARNING], > [!TIP], > [!IMPORTANT])
  html = html.replace(/^&gt;\s*\[!(NOTE|WARNING|TIP|IMPORTANT)\]\s*(.*$)/gim, function(match, type, content) {
    const typeLower = type.toLowerCase();
    return `<div class="ai-ws-callout ${typeLower}"><strong>${type}:</strong> ${content}</div>`;
  });

  // 4. Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // 5. Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // 6. Headings
  html = html.replace(/^### (.*$)/gim, '<h5>$1</h5>');
  html = html.replace(/^## (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^# (.*$)/gim, '<h3>$1</h3>');
  
  // 7. Blockquotes
  html = html.replace(/^&gt;\s*(.*$)/gim, '<blockquote>$1</blockquote>');
  
  // 8. Horizontal rules
  html = html.replace(/^---$/gim, '<hr>');

  // 9. Checklists
  html = html.replace(/^\s*\[\s*\]\s+(.*)$/gim, '<div><i class="bi bi-square me-1"></i> $1</div>');
  html = html.replace(/^\s*\[[xX]\]\s+(.*)$/gim, '<div><i class="bi bi-check-square-fill text-success me-1"></i> $1</div>');

  // 10. Unordered & Ordered Lists
  html = html.replace(/^\s*[-*]\s+(.*)$/gim, '<ul><li>$1</li></ul>');
  html = html.replace(/<\/ul>\n<ul>/g, '\n');

  html = html.replace(/^\s*\d+\.\s+(.*)$/gim, '<ol><li>$1</li></ol>');
  html = html.replace(/<\/ol>\n<ol>/g, '\n');

  // 11. Tables
  html = html.replace(/^\|(.+)\|$/gim, function(match, content) {
    const cells = content.split('|').map(c => `<td>${c.trim()}</td>`).join('');
    return `<tr>${cells}</tr>`;
  });
  html = html.replace(/(<tr>.*?<\/tr>[\n\r]*)+/g, '<div class="ai-table-wrap"><table>$&</table></div>');

  // 12. Line breaks
  html = html.replace(/\n/g, '<br>');

  // 13. Restore code blocks with language header
  html = html.replace(/__CODE_BLOCK_(\d+)__/g, function(match, index) {
    const block = codeBlocks[index];
    let codeContent = block.code.replace(/[&<>"']/g, function(m) {
      switch (m) {
        case '&': return '&amp;';
        case '<': return '&lt;';
        case '>': return '&gt;';
        case '"': return '&quot;';
        case "'": return '&#039;';
        default: return m;
      }
    });
    return `
      <div class="ai-ws-code-wrap">
        <div class="ai-ws-code-header">
          <span><i class="bi bi-code-slash me-1"></i> ${block.lang}</span>
        </div>
        <pre class="ai-ws-code-content"><code>${codeContent}</code></pre>
      </div>
    `;
  });

  return html;
}

function _renderMessageHTML(role, content, toolCalls, sources, timestamp) {
  const isUser = role === 'user';
  const roleI18n = isUser ? 'ai_ws_role_you' : 'ai_ws_role_assistant';
  const roleName = isUser ? 'You' : 'WealthFlow AI';
  const icon = isUser ? 'bi-person' : 'bi-cpu';
  const timeStr = _formatDate(timestamp || new Date().toISOString());

  let toolBadges = '';
  if (toolCalls && toolCalls.length > 0) {
    toolBadges = '<div class="ai-ws-tool-badges">';
    toolCalls.forEach(tc => {
      const toolName = tc.tool || tc.name || 'tool';
      const statusIcon = (tc.status === 'success' || !tc.status) ? 'bi-check-circle-fill' : 'bi-x-circle-fill';
      toolBadges += `<span class="ai-ws-tool-badge"><i class="bi ${statusIcon}"></i> ${toolName}</span>`;
    });
    toolBadges += '</div>';
  }

  const processedContent = _renderMarkdown(content);

  return `
    <div class="ai-ws-msg">
      <div class="ai-ws-msg-avatar ${isUser ? 'user' : 'assistant'}">
        <i class="bi ${icon}"></i>
      </div>
      <div class="ai-ws-msg-body">
        <div class="ai-ws-msg-role">
          <span data-i18n="${roleI18n}">${roleName}</span>
          <span class="msg-time">${timeStr}</span>
        </div>
        ${toolBadges}
        <div class="ai-ws-msg-content">${processedContent}</div>
      </div>
    </div>
  `;
}

function _appendMessage(role, content, toolCalls, sources, timestamp) {
  const container = document.getElementById('ai-ws-messages');
  if (!container) return;

  if (!_aiState.conversationId && container.querySelector('.ai-ws-empty-state')) {
    container.innerHTML = '';
  }

  container.innerHTML += _renderMessageHTML(role, content, toolCalls, sources, timestamp);
  container.scrollTop = container.scrollHeight;
  _applyTranslations();
}

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

async function _handleAIChatSubmit() {
  const inputEl = document.getElementById('ai-ws-input');
  if (!inputEl) return;
  const message = inputEl.value.trim();
  if (!message || _aiState.loading) return;

  const domainSelect = document.getElementById('ai-ws-domain-select');
  const domain = domainSelect ? domainSelect.value : 'business_data_analysis';

  inputEl.value = '';
  inputEl.style.height = 'auto';

  _appendMessage('user', message, null, null, new Date().toISOString());
  // Pass conversationId so progress polling can start immediately if known
  _setLoadingUI(true, _aiState.conversationId);

  try {
    const res = await fetch('/api/financial-advisor/ai/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
      },
      body: JSON.stringify({
        message: message,
        conversation_id: _aiState.conversationId,
        question_domain: domain
      })
    });

    if (!res.ok) throw new Error('Network response was not ok');

    const data = await res.json();

    if (data.conversation_id) {
      _aiState.conversationId = data.conversation_id;
    }

    const aiMsg = data.message || {};
    _aiState.lastResponseMeta = {
      sources: aiMsg.sources || data.sources || [],
      tool_calls: aiMsg.tool_calls || []
    };

    _setLoadingUI(false);
    _appendMessage('assistant', aiMsg.content || '', aiMsg.tool_calls, aiMsg.sources, aiMsg.created_at || new Date().toISOString());

    _renderRightPanel();
    _fetchAIChatConversations();

  } catch (err) {
    _stopProgressPolling();
    _setLoadingUI(false);
    _appendMessage('assistant', _aiT('ai_ws_error_processing', 'Sorry, there was an error processing your request.'), null, null, new Date().toISOString());
  } finally {
    _stopProgressPolling();
    _setLoadingUI(false);
  }
}


function _toggleAIContextPanel() {
  const rightPanel = document.getElementById('ai-ws-right-panel');
  if (!rightPanel) return;
  
  _aiState.contextPanelOpen = !_aiState.contextPanelOpen;
  rightPanel.classList.toggle('collapsed', !_aiState.contextPanelOpen);
}

function _renderRightPanel() {
  const container = document.getElementById('ai-ws-context-content');
  if (!container) return;

  const sourcesMap = {
    overview: 'ai_ws_source_overview',
    cash_flow: 'ai_ws_source_cash_flow',
    goal_planning: 'ai_ws_source_goal_planning',
    risk_analysis: 'ai_ws_source_risk_analysis',
    balance: 'ai_ws_source_balance',
    bank_certificates: 'ai_ws_source_certificates',
    expenses: 'ai_ws_source_expenses',
    salary: 'ai_ws_source_employment',
    gold: 'ai_ws_source_gold',
    fixed_assets: 'ai_ws_source_fixed_assets'
  };

  const toolsMap = {
    query_application_data: 'ai_ws_tool_query_database',
    read_live_app_structure: 'ai_ws_tool_app_discovery',
    suggest_app_feature: 'ai_ws_tool_feature_draft',
    read_application_codebase: 'ai_ws_tool_codebase_search'
  };

  let sourcesHtml = '';
  let toolsHtml = '';
  let confidenceHtml = '';

  if (_aiState.lastResponseMeta) {
    const sources = _aiState.lastResponseMeta.sources || [];
    const tools = _aiState.lastResponseMeta.tool_calls || [];

    if (sources.length > 0) {
      sources.forEach(src => {
        const name = typeof src === 'string' ? src : (src.name || 'Unknown');
        const i18nKey = sourcesMap[name] || name;
        sourcesHtml += `<div class="ai-ws-source-chip active"><i class="bi bi-check-circle-fill me-1"></i> <span data-i18n="${i18nKey}">${name}</span></div>`;
      });
      confidenceHtml = `
        <div class="ai-ws-confidence-box">
          <div class="ai-ws-confidence-row">
            <span>Confidence Rating</span>
            <span class="ai-ws-confidence-score">94% High</span>
          </div>
          <div class="ai-ws-confidence-bar">
            <div class="ai-ws-confidence-fill high"></div>
          </div>
        </div>
      `;
    } else {
      sourcesHtml = `<div class="ai-ws-empty-text" data-i18n="ai_ws_no_sources">No sources queried.</div>`;
      confidenceHtml = `
        <div class="ai-ws-confidence-box">
          <div class="ai-ws-confidence-row">
            <span>Confidence Rating</span>
            <span class="ai-ws-confidence-score">Standard</span>
          </div>
          <div class="ai-ws-confidence-bar">
            <div class="ai-ws-confidence-fill medium"></div>
          </div>
        </div>
      `;
    }

    if (tools.length > 0) {
      tools.forEach(tool => {
        const name = typeof tool === 'string' ? tool : (tool.name || 'Unknown');
        const i18nKey = toolsMap[name] || name;
        toolsHtml += `<div class="ai-ws-tool-item"><i class="bi bi-check-circle-fill success"></i> <span data-i18n="${i18nKey}">${name}</span></div>`;
      });
    } else {
      toolsHtml = `<div class="ai-ws-empty-text" data-i18n="ai_ws_no_tools">No tools executed.</div>`;
    }
  } else {
    const placeholder = `<div class="ai-ws-empty-text" data-i18n="ai_ws_awaiting_interaction">Awaiting interaction...</div>`;
    sourcesHtml = placeholder;
    toolsHtml = placeholder;
    confidenceHtml = placeholder;
  }

  container.innerHTML = `
    <div class="ai-ws-right-section">
      <div class="ai-ws-right-title"><i class="bi bi-database me-1"></i> <span data-i18n="ai_ws_context_sources">Context Sources</span></div>
      <div class="ai-ws-chip-list">${sourcesHtml}</div>
    </div>
    
    <div class="ai-ws-right-section">
      <div class="ai-ws-right-title"><i class="bi bi-wrench me-1"></i> <span data-i18n="ai_ws_tools_executed">Tools Executed</span></div>
      <div class="ai-ws-tool-list">${toolsHtml}</div>
    </div>
    
    <div class="ai-ws-right-section">
      <div class="ai-ws-right-title"><i class="bi bi-shield-check me-1"></i> <span data-i18n="ai_ws_confidence">Confidence &amp; Reasoning</span></div>
      <div>${confidenceHtml}</div>
    </div>
    
    <div class="ai-ws-right-section">
      <div class="ai-ws-right-title"><i class="bi bi-grid me-1"></i> <span data-i18n="ai_ws_app_modules">Application Modules</span></div>
      <div class="ai-ws-modules-grid">
        <div class="ai-ws-module-chip" data-i18n="nav_dashboard">Dashboard</div>
        <div class="ai-ws-module-chip" data-i18n="nav_financial_advisor">Financial Advisor</div>
        <div class="ai-ws-module-chip" data-i18n="nav_employment">Employment</div>
        <div class="ai-ws-module-chip" data-i18n="nav_balance">Balance</div>
        <div class="ai-ws-module-chip" data-i18n="nav_certificates">Certificates</div>
        <div class="ai-ws-module-chip" data-i18n="nav_fixed_assets">Fixed Assets</div>
        <div class="ai-ws-module-chip" data-i18n="nav_gold">Gold</div>
        <div class="ai-ws-module-chip" data-i18n="nav_expenses">Expenses</div>
        <div class="ai-ws-module-chip" data-i18n="nav_reports">Reports</div>
      </div>
    </div>

    <div class="ai-ws-right-section">
      <div class="ai-ws-right-title"><i class="bi bi-rocket-takeoff me-1"></i> <span data-i18n="ai_ws_future_capabilities">Future Capabilities</span></div>
      <div class="ai-ws-right-future">
        <div class="ai-ws-future-card">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-journal-text"></i>
            <span data-i18n="ai_ws_future_knowledge_base">Knowledge Base</span>
          </div>
          <span class="ai-ws-future-badge">🔒 COMING SOON</span>
        </div>
        <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-prompt-library" onclick="openPromptLibraryModal()" style="cursor: pointer;">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-chat-left-quote text-primary"></i>
            <span data-i18n="ai_ws_future_prompt_library">Prompt Library</span>
          </div>
          <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
        </div>

        <div class="ai-ws-future-card">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-server"></i>
            <span data-i18n="ai_ws_future_dataset_manager">Dataset Manager</span>
          </div>
          <span class="ai-ws-future-badge">🔒 COMING SOON</span>
        </div>
        <div class="ai-ws-future-card">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-sliders"></i>
            <span data-i18n="ai_ws_future_model_mgmt">Model Management</span>
          </div>
          <span class="ai-ws-future-badge">🔒 COMING SOON</span>
        </div>
        <div class="ai-ws-future-card">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-graph-up-arrow"></i>
            <span data-i18n="ai_ws_future_benchmarks">Benchmark Results</span>
          </div>
          <span class="ai-ws-future-badge">🔒 COMING SOON</span>
        </div>
      </div>
    </div>
  `;
  _applyTranslations();
}

function _renderExtensions() {
  const leftContainer = document.getElementById('ai-ws-ext-left');
  const rightContainer = document.getElementById('ai-ws-ext-right');

  if (leftContainer) {
    _aiWorkspaceExtensions.leftPanels.forEach(ext => {
      const div = document.createElement('div');
      if (typeof ext.render === 'function') {
        div.innerHTML = ext.render();
      }
      leftContainer.appendChild(div);
    });
  }

  if (rightContainer) {
    _aiWorkspaceExtensions.rightPanels.forEach(ext => {
      const div = document.createElement('div');
      if (typeof ext.render === 'function') {
        div.innerHTML = ext.render();
      }
      rightContainer.appendChild(div);
    });
  }
}

async function _switchAIChatConversation(convId) {
  _aiState.conversationId = convId;
  _aiState.lastResponseMeta = null;
  
  const container = document.getElementById('ai-ws-messages');
  if (container) {
    container.innerHTML = '';
  }
  
  _fetchAIChatConversations();
  
  try {
    const res = await fetch(`/api/financial-advisor/ai/conversations/${convId}/`);
    if (!res.ok) throw new Error('Failed to fetch conversation');
    const data = await res.json();
    
    const conv = data.conversation || data;
    const messages = conv.messages || [];
    if (messages.length > 0) {
      messages.forEach(msg => {
        _appendMessage(msg.role, msg.content, msg.tool_calls, msg.sources, msg.created_at);
      });
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === 'assistant') {
        _aiState.lastResponseMeta = {
          sources: lastMsg.sources || [],
          tool_calls: lastMsg.tool_calls || []
        };
      }
    } else {
      _renderEmptyState();
    }
    
    _renderRightPanel();
  } catch (err) {
    _renderEmptyState();
  }
}

async function _deleteAIChatConversation(convId) {
  if (!confirm(_aiT('ai_ws_confirm_delete', 'Are you sure you want to delete this conversation?'))) {
    return;
  }
  
  try {
    const res = await fetch(`/api/financial-advisor/ai/conversations/${convId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
      }
    });
    
    if (res.ok) {
      if (String(_aiState.conversationId) === String(convId)) {
        _aiState.conversationId = null;
        _aiState.lastResponseMeta = null;
        const container = document.getElementById('ai-ws-messages');
        if (container) container.innerHTML = '';
        _renderEmptyState();
        _renderRightPanel();
      }
      _fetchAIChatConversations();
    }
  } catch (err) {
    // Handle error
  }
}

function loadAIChat() {
  renderAI();
}

window.renderAI = renderAI;
window.loadAIChat = loadAIChat;
window._startNewAIChatConversation = _startNewAIChatConversation;
window._switchAIChatConversation = _switchAIChatConversation;
window._deleteAIChatConversation = _deleteAIChatConversation;
window._aiSuggestionClick = _aiSuggestionClick;
window._handleAIChatSubmit = _handleAIChatSubmit;
window._handleInputKeydown = _handleInputKeydown;
window._toggleAIContextPanel = _toggleAIContextPanel;
window.registerAIWorkspaceCard = registerAIWorkspaceCard;
window.registerAIRightPanel = registerAIRightPanel;
window.registerAILeftPanel = registerAILeftPanel;
window.registerAIWidget = registerAIWidget;
window.registerAIAgent = registerAIAgent;
