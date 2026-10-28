"use strict";

/* Browser microphone and audio playback only; all provider work stays in Django. */
window.WFSpeech = window.WFSpeech || {};
window.WFSpeech.recorder = null;
window.WFSpeech.chunks = [];
window.WFSpeech.lastText = "";
window.WFSpeech.stream = null;

window.WFSpeech.init = async function () {
  try {
    const response = await fetch("/api/financial-advisor/ai/speech/capabilities/");
    if (!response.ok) return;
    const caps = await response.json();
    const stt = document.getElementById("ai-ws-stt-btn");
    const tts = document.getElementById("ai-ws-tts-btn");
    if (stt) stt.hidden = !caps.stt_enabled;
    if (tts) tts.hidden = !caps.tts_enabled;
  } catch (_error) {
    /* Optional speech must never interfere with text chat. */
  }
};

window.WFSpeech.setLastText = function (text) {
  window.WFSpeech.lastText = String(text || "");
  const button = document.getElementById("ai-ws-tts-btn");
  if (button && window.WFSpeech.lastText)
    button.title = t("speech_read_answer", "Read latest answer aloud");
};

window.WFSpeech.toggleRecording = async function () {
  if (window.WFSpeech.recorder?.state === "recording") {
    window.WFSpeech.recorder.stop();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    window.WFSpeech.notify(
      t("speech_browser_unsupported", "This browser does not support microphone recording."),
      "error"
    );
    return;
  }
  try {
    window.WFSpeech.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    window.WFSpeech.chunks = [];
    const recorder = new MediaRecorder(window.WFSpeech.stream);
    window.WFSpeech.recorder = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data?.size) window.WFSpeech.chunks.push(event.data);
    };
    recorder.onstop = window.WFSpeech.uploadRecording;
    recorder.start();
    const button = document.getElementById("ai-ws-stt-btn");
    if (button) {
      button.innerHTML = '<i class="bi bi-stop-circle"></i>';
      button.classList.add("btn-danger");
    }
  } catch (_error) {
    window.WFSpeech.notify(
      t("speech_mic_denied", "Microphone access was denied or is unavailable."),
      "error"
    );
  }
};

window.WFSpeech.uploadRecording = async function () {
  const button = document.getElementById("ai-ws-stt-btn");
  try {
    const mime = window.WFSpeech.chunks[0]?.type || "audio/webm";
    const blob = new Blob(window.WFSpeech.chunks, { type: mime });
    if (!blob.size) throw new Error("No audio was recorded.");
    const data = new FormData();
    data.append("audio", blob, `recording.${mime.includes("mp4") ? "m4a" : "webm"}`);
    if (button) button.disabled = true;
    const response = await fetch("/api/financial-advisor/ai/speech/transcribe/", {
      method: "POST",
      headers: { "X-CSRFToken": window.wfGetCsrfToken?.() || "" },
      body: data,
    });
    const result = await response.json();
    if (!response.ok || !result.text) throw new Error(result.error || "Transcription failed.");
    const input = document.getElementById("ai-ws-input");
    if (input) {
      input.value = `${input.value.trim()}${input.value.trim() ? " " : ""}${result.text}`;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
    }
    window.WFSpeech.notify(
      t("speech_transcription_ready", "Transcription added to the message box."),
      "success"
    );
  } catch (error) {
    window.WFSpeech.notify(
      error.message || t("speech_transcription_failed", "Transcription failed."),
      "error"
    );
  } finally {
    window.WFSpeech.stream?.getTracks().forEach((track) => track.stop());
    window.WFSpeech.stream = null;
    window.WFSpeech.recorder = null;
    window.WFSpeech.chunks = [];
    if (button) {
      button.disabled = false;
      button.innerHTML = '<i class="bi bi-mic"></i>';
      button.classList.remove("btn-danger");
    }
  }
};

window.WFSpeech.speakLast = async function () {
  const text = window.WFSpeech.lastText.trim();
  if (!text)
    return window.WFSpeech.notify(
      t("speech_no_answer", "There is no answer to read aloud yet."),
      "warning"
    );
  const button = document.getElementById("ai-ws-tts-btn");
  try {
    if (button) button.disabled = true;
    const response = await fetch("/api/financial-advisor/ai/speech/synthesize/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.wfGetCsrfToken?.() || "",
      },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "Speech generation failed.");
    }
    const url = URL.createObjectURL(await response.blob());
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    audio.onerror = () => URL.revokeObjectURL(url);
    await audio.play();
  } catch (error) {
    window.WFSpeech.notify(
      error.message || t("speech_tts_failed", "Speech generation failed."),
      "error"
    );
  } finally {
    if (button) button.disabled = false;
  }
};

window.WFSpeech.notify = function (message, type) {
  if (typeof showToast === "function")
    showToast(message, type === "error" ? "error" : type === "warning" ? "warning" : undefined);
};
