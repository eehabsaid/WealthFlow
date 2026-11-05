"use strict";
window.AIA = window.AIA || {};

// Settings > AI Advisor > Image generation: the same five fields everywhere (enabled, provider, model, API URL, credentials).
// The provider list comes from the server (registered providers), so a new provider appears here without a UI change.
window.AIA.buildImageSettingsHtml = function (s) {
  const ui = window.AIA.ui;
  const field = (id, label, value, type, placeholder) => `
    <div class="aia-field"><label class="aia-label" for="${id}" data-i18n="${id}_label">${t(`${id}_label`, label)}</label>
    <input class="form-control" id="${id}" type="${type}" value="${escapeHtml(value ?? "")}" placeholder="${escapeHtml(placeholder)}" autocomplete="off"></div>`;
  const providers = s.image_gen_providers || [];
  const options =
    `<option value="" ${s.image_gen_provider ? "" : "selected"} data-i18n="image_gen_provider_none">${t("image_gen_provider_none", "Select a provider")}</option>` +
    providers
      .map(
        (p) =>
          `<option value="${escapeHtml(p.key)}" ${s.image_gen_provider === p.key ? "selected" : ""}>${escapeHtml(p.label)}</option>`
      )
      .join("");
  const provider = `<div class="aia-field"><label class="aia-label" for="image_gen_provider" data-i18n="image_gen_provider_label">${t("image_gen_provider_label", "Provider")}</label><select class="form-select" id="image_gen_provider">${options}</select></div>`;
  return (
    ui.toggleRow({
      id: "image_gen_enabled",
      checked: !!s.image_gen_enabled,
      labelKey: "image_gen_enabled_label",
      label: "Enable image generation",
      helpKey: "image_gen_enabled_help",
      help: "Lets the AI agent create and edit images. Off by default; it never affects text chat, speech or the other tools.",
    }) +
    ui.grid(
      provider +
        field(
          "image_gen_model",
          "Model name / file",
          s.image_gen_model,
          "text",
          "Configured model identifier"
        ),
      2
    ) +
    ui.grid(
      field(
        "image_gen_endpoint",
        "API URL",
        s.image_gen_endpoint,
        "url",
        "Full API URL of the provider"
      ) +
        field(
          "image_gen_api_key",
          "API key (optional)",
          s.image_gen_api_key,
          "password",
          "Leave unchanged to keep saved key"
        ),
      2
    ) +
    field(
      "image_gen_start_command",
      "Server start command (optional)",
      s.image_gen_start_command,
      "text",
      "Full command that starts the provider's server; {host} and {port} come from the API URL"
    ) +
    `<div class="aia-help mb-2" data-i18n="image_gen_start_command_help">${t("image_gen_start_command_help", "When set, WealthFlow starts the server in the background whenever image generation is enabled, waits until it answers, never starts a second copy, and stops it when you switch image generation off or WealthFlow exits. Leave empty if you run the server yourself.")}</div>` +
    `<div class="aia-row"><div class="aia-row-text"><label class="aia-label" data-i18n="image_gen_test_label">${t("image_gen_test_label", "Test connection")}</label><div class="aia-help" data-i18n="image_gen_test_help">${t("image_gen_test_help", "Checks that the provider answers with the values above and that its model files are installed.")}</div></div><div class="aia-row-control"><button type="button" class="btn btn-outline-info" id="image_gen_test" onclick="window.AIA.testImageProvider()"><i class="bi bi-activity me-1"></i><span data-i18n="image_gen_test_button">${t("image_gen_test_button", "Test connection")}</span></button></div></div><div id="image_gen_test_result" class="mb-2" hidden></div>`
  );
};

window.AIA.addImageSettingsPayload = function (payload) {
  ["enabled", "provider", "model", "endpoint", "api_key", "start_command"].forEach((f) => {
    const el = document.getElementById(`image_gen_${f}`);
    if (el) payload[`image_gen_${f}`] = f === "enabled" ? el.checked : el.value.trim();
  });
};

window.AIA.testImageProvider = async function () {
  const result = document.getElementById("image_gen_test_result");
  const button = document.getElementById("image_gen_test");
  if (!result || !button) return;
  const payload = {};
  window.AIA.addImageSettingsPayload(payload);
  result.hidden = false;
  result.className = "alert alert-info mb-2";
  result.textContent = t(
    "image_gen_testing",
    "Testing connection (starting the server first if needed, this can take a minute)..."
  );
  button.disabled = true;
  try {
    const response = await fetch("/api/settings/ai/image-generation/test/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.wfGetCsrfToken?.() || "",
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    result.className = `alert ${response.ok && data.ok ? "alert-success" : "alert-danger"} mb-2`;
    result.textContent =
      data.detail || data.error || t("image_gen_test_failed", "Connection test failed");
  } catch (_error) {
    result.className = "alert alert-danger mb-2";
    result.textContent = t("image_gen_test_failed", "Connection test failed");
  } finally {
    button.disabled = false;
  }
};
