"use strict";
// Voice cloning sample upload in Settings > AI Advisor > Text to speech.
window.AIA = window.AIA || {};

window.AIA.paintVoiceSample = async function (message) {
  const el = document.getElementById("speech_clone_status");
  if (!el) return;
  if (message) {
    el.textContent = message;
    return;
  }
  const res = await fetch("/api/settings/ai/speech/voice-sample/");
  const data = res.ok ? await res.json() : {};
  el.textContent = data.has_sample
    ? t("speech_clone_saved", "A voice sample is saved.")
    : t("speech_clone_none", "No voice sample saved.");
};

window.AIA.uploadVoiceSample = async function (input) {
  const file = input.files && input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/settings/ai/speech/voice-sample/", {
    method: "POST",
    headers: { "X-CSRFToken": window.wfGetCsrfToken?.() || "" },
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  input.value = "";
  window.AIA.paintVoiceSample(
    res.ok ? "" : t("speech_clone_err_" + data.error, data.message || "Upload failed.")
  );
  if (res.ok) window.AIA.paintVoiceSample();
};

window.AIA.removeVoiceSample = async function () {
  await fetch("/api/settings/ai/speech/voice-sample/", {
    method: "DELETE",
    headers: { "X-CSRFToken": window.wfGetCsrfToken?.() || "" },
  });
  window.AIA.paintVoiceSample();
};
