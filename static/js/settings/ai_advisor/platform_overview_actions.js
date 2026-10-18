"use strict";
// AI Advisor settings: the Autonomous App Scan action.

window.AIA = window.AIA || {};

window.AIA.runAutonomousAppScan = async function (btn) {
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/ai-platform/knowledge/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "scan" }),
    });
    const data = await res.json();
    if (data.ok) {
      if (typeof showToast === "function")
        showToast(`Autonomous scan complete ✓ (${data.updated_entries_count} entries updated)`);
    }
  } catch (err) {
    if (typeof showToast === "function") showToast("Autonomous scan failed", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
};

window.renderAIAdvisorSettings = window.AIA.renderAIAdvisorSettings;
