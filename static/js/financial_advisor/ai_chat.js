"use strict";

// Backward-compatibility bridge for AI Advisor
function loadAIChat() {
  if (typeof window.renderAI === "function") {
    window.renderAI();
  }
}

window.loadAIChat = loadAIChat;
