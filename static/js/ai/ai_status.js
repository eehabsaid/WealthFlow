"use strict";

/**
 * AI Workspace — Status Chips
 * Fetches provider/model/knowledge/online status and populates the header chips.
 * Depends on: ai_core.js
 */

async function _fetchAIWorkspaceStatus() {
  try {
    const [settingsRes, knowledgeRes, modelsRes] = await Promise.all([
      fetch("/api/settings/ai/").catch(() => null),
      fetch("/api/ai-platform/knowledge/").catch(() => null),
      fetch("/api/ai-platform/models/").catch(() => null),
    ]);

    if (settingsRes && settingsRes.ok) _aiState.aiSettings = await settingsRes.json();
    if (knowledgeRes && knowledgeRes.ok) {
      const kData = await knowledgeRes.json();
      _aiState.knowledgeCount = (kData.entries && kData.entries.length) || 0;
    }
    if (modelsRes && modelsRes.ok) _aiState.modelInfo = await modelsRes.json();

    const providerEl = document.getElementById("ai-ws-chip-provider");
    const modelEl = document.getElementById("ai-ws-chip-model");
    const knowledgeEl = document.getElementById("ai-ws-chip-knowledge");
    const statusEl = document.getElementById("ai-ws-chip-status");
    const statusContainer = document.getElementById("ai-ws-chip-status-container");

    if (providerEl) providerEl.textContent = _aiState.aiSettings?.ai_provider || "—";
    if (modelEl)
      modelEl.textContent =
        _aiState.aiSettings?.ai_model || _aiState.modelInfo?.active_model?.base_model || "—";
    if (knowledgeEl) knowledgeEl.textContent = _aiState.knowledgeCount || "—";
    if (statusEl) {
      const isOnline = _aiState.aiSettings && _aiState.aiSettings.ai_enabled;
      statusEl.textContent = isOnline
        ? _aiT("ai_ws_online", "Online")
        : _aiT("ai_ws_offline", "Offline");
      if (statusContainer) statusContainer.classList.toggle("online", !!isOnline);
      if (statusContainer) statusContainer.classList.toggle("offline", !isOnline);
    }
  } catch (err) {
    const ids = [
      "ai-ws-chip-provider",
      "ai-ws-chip-model",
      "ai-ws-chip-knowledge",
      "ai-ws-chip-status",
    ];
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.textContent = "—";
    });
  }
}
