"use strict";
window.AIA = window.AIA || {};

window.AIA.buildSpeechSettingsHtml = function (s) {
  const ui = window.AIA.ui;
  const field = (id, label, value, type = "text", placeholder = "") => `
    <div class="aia-field"><label class="aia-label" for="${id}" data-i18n="${id}_label">${t(`${id}_label`, label)}</label>
    <input class="form-control" id="${id}" type="${type}" value="${escapeHtml(value ?? "")}" placeholder="${escapeHtml(placeholder)}" autocomplete="off"></div>`;
  const group = (kind, title, desc) => {
    const prefix = `speech_${kind}`;
    const language =
      kind === "stt"
        ? `<div class="aia-field"><label class="aia-label" for="speech_stt_language" data-i18n="speech_language_label">${t("speech_language_label", "Transcription language")}</label><select class="form-select" id="speech_stt_language"><option value="auto" ${!s.speech_stt_language || s.speech_stt_language === "auto" ? "selected" : ""} data-i18n="speech_language_auto">${t("speech_language_auto", "Auto detect")}</option><option value="en" ${s.speech_stt_language === "en" ? "selected" : ""} data-i18n="speech_language_en">${t("speech_language_en", "English")}</option><option value="ar" ${s.speech_stt_language === "ar" ? "selected" : ""} data-i18n="speech_language_ar">${t("speech_language_ar", "Arabic")}</option><option value="de" ${s.speech_stt_language === "de" ? "selected" : ""} data-i18n="speech_language_de">${t("speech_language_de", "German")}</option><option value="fr" ${s.speech_stt_language === "fr" ? "selected" : ""} data-i18n="speech_language_fr">${t("speech_language_fr", "French")}</option></select></div>`
        : "";
    return (
      `<div class="aia-row aia-row-wide"><h3 class="h6 mb-1" data-i18n="${prefix}_title">${t(`${prefix}_title`, title)}</h3><p class="aia-help" data-i18n="${prefix}_help">${t(`${prefix}_help`, desc)}</p></div>` +
      ui.toggleRow({
        id: `${prefix}_enabled`,
        checked: !!s[`${prefix}_enabled`],
        labelKey: `${prefix}_enabled_label`,
        label: `Enable ${kind.toUpperCase()}`,
        helpKey: `${prefix}_enabled_help`,
        help: "Disabled by default; speech does not affect text chat.",
      }) +
      ui.grid(
        field(
          `${prefix}_provider`,
          "Provider / service",
          s[`${prefix}_provider`],
          "text",
          "Any compatible service"
        ) +
          field(
            `${prefix}_model`,
            "Model name / ID",
            s[`${prefix}_model`],
            "text",
            "Configured model identifier"
          ) +
          language,
        language ? 3 : 2
      ) +
      ui.grid(
        field(
          `${prefix}_endpoint`,
          "Full API endpoint URL",
          s[`${prefix}_endpoint`],
          "url",
          "Paste full API endpoint URL"
        ) +
          field(
            `${prefix}_api_key`,
            "API key (optional)",
            s[`${prefix}_api_key`],
            "password",
            "Leave unchanged to keep saved key"
          ),
        2
      ) +
      ui.grid(
        field(
          `${prefix}_timeout`,
          "Timeout (seconds)",
          s[`${prefix}_timeout`] ?? 60,
          "number",
          "1–300"
        ) +
          (kind === "tts"
            ? field(
                `${prefix}_voice`,
                "Voice (optional)",
                s.speech_tts_voice,
                "text",
                "Provider-specific voice"
              )
            : ""),
        2
      ) +
      `<div class="aia-row"><div class="aia-row-text"><label class="aia-label" data-i18n="speech_test_label">Test endpoint</label><div class="aia-help" data-i18n="speech_test_help">Tests the configured API endpoint; compatibility is confirmed by an actual recording or generated audio.</div></div><div class="aia-row-control"><button type="button" class="btn btn-outline-info" id="speech_${kind}_test" onclick="window.AIA.testSpeechEndpoint('${kind}')"><i class="bi bi-activity me-1"></i><span data-i18n="speech_test_button">Test endpoint</span></button></div></div><div id="speech_${kind}_test_result" class="mb-2" hidden></div>`
    );
  };
  return (
    group("stt", "Speech to text (STT)", "Transcribe microphone recordings into the chat input.") +
    group("tts", "Text to speech (TTS)", "Generate spoken audio for an AI answer when requested.")
  );
};

window.AIA.addSpeechSettingsPayload = function (payload) {
  ["stt", "tts"].forEach((kind) => {
    ["enabled", "provider", "endpoint", "model", "api_key", "timeout", "voice", "language"].forEach(
      (field) => {
        const el = document.getElementById(`speech_${kind}_${field}`);
        if (el)
          payload[`speech_${kind}_${field}`] = field === "enabled" ? el.checked : el.value.trim();
      }
    );
  });
};

window.AIA.testSpeechEndpoint = async function (kind) {
  const result = document.getElementById(`speech_${kind}_test_result`);
  const button = document.getElementById(`speech_${kind}_test`);
  if (!result || !button) return;
  const payload = { kind };
  window.AIA.addSpeechSettingsPayload(payload);
  result.hidden = false;
  result.className = "alert alert-info mb-2";
  result.textContent = t("speech_testing", "Testing endpoint...");
  button.disabled = true;
  try {
    const response = await fetch("/api/settings/ai/speech/test/", {
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
      data.detail || data.error || t("speech_test_failed", "Endpoint test failed");
  } catch (_error) {
    result.className = "alert alert-danger mb-2";
    result.textContent = t("speech_test_failed", "Endpoint test failed");
  } finally {
    button.disabled = false;
  }
};
