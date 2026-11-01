"use strict";

/* Press-and-hold voice message: record, transcribe (STT) and submit to WealthFlow AI automatically. */
(function () {
  const S = window.WFSpeech;
  S.rec = {
    recorder: null,
    stream: null,
    chunks: [],
    active: false,
    starting: false,
    wantStop: false,
    processing: false,
  };

  function release() {
    const rec = S.rec;
    rec.stream?.getTracks().forEach((track) => track.stop());
    Object.assign(rec, {
      stream: null,
      recorder: null,
      chunks: [],
      active: false,
      processing: false,
    });
    S.paintRecording("idle");
  }

  S.startRecording = async function () {
    const rec = S.rec;
    if (rec.active || rec.starting || rec.processing || !S.caps.stt) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined")
      return S.notify(
        t("speech_browser_unsupported", "This browser does not support microphone recording."),
        "error"
      );
    S.stop(); // never record the assistant's own voice
    rec.starting = true;
    rec.wantStop = false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (rec.wantStop) {
        stream.getTracks().forEach((track) => track.stop()); // released before the mic was ready
        return;
      }
      const recorder = new MediaRecorder(stream);
      Object.assign(rec, { stream, recorder, chunks: [], active: true });
      recorder.ondataavailable = (event) => event.data?.size && rec.chunks.push(event.data);
      recorder.onstop = S.finishRecording;
      recorder.start();
      S.paintRecording("recording");
    } catch (_error) {
      release();
      S.notify(t("speech_mic_denied", "Microphone access was denied or is unavailable."), "error");
    } finally {
      rec.starting = false;
    }
  };

  S.stopRecording = function () {
    const rec = S.rec;
    rec.wantStop = true;
    if (rec.active && rec.recorder?.state === "recording") rec.recorder.stop();
  };

  async function transcribe(blob, mime) {
    const data = new FormData();
    data.append("audio", blob, `recording.${mime.includes("mp4") ? "m4a" : "webm"}`);
    const response = await fetch(`${S.api}/transcribe/`, {
      method: "POST",
      headers: S.csrfHeaders(),
      body: data,
    });
    const result = await response.json();
    if (!response.ok || !result.text)
      throw new Error(result.error || t("speech_transcription_failed", "Transcription failed."));
    return result.text;
  }

  S.finishRecording = async function () {
    const rec = S.rec;
    rec.active = false;
    rec.processing = true;
    S.paintRecording("processing");
    let text = "";
    try {
      const mime = rec.chunks[0]?.type || "audio/webm";
      const blob = new Blob(rec.chunks, { type: mime });
      if (!blob.size) throw new Error(t("speech_no_speech", "No speech was recorded."));
      text = await transcribe(blob, mime);
    } catch (error) {
      S.notify(error.message || t("speech_transcription_failed", "Transcription failed."), "error");
    } finally {
      release();
    }
    if (text) await S.submitVoiceText(text);
  };

  S.submitVoiceText = async function (text) {
    const input = document.getElementById("ai-ws-input");
    if (!input) return;
    const draft = input.value.trim();
    input.value = draft ? `${draft} ${text}` : text;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    if (typeof _aiState !== "undefined" && _aiState.loading) {
      input.focus();
      return S.notify(
        t(
          "speech_busy",
          "WealthFlow AI is still answering. Your message was left in the message box."
        ),
        "warning"
      );
    }
    S.voiceTurn = true;
    try {
      await _handleAIChatSubmit();
    } finally {
      S.voiceTurn = false;
    }
  };
})();
