"use strict";

/* Voice-only sentence polling and playback; normal chat remains a single validated JSON response. */
(function () {
  const S = window.WFSpeech;
  const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const oldAfterAnswer = S.afterAnswer;
  const oldStop = S.stop;
  const oldToggle = S.toggleSpeakLast;

  function finish(session) {
    if (session.cleaned) return;
    session.cleaned = true;
    clearInterval(session.pollTimer);
    session.pollAbort.abort();
    session.audioAbort.abort();
    if (session.audio) session.audio.pause();
    session.placeholder?.closest(".ai-ws-msg")?.remove();
    if (S.streamSession === session) S.streamSession = null;
    S.paintSpeaking(false);
    S.indicator.hide("speaking");
  }
  S.finishStream = finish;

  function reveal(session, text) {
    session.hasSentences = true;
    session.text += `${session.text ? " " : ""}${text}`;
    if (!session.placeholder) {
      _appendMessage("assistant", "", null, null, new Date().toISOString(), null, 0);
      session.placeholder = S.lastAssistantContent();
      session.placeholder?.setAttribute("dir", "auto");
      const role = session.placeholder?.closest(".ai-ws-msg-body")?.querySelector(".ai-ws-msg-role");
      S.indicator.show(role, "speaking", t("speech_generating", "Preparing voice…"));
    }
    if (session.placeholder) session.placeholder.innerHTML = _renderMarkdown(session.text);
    const box = document.getElementById("ai-ws-messages");
    if (box) box.scrollTop = box.scrollHeight;
  }

  async function poll(session) {
    try {
      while (!session.cancelled && !session.failed && !session.blocked) {
        const response = await fetch(
          `${S.api}/voice-chunks/${session.id}/?after=${session.offset}`,
          { cache: "no-store", signal: session.pollAbort.signal }
        );
        if (!response.ok) throw new Error("Voice sentence stream is unavailable.");
        const result = await response.json();
        result.sentences.forEach((text) => {
          session.offset += 1;
          session.queue.push(text);
          reveal(session, text);
        });
        if (result.blocked || result.failed) {
          session.blocked = !!result.blocked;
          session.failed = !!result.failed;
          session.queue.length = 0;
          if (session.audio) session.audio.pause();
          break;
        }
        if (result.done) {
          session.done = true;
          break;
        }
        if (!result.sentences.length) await pause(160);
      }
    } catch (_error) {
      if (!session.cancelled) {
        session.failed = true;
        session.queue.length = 0;
        if (session.audio) session.audio.pause();
      }
    } finally {
      session.done = true;
    }
  }

  S.startStream = function (id) {
    S.cancelStream();
    S.skipAfterAnswer = false;
    const session = {
      id,
      offset: 0,
      queue: [],
      text: "",
      cancelled: false,
      done: false,
      failed: false,
      blocked: false,
      hasSentences: false,
      answerComplete: false,
      audioComplete: false,
      autoplayBlocked: false,
      pollAbort: new AbortController(),
      audioAbort: new AbortController(),
      audio: null,
      placeholder: null,
      cleaned: false,
    };
    S.streamSession = session;
    S.paintSpeaking(true);
    S.indicator.show(
      document.querySelector(".ai-ws-input-box"),
      "speaking",
      t("speech_generating", "Preparing voice…"),
      document.getElementById("ai-ws-input")
    );
    poll(session);
    S.playStreamQueue(session);
  };

  S.prepareStreamFinal = function () {
    const session = S.streamSession;
    session?.placeholder?.closest(".ai-ws-msg")?.remove();
    if (session) session.placeholder = null;
  };

  S.cancelStream = function () {
    const session = S.streamSession;
    if (!session) return;
    session.cancelled = true;
    finish(session);
  };

  S.afterAnswer = function (text) {
    if (S.skipAfterAnswer) {
      S.skipAfterAnswer = false;
      return;
    }
    const session = S.streamSession;
    if (!session) return oldAfterAnswer(text);
    S.prepareStreamFinal();
    if (!session.hasSentences || session.failed || session.blocked) {
      const speakFallback = !session.cancelled && !session.autoplayBlocked;
      finish(session);
      if (speakFallback) return oldAfterAnswer(text);
      return;
    }
    session.answerComplete = true;
    if (session.audioComplete) finish(session);
  };

  S.stop = function () {
    if (S.streamSession) S.skipAfterAnswer = true;
    S.cancelStream();
    oldStop();
  };

  S.toggleSpeakLast = function () {
    return S.streamSession ? S.stop() : oldToggle();
  };
})();
