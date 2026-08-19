'use strict';

/**
 * AI Workspace — Context Panel & Extensions
 * Renders the right-hand context panel (sources, tools, confidence, modules)
 * and mounts any registered left/right panel extensions.
 * Depends on: ai_core.js
 */

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
        const name = typeof tool === 'string' ? tool : (tool.tool || tool.name || 'Unknown');
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
        <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-knowledge-base" onclick="openKnowledgeBaseModal()" style="cursor: pointer;">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-journal-text text-primary"></i>
            <span data-i18n="ai_ws_future_knowledge_base">Knowledge Base</span>
          </div>
          <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
        </div>
        <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-prompt-library" onclick="openPromptLibraryModal()" style="cursor: pointer;">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-chat-left-quote text-primary"></i>
            <span data-i18n="ai_ws_future_prompt_library">Prompt Library</span>
          </div>
          <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
        </div>

        <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-dataset-manager" onclick="openDatasetManagerModal()" style="cursor: pointer;">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-server text-primary"></i>
            <span data-i18n="ai_ws_future_dataset_manager">Dataset Manager</span>
          </div>
          <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
        </div>
        <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-model-management" onclick="openModelManagementModal()" style="cursor: pointer;">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-sliders text-primary"></i>
            <span data-i18n="ai_ws_future_model_mgmt">Model Management</span>
          </div>
          <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
        </div>
        <div class="ai-ws-future-card ai-ws-active-card" id="ai-ws-card-benchmark-results" onclick="openBenchmarkResultsModal()" style="cursor: pointer;">
          <div class="ai-ws-future-card-left">
            <i class="bi bi-graph-up-arrow text-primary"></i>
            <span data-i18n="ai_ws_future_benchmarks">Benchmark Results</span>
          </div>
          <span class="badge bg-primary text-white" style="font-size: 0.7rem;"><i class="bi bi-folder-fill me-1"></i><span data-i18n="ai_prompt_open_btn">Open</span></span>
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

window._toggleAIContextPanel = _toggleAIContextPanel;