"use strict";

/* TTS producer/consumer for the opt-in sentence stream. */
(function () {
  const S = window.WFSpeech;
  const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function synthesize(text, session) {
    const response = await fetch(`${S.api}/synthesize/`, {
      method: "POST",
      headers: S.csrfHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ text }),
      signal: session.audioAbort.signal,
    });
    if (response.status === 204) return null;
    if (!response.ok) throw new Error(t("speech_tts_failed", "Speech generation failed."));
    return response.blob();
  }

  function play(blob, session) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      const done = () => {
        URL.revokeObjectURL(url);
        if (session.audio === audio) session.audio = null;
        resolve();
      };
      session.audio = audio;
      audio.onended = done;
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        if (session.audio === audio) session.audio = null;
        reject(new Error(t("speech_tts_failed", "Audio playback failed.")));
      };
      audio.onpause = () => {
        if (session.cancelled || session.failed || session.blocked) done();
      };
      audio.play().catch((error) => {
        URL.revokeObjectURL(url);
        if (session.audio === audio) session.audio = null;
        if (error?.name === "NotAllowedError") session.autoplayBlocked = true;
        reject(error);
      });
    });
  }

  async function take(session) {
    while (!session.cancelled && !session.failed && !session.blocked) {
      if (session.queue.length) return session.queue.shift();
      if (session.done) return null;
      await pause(70);
    }
    return null;
  }

  function takeGroup(session, first) {
    let text = first;
    while (session.queue.length && text.length + session.queue[0].length + 1 <= 200)
      text += ` ${session.queue.shift()}`;
    return text;
  }

  async function playQueue(session) {
    try {
      const first = await take(session);
      if (!first) return;
      let pending = synthesize(first, session);
      while (pending) {
        const blob = await pending;
        if (session.cancelled || session.failed || session.blocked) return;
        if (!blob && session.done && !session.queue.length) break;
        const next = take(session).then((text) =>
          text ? synthesize(takeGroup(session, text), session) : null
        );
        if (blob) {
          S.indicator.setLabel("speaking", t("speech_speaking", "Speaking…"));
          await play(blob, session);
        }
        pending = next;
      }
    } catch (error) {
      if (!session.cancelled && !session.autoplayBlocked) {
        session.failed = true;
        S.notify(error.message || t("speech_tts_failed", "Speech generation failed."), "error");
      } else if (session.autoplayBlocked) {
        S.notify(
          t("speech_autoplay_blocked", "The browser blocked audio playback. Press the speaker button to listen."),
          "warning"
        );
      }
    } finally {
      session.audioComplete = true;
      S.paintSpeaking(false);
      S.indicator.hide("speaking");
      if (session.answerComplete || session.cancelled) S.finishStream(session);
    }
  }

  S.playStreamQueue = playQueue;
})();
