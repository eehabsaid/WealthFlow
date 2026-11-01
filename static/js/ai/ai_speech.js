"use strict";

/* Voice controls: shared state, capabilities, button wiring. Provider work stays in Django. */
window.WFSpeech = window.WFSpeech || {};
Object.assign(window.WFSpeech, {
  api: "/api/financial-advisor/ai/speech",
  caps: { stt: false, tts: false },
  lastText: "",
  voiceTurn: false,
  session: null,
});

window.WFSpeech.csrfHeaders = function (extra) {
  return Object.assign({ "X-CSRFToken": window.wfGetCsrfToken?.() || "" }, extra || {});
};

window.WFSpeech.notify = function (message, type) {
  if (typeof showToast === "function")
    showToast(message, type === "error" ? "error" : type === "warning" ? "warning" : undefined);
};

window.WFSpeech.init = async function () {
  const S = window.WFSpeech;
  S.bindControls();
  try {
    const response = await fetch(`${S.api}/capabilities/`);
    if (!response.ok) return;
    const caps = await response.json();
    S.caps = { stt: !!caps.stt_enabled, tts: !!caps.tts_enabled };
    const stt = document.getElementById("ai-ws-stt-btn");
    const tts = document.getElementById("ai-ws-tts-btn");
    if (stt) stt.hidden = !S.caps.stt;
    if (tts) tts.hidden = !S.caps.tts;
  } catch (_error) {
    /* Optional speech must never interfere with text chat. */
  }
};

window.WFSpeech.setLastText = function (text) {
  window.WFSpeech.lastText = String(text || "");
};

/* Press-and-hold microphone (pointer + keyboard); speaker toggles read/stop; Stop button. */
window.WFSpeech.bindControls = function () {
  const S = window.WFSpeech;
  const stt = document.getElementById("ai-ws-stt-btn");
  if (stt) {
    stt.addEventListener("pointerdown", (event) => {
      if (event.button > 0) return;
      event.preventDefault();
      try {
        stt.setPointerCapture(event.pointerId);
      } catch (_error) {
        /* capture is best effort */
      }
      S.startRecording();
    });
    ["pointerup", "pointercancel", "lostpointercapture", "blur"].forEach((name) =>
      stt.addEventListener(name, () => S.stopRecording())
    );
    stt.addEventListener("keydown", (event) => {
      if ((event.key === " " || event.key === "Enter") && !event.repeat) {
        event.preventDefault();
        S.startRecording();
      }
    });
    stt.addEventListener("keyup", (event) => {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        S.stopRecording();
      }
    });
    stt.addEventListener("contextmenu", (event) => event.preventDefault());
  }
  document.getElementById("ai-ws-tts-btn")?.addEventListener("click", () => S.toggleSpeakLast());
  document.getElementById("ai-ws-tts-stop-btn")?.addEventListener("click", () => S.stop());
};

/* Button states. */
window.WFSpeech.paintSpeaking = function (on) {
  const tts = document.getElementById("ai-ws-tts-btn");
  const stop = document.getElementById("ai-ws-tts-stop-btn");
  if (tts) {
    tts.classList.toggle("is-speaking", on);
    tts.setAttribute("aria-pressed", on ? "true" : "false");
    tts.innerHTML = `<i class="bi ${on ? "bi-volume-up-fill" : "bi-volume-up"}"></i>`;
  }
  if (stop) stop.hidden = !on;
};

window.WFSpeech.paintRecording = function (state) {
  const button = document.getElementById("ai-ws-stt-btn");
  if (!button) return;
  const S = window.WFSpeech;
  const labels = {
    recording: t("speech_recording", "Recording… release to send"),
    processing: t("speech_processing", "Transcribing…"),
  };
  button.classList.toggle("is-recording", state === "recording");
  button.classList.toggle("is-processing", state === "processing");
  button.disabled = state === "processing";
  button.innerHTML =
    state === "processing"
      ? '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>'
      : `<i class="bi ${state === "recording" ? "bi-mic-fill" : "bi-mic"}"></i>`;
  S.indicator.hide("recording");
  S.indicator.hide("processing");
  if (labels[state])
    S.indicator.show(
      document.querySelector(".ai-ws-input-box"),
      state,
      labels[state],
      document.getElementById("ai-ws-input")
    );
};

/* Speech must not outlive the page it belongs to. */
window.addEventListener("hashchange", () => window.WFSpeech.stop?.());
