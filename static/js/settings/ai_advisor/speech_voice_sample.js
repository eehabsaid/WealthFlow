"use strict";
// Voice cloning sample upload in Settings > AI Advisor > Text to speech.
window.AIA = window.AIA || {};

window.AIA.paintVoiceSample = async function (info, error) {
  const el = document.getElementById("speech_clone_status");
  if (!el) return;
  if (error) {
    el.className = "alert alert-danger py-1 px-2 mt-2 mb-0";
    el.textContent = error;
    return;
  }
  if (!info) {
    const res = await fetch("/api/settings/ai/speech/voice-sample/");
    info = res.ok ? await res.json() : {};
  }
  el.className =
    (info.has_sample ? "alert alert-success" : "alert alert-secondary") + " py-1 px-2 mt-2 mb-0";
  el.textContent = info.has_sample
    ? t("speech_clone_saved", "Saved: {name} ({size} KB).")
        .replace("{name}", info.name)
        .replace("{size}", info.size_kb)
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
  if (!res.ok) {
    window.AIA.paintVoiceSample(
      null,
      t("speech_clone_err_" + data.error, data.message || "Upload failed.")
    );
    return;
  }
  window.AIA.paintVoiceSample(data);
  window.showToast?.(t("speech_clone_toast", "Voice sample saved."), "success");
};

window.AIA.removeVoiceSample = async function () {
  const res = await fetch("/api/settings/ai/speech/voice-sample/", {
    method: "DELETE",
    headers: { "X-CSRFToken": window.wfGetCsrfToken?.() || "" },
  });
  window.AIA.paintVoiceSample(res.ok ? await res.json() : null);
};
