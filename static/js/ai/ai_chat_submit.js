'use strict';

/**
 * AI Workspace — Chat Submit
 * Sends the user's message to the backend chat endpoint and renders the response.
 * Depends on: ai_core.js, ai_messages.js, ai_progress.js, ai_context_panel.js, ai_conversations.js
 */

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

window._handleAIChatSubmit = _handleAIChatSubmit;