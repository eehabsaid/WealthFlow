"use strict";

/**
 * AI Workspace — Status chip
 * Fetches the AI settings and shows whether the AI is online in the header.
 * Depends on: ai_core.js
 */

async function _fetchAIWorkspaceStatus() {
  try {
    const settingsRes = await fetch("/api/settings/ai/").catch(() => null);

    if (settingsRes && settingsRes.ok) {
      _aiState.aiSettings = await settingsRes.json();
    } else {
      // Members cannot read the sysadmin settings: show their effective provider/model/state instead
      const me = await fetch("/api/settings/ai/me/")
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);
      if (me) {
        _aiState.aiSettings = {
          ai_provider: me.effective.ai_provider,
          ai_model: me.effective.ai_model,
          ai_enabled: String(me.effective.ai_enabled).toLowerCase() === "true",
        };
      }
    }

    const statusEl = document.getElementById("ai-ws-chip-status");
    const statusContainer = document.getElementById("ai-ws-chip-status-container");

    if (statusEl) {
      const isOnline = _aiState.aiSettings && _aiState.aiSettings.ai_enabled;
      statusEl.textContent = isOnline
        ? _aiT("ai_ws_online", "Online")
        : _aiT("ai_ws_offline", "Offline");
      if (statusContainer) statusContainer.classList.toggle("online", !!isOnline);
      if (statusContainer) statusContainer.classList.toggle("offline", !isOnline);
    }
  } catch (err) {
    const el = document.getElementById("ai-ws-chip-status");
    if (el) el.textContent = "—";
  }
}
