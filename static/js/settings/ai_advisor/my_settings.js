"use strict";
// "My AI Settings" tab: each user chooses the general AI settings or their own.
// Only the fields the backend whitelists are shown; sysadmin-only options never appear here.

window.AIA = window.AIA || {};

const MYAI_NUM_FIELDS = [
  ["ai_temperature", "myai_temperature", "Temperature", "0.1"],
  ["ai_max_tokens", "myai_max_tokens", "Max tokens", "1"],
  ["ai_context_size", "myai_context_size", "Context size", "1"],
  ["ai_timeout", "myai_timeout", "Timeout (s)", "1"],
  ["ai_top_p", "myai_top_p", "Top P", "0.05"],
  ["ai_top_k", "myai_top_k", "Top K", "1"],
  ["ai_repeat_penalty", "myai_repeat_penalty", "Repeat penalty", "0.05"],
  ["ai_history_window", "myai_history_window", "History window", "1"],
  ["ai_context_token_budget", "myai_context_budget", "Context token budget", "1"],
];

const MYAI_PROVIDER_FIELDS = {
  ollama: [["ai_model", "myai_model", "Model"]],
  openai: [
    ["ai_openai_model", "myai_model", "Model"],
    ["ai_openai_api_key", "myai_api_key", "API key"],
  ],
  claude: [
    ["ai_claude_model", "myai_model", "Model"],
    ["ai_claude_api_key", "myai_api_key", "API key"],
  ],
  gemini: [
    ["ai_gemini_model", "myai_model", "Model"],
    ["ai_gemini_api_key", "myai_api_key", "API key"],
  ],
};

function myAIUsageHtml(u) {
  if (!u.use_general) {
    return `<div class="alert alert-info py-2" data-i18n="myai_unlimited_own">${t("myai_unlimited_own", "You are on your own AI settings: no monthly token limit applies.")}</div>`;
  }
  const limit = u.limit
    ? `${u.used.toLocaleString()} / ${u.limit.toLocaleString()}`
    : `${u.used.toLocaleString()} (${t("myai_no_limit", "no limit")})`;
  const cls = u.exceeded ? "alert-danger" : "alert-secondary";
  return `<div class="alert ${cls} py-2" id="myAIUsage"><span data-i18n="myai_usage_label">${t("myai_usage_label", "Tokens used this month")}</span>: <strong>${limit}</strong></div>`;
}

function myAIFieldHtml(id, label, i18n, value, type, step) {
  const attrs = type === "number" ? `step="${step}"` : "";
  const val = String(value ?? "").replace(/"/g, "&quot;");
  return `<div class="col-md-4"><label class="form-label small" for="${id}" data-i18n="${i18n}">${t(i18n, label)}</label>
    <input class="form-control form-control-sm myai-input" id="${id}" type="${type}" ${attrs} value="${val}"></div>`;
}

function myAIProviderBlocks(fields) {
  return Object.entries(MYAI_PROVIDER_FIELDS)
    .map(([prov, list]) => {
      const inner = list
        .map(([k, i18n, label]) =>
          myAIFieldHtml(k, label, i18n, fields[k], k.endsWith("api_key") ? "password" : "text")
        )
        .join("");
      return `<div class="row g-2 myai-provider" data-provider="${prov}">${inner}</div>`;
    })
    .join("");
}

window.renderMyAISettings = async function () {
  const box = document.getElementById("settingsContent");
  if (!box) return;
  const res = await fetch("/api/settings/ai/me/");
  if (!res.ok) {
    box.innerHTML = `<div class="alert alert-danger m-3">${t("ai_load_failed_title", "Unable to load AI Advisor Settings")}</div>`;
    return;
  }
  const d = await res.json();
  const f = d.fields;
  const provOpts = d.providers_schema
    .map(
      (p) =>
        `<option value="${p.key}" ${p.key === f.ai_provider ? "selected" : ""}>${t(p.label_key, p.key.toUpperCase())}</option>`
    )
    .join("");
  const numeric = MYAI_NUM_FIELDS.map(([k, i18n, label, step]) =>
    myAIFieldHtml(k, label, i18n, f[k], "number", step)
  ).join("");
  box.innerHTML = `<div class="card p-3" id="myAIPanel">
    ${myAIUsageHtml(d.usage)}
    <div class="form-check form-switch mb-3">
      <input class="form-check-input" type="checkbox" id="myAIUseGeneral" ${d.use_general ? "checked" : ""}>
      <label class="form-check-label" for="myAIUseGeneral" data-i18n="myai_use_general">${t("myai_use_general", "Use general app settings")}</label>
      <div class="form-text" data-i18n="myai_use_general_hint">${t("myai_use_general_hint", "Turn off to use your own provider, model and keys. Your own settings have no monthly token limit.")}</div>
    </div>
    <fieldset id="myAIOwn" ${d.use_general ? "disabled" : ""}>
      <div class="form-check form-switch mb-2"><input class="form-check-input" type="checkbox" id="ai_enabled" ${String(f.ai_enabled) === "true" ? "checked" : ""}>
        <label class="form-check-label" for="ai_enabled" data-i18n="myai_enabled">${t("myai_enabled", "Enable AI with my settings")}</label></div>
      <div class="mb-2"><label class="form-label small" for="ai_provider" data-i18n="myai_provider">${t("myai_provider", "Provider")}</label>
        <select class="form-select form-select-sm" id="ai_provider">${provOpts}</select></div>
      ${myAIProviderBlocks(f)}
      <div class="row g-2 mt-1">${numeric}</div>
      <div class="mt-2"><label class="form-label small" for="ai_system_prompt" data-i18n="myai_system_prompt">${t("myai_system_prompt", "System prompt")}</label>
        <textarea class="form-control form-control-sm" id="ai_system_prompt" rows="3">${escapeHtml(f.ai_system_prompt)}</textarea></div>
    </fieldset>
    <div class="mt-3"><button type="button" class="btn btn-primary" id="myAISaveBtn" onclick="window.saveMyAISettings()" data-i18n="ai_save_settings">${t("ai_save_settings", "Save Settings")}</button></div>
  </div>`;
  const sync = () => {
    const general = document.getElementById("myAIUseGeneral").checked;
    document.getElementById("myAIOwn").disabled = general;
    const prov = document.getElementById("ai_provider").value;
    document.querySelectorAll(".myai-provider").forEach((el) => {
      el.style.display = el.dataset.provider === prov ? "" : "none";
    });
  };
  document.getElementById("myAIUseGeneral").addEventListener("change", sync);
  document.getElementById("ai_provider").addEventListener("change", sync);
  sync();
  if (typeof applyTranslations === "function") applyTranslations();
};

window.saveMyAISettings = async function () {
  const general = document.getElementById("myAIUseGeneral").checked;
  const payload = { use_general: general };
  if (!general) {
    document
      .querySelectorAll("#myAIOwn input.myai-input, #myAIOwn textarea, #myAIOwn select")
      .forEach((el) => {
        payload[el.id] = el.value;
      });
    payload.ai_enabled = document.getElementById("ai_enabled").checked;
  }
  const res = await fetch("/api/settings/ai/me/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.ok) {
    showToast(data.error || t("settings_save_failed", "Save failed"), "error");
    return;
  }
  showToast(
    general || data.connection_ok || !payload.ai_enabled
      ? t("ai_saved_success", "Configuration saved successfully ✓")
      : t("ai_saved_conn_failed", "Configuration saved, but connection test failed ⚠️"),
    general || data.connection_ok || !payload.ai_enabled ? "success" : "warning"
  );
  await window.renderMyAISettings();
};
