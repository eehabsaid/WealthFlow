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

// Safe translation wrappers
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
  if (typeof window.formatDate === 'function') {
    return window.formatDate(dateStr);
  }
  return new Date(dateStr).toLocaleString();
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
            <div class="ai-ws-future-section"><i class="bi bi-pin-angle"></i> <span class="future-label" data-i18n="ai_ws_pinned_chats">Pinned Chats</span> <i class="bi bi-lock future-lock"></i></div>
            <div class="ai-ws-future-section"><i class="bi bi-bookmark"></i> <span class="future-label" data-i18n="ai_ws_saved_prompts">Saved Prompts</span> <i class="bi bi-lock future-lock"></i></div>
            <div class="ai-ws-future-section"><i class="bi bi-search"></i> <span class="future-label" data-i18n="ai_ws_knowledge_search">Knowledge Search</span> <i class="bi bi-lock future-lock"></i></div>
          </div>
          <div id="ai-ws-ext-left"></div>
        </div>
        
        <!-- Center Workspace -->
        <div class="ai-ws-center">
          <!-- Messages -->
          <div class="ai-ws-messages" id="ai-ws-messages">
            <!-- Empty state or messages populated via JS -->
          </div>
          
          <!-- Input Area -->
          <div class="ai-ws-input-area">
            <div class="ai-ws-input-domain">
              <select id="ai-ws-domain-select" class="ai-ws-domain-select">
                <option value="business_data_analysis" data-i18n="ai_domain_business_data">Business / Data Analysis</option>
                <option value="app_features_architecture" data-i18n="ai_domain_app_features">Application Features &amp; Architecture</option>
              </select>
            </div>
            <div class="ai-ws-input-row">
              <textarea id="ai-ws-input" class="ai-ws-textarea" rows="1" placeholder="${_aiT('ai_chat_input_placeholder_business', 'Ask a financial or business data question...')}" onkeydown="_handleInputKeydown(event)"></textarea>
              <button class="ai-ws-send-btn" onclick="_handleAIChatSubmit()" title="${_aiT('ai_chat_send_button', 'Send')}">
                <i class="bi bi-send"></i>
              </button>
            </div>
          </div>
        </div>
        
        <!-- Right Context Panel -->
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
    this.style.height = (this.scrollHeight < 140 ? this.scrollHeight : 140) + 'px';
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

    if (providerEl) providerEl.textContent = _aiState.aiSettings?.ai_provider || '\u2014';
    if (modelEl) modelEl.textContent = _aiState.aiSettings?.ai_model || _aiState.modelInfo?.active_model?.base_model || '\u2014';
    if (knowledgeEl) knowledgeEl.textContent = _aiState.knowledgeCount || '\u2014';
    if (statusEl) {
      const isOnline = _aiState.aiSettings && _aiState.aiSettings.ai_enabled;
      statusEl.textContent = isOnline ? _aiT('ai_ws_online', 'Online') : _aiT('ai_ws_offline', 'Offline');
      if (statusContainer) statusContainer.classList.toggle('online', !!isOnline);
      if (statusContainer) statusContainer.classList.toggle('offline', !isOnline);
    }
  } catch (err) {
    const ids = ['ai-ws-chip-provider', 'ai-ws-chip-model', 'ai-ws-chip-knowledge', 'ai-ws-chip-status'];
    ids.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '\u2014'; });
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
      const date = new Date(conv.created_at);
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
        const isActive = _aiState.conversationId === conv.id ? 'active' : '';
        html += `
          <div class="ai-ws-conv-item ${isActive}" onclick="_switchAIChatConversation('${conv.id}')">
            <div class="ai-ws-conv-title">${conv.title || _aiT('ai_ws_untitled', 'Untitled')}</div>
            <button class="ai-ws-btn-delete" onclick="event.stopPropagation(); _deleteAIChatConversation('${conv.id}')">
              <i class="bi bi-trash"></i>
            </button>
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

  messagesContainer.innerHTML = `
    <div class="ai-ws-empty-state">
      <i class="bi bi-cpu ai-ws-empty-icon"></i>
      <div class="ai-ws-empty-title" data-i18n="ai_ws_welcome_title">Welcome to WealthFlow AI</div>
      <div class="ai-ws-empty-desc" data-i18n="ai_ws_welcome_desc">Your cross-application intelligence workspace for business data reasoning, financial planning insights, and application architecture understanding.</div>
      
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

function _renderMarkdown(text) {
  if (!text) return '';
  
  let html = text;

  // Protect code blocks first
  const codeBlocks = [];
  html = html.replace(/```([\s\S]*?)```/g, function(match, p1) {
    codeBlocks.push(p1);
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });

  // HTML escape (excluding protected blocks)
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

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // Italic
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Headings
  html = html.replace(/^### (.*$)/gim, '<h5>$1</h5>');
  html = html.replace(/^## (.*$)/gim, '<h4>$1</h4>');
  
  // Blockquotes
  html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');
  
  // Horizontal rules
  html = html.replace(/^---$/gim, '<hr>');

  // Unordered Lists
  html = html.replace(/^\s*[-*]\s+(.*)$/gim, '<ul><li>$1</li></ul>');
  html = html.replace(/<\/ul>\n<ul>/g, '\n');

  // Ordered Lists
  html = html.replace(/^\s*\d+\.\s+(.*)$/gim, '<ol><li>$1</li></ol>');
  html = html.replace(/<\/ol>\n<ol>/g, '\n');

  // Tables
  html = html.replace(/^\|(.+)\|$/gim, function(match, content) {
    const cells = content.split('|').map(c => `<td>${c.trim()}</td>`).join('');
    return `<tr>${cells}</tr>`;
  });
  html = html.replace(/(<tr>.*?<\/tr>[\n\r]*)+/g, '<div class="ai-table-wrap"><table>$&</table></div>');

  // Line breaks
  html = html.replace(/\n/g, '<br>');

  // Restore code blocks
  html = html.replace(/__CODE_BLOCK_(\d+)__/g, function(match, index) {
    let codeContent = codeBlocks[index];
    codeContent = codeContent.replace(/[&<>"']/g, function(m) {
        switch (m) {
          case '&': return '&amp;';
          case '<': return '&lt;';
          case '>': return '&gt;';
          case '"': return '&quot;';
          case "'": return '&#039;';
          default: return m;
        }
      });
    return `<pre><code>${codeContent}</code></pre>`;
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

async function _handleAIChatSubmit() {
  const inputEl = document.getElementById('ai-ws-input');
  if (!inputEl) return;
  const message = inputEl.value.trim();
  if (!message || _aiState.loading) return;

  const domainSelect = document.getElementById('ai-ws-domain-select');
  const domain = domainSelect ? domainSelect.value : 'business';

  inputEl.value = '';
  inputEl.style.height = 'auto';
  _aiState.loading = true;

  _appendMessage('user', message, null, null, new Date().toISOString());

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
      sources: aiMsg.sources || [],
      tool_calls: aiMsg.tool_calls || []
    };

    _appendMessage('assistant', aiMsg.content || '', aiMsg.tool_calls, aiMsg.sources, aiMsg.created_at || new Date().toISOString());
    
    _renderRightPanel();
    _fetchAIChatConversations();

  } catch (err) {
    _appendMessage('assistant', _aiT('ai_ws_error_processing', 'Sorry, there was an error processing your request.'), null, null, new Date().toISOString());
  } finally {
    _aiState.loading = false;
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
        sourcesHtml += `<div class="ai-ws-source-chip active" data-i18n="${i18nKey}">${name}</div>`;
      });
      confidenceHtml = `<div class="ai-ws-confidence-high" data-i18n="ai_ws_confidence_high">High</div>`;
    } else {
      sourcesHtml = `<div class="ai-ws-empty-text" data-i18n="ai_ws_no_sources">No sources queried.</div>`;
      confidenceHtml = `<div class="ai-ws-confidence-low" data-i18n="ai_ws_confidence_low">Low</div>`;
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
    <div class="ai-ws-panel-section">
      <div class="ai-ws-section-title" data-i18n="ai_ws_context_sources">Context Sources</div>
      <div class="ai-ws-sources-list">${sourcesHtml}</div>
    </div>
    
    <div class="ai-ws-panel-section">
      <div class="ai-ws-section-title" data-i18n="ai_ws_tools_executed">Tools Executed</div>
      <div class="ai-ws-tools-list">${toolsHtml}</div>
    </div>
    
    <div class="ai-ws-panel-section">
      <div class="ai-ws-section-title" data-i18n="ai_ws_confidence">Confidence</div>
      <div>${confidenceHtml}</div>
    </div>
    
    <div class="ai-ws-panel-section">
      <div class="ai-ws-section-title" data-i18n="ai_ws_app_modules">Application Modules</div>
      <div class="ai-ws-modules-list">
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

    <div class="ai-ws-panel-section">
      <div class="ai-ws-section-title" data-i18n="ai_ws_future_capabilities">Future Capabilities</div>
      <div class="ai-ws-future-section" data-i18n="ai_ws_future_knowledge_base">Knowledge Base</div>
      <div class="ai-ws-future-section" data-i18n="ai_ws_future_prompt_library">Prompt Library</div>
      <div class="ai-ws-future-section" data-i18n="ai_ws_future_dataset_manager">Dataset Manager</div>
      <div class="ai-ws-future-section" data-i18n="ai_ws_future_model_mgmt">Model Management</div>
      <div class="ai-ws-future-section" data-i18n="ai_ws_future_benchmarks">Benchmark Results</div>
      <div class="ai-ws-future-section" data-i18n="ai_ws_future_recent">Recent Analyses</div>
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
