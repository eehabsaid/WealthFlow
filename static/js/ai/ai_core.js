'use strict';

/**
 * AI Workspace — Core State & Extension Registry
 * Shared global state and small formatting helpers used across all ai_*.js files.
 * Must load BEFORE any other ai_*.js file.
 */

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

window.registerAIWorkspaceCard = registerAIWorkspaceCard;
window.registerAIRightPanel = registerAIRightPanel;
window.registerAILeftPanel = registerAILeftPanel;
window.registerAIWidget = registerAIWidget;
window.registerAIAgent = registerAIAgent;