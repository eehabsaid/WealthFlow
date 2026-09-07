"use strict";
// AI Advisor settings: "Save" button handler.

window.AIA = window.AIA || {};

window.AIA.saveAISettingsFromGui = async function() {
  const btn = document.getElementById("aiSaveBtn");
  const enabled = document.getElementById("aiEnabledToggle")?.checked || false;
  const readOnly = document.getElementById("aiReadOnlyToggle")?.checked ?? true;
  const provider = document.getElementById("aiProviderSelect")?.value || "ollama";
  const model = (document.getElementById("aiModelInput")?.value || "").trim();
  const temperature = parseFloat(document.getElementById("aiTemperatureInput")?.value || "0.7");
  const contextSize = parseInt(document.getElementById("aiContextSizeInput")?.value || "4096", 10);
  const timeout = parseInt(document.getElementById("aiTimeoutInput")?.value || "60", 10);

  const systemPrompt = (document.getElementById("aiSystemPromptInput")?.value || "").trim();
  const maxTokens = parseInt(document.getElementById("aiMaxTokensInput")?.value || "2048", 10);
  const topP = parseFloat(document.getElementById("aiTopPInput")?.value || "0.9");
  const topK = parseInt(document.getElementById("aiTopKInput")?.value || "40", 10);
  const repeatPenalty = parseFloat(document.getElementById("aiRepeatPenaltyInput")?.value || "1.1");
  const seed = (document.getElementById("aiSeedInput")?.value || "").trim();
  const keepAlive = (document.getElementById("aiKeepAliveInput")?.value || "5m").trim();

  const payload = {
    ai_enabled: enabled,
    ai_read_only: readOnly,
    ai_provider: provider,
    ai_model: model,
    ai_temperature: temperature,
    ai_context_size: contextSize,
    ai_timeout: timeout,
    ai_system_prompt: systemPrompt,
    ai_max_tokens: maxTokens,
    ai_top_p: topP,
    ai_top_k: topK,
    ai_repeat_penalty: repeatPenalty,
    ai_seed: seed,
    ai_keep_alive: keepAlive,
  };

  // Save provider specific models
  if (provider === "ollama") payload.ai_model = model;
  if (provider === "openai") payload.ai_openai_model = model;
  if (provider === "claude") payload.ai_claude_model = model;
  if (provider === "gemini") payload.ai_gemini_model = model;
  if (provider === "azure") payload.ai_azure_deployment = model;

  // Collect all provider specific inputs
  window.AIA.state.currentProviderSchemas.forEach((schema) => {
    if (Array.isArray(schema.fields)) {
      schema.fields.forEach((f) => {
        const el = document.getElementById(f.name);
        if (el) {
          payload[f.name] = el.value.trim();
        }
      });
    }
  });

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> ${t("saving", "Saving...")}`;
  }

  try {
    const res = await fetch("/api/settings/ai/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.error || t("settings_save_failed", "Save failed"));
    }

    if (!enabled) {
      showToast(t("settings_saved", "Settings saved ✓"));
    } else if (data.connection_ok) {
      showToast(t("ai_saved_success", "Configuration saved successfully ✓"));
    } else {
      showToast(
        t("ai_saved_conn_failed", "Configuration saved, but connection test failed ⚠️"),
        "warning"
      );
    }
    await window.AIA.renderAIAdvisorSettings();
  } catch (err) {
    if (typeof showToast === "function") {
      showToast(err.message || t("settings_save_failed", "Save failed"), "error");
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-check-lg me-1"></i> <span>${t("ai_save_settings", "Save Settings")}</span>`;
    }
  }
}

