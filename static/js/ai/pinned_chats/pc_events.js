/**
 * WealthFlow AI Workspace - Pinned Chats: Entry Point
 */

'use strict';

window.PC = window.PC || {};

window.openPinnedChatsModal = function () {
  window.PC.state.conversations = [];
  window.PC.state.loading = false;
  window.PC.state.error = null;

  showModal(window.PC.renderModalShell());
  window.PC.load();
};

/**
 * Toggle pin on a conversation from the conv list.
 * Called by ai_conversations.js pin button.
 */
window.togglePinConversation = function (convId, currentlyPinned) {
  fetch('/api/financial-advisor/ai/conversations/' + convId + '/', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
    },
    body: JSON.stringify({ is_pinned: !currentlyPinned }),
  })
    .then(function () {
      if (window._fetchAIChatConversations) window._fetchAIChatConversations();
    })
    .catch(function () {
      showToast(window.PC.t('ai_pc_pin_error', 'Failed to update pin.'), 'error');
    });
};
