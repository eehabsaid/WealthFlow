"use strict";

/* Sentence-by-sentence speech: each segment is synthesized while the previous one plays, and the
   answer text is revealed in step with the audio. Stop ends audio only; the full answer stays. */
(function () {
  const S = window.WFSpeech;

  async function synthesize(text, session) {
    const response = await fetch(`${S.api}/synthesize/`, {
      method: "POST",
      headers: S.csrfHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ text }),
      signal: session.abort.signal,
    });
    if (response.status === 204) return null; // nothing speakable in this segment
    if (!response.ok) {
      let message = "";
      try {
        message = (await response.json()).error;
      } catch (_error) {
        /* non-JSON error body */
      }
      throw new Error(message || t("speech_tts_failed", "Speech generation failed."));
    }
    return response.blob();
  }

  function play(blob, session) {
    return new Promise((resolve) => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      const done = () => {
        URL.revokeObjectURL(url);
        session.audio = null;
        session.stopPlayback = null;
        resolve();
      };
      session.audio = audio;
      session.stopPlayback = done;
      audio.onended = done;
      audio.onerror = done;
      audio.play().catch((error) => {
        if (error?.name === "NotAllowedError") session.blocked = true;
        done();
      });
    });
  }

  function reveal(session, end) {
    const el = session.content;
    if (!el) return;
    if (!el.isConnected) return S.stop(); // the conversation was switched away
    el.innerHTML = _renderMarkdown(session.full.slice(0, end));
    const box = document.getElementById("ai-ws-messages");
    if (box) box.scrollTop = box.scrollHeight;
  }

  function groupSegments(segments, limit = 240) {
    const groups = [];
    let current = null;
    segments.forEach((segment) => {
      const text = segment.text.trim();
      if (current && current.text.length + text.length + 1 > limit) {
        groups.push(current);
        current = null;
      }
      if (!current) current = { text, end: segment.end };
      else {
        current.text += ` ${text}`;
        current.end = segment.end;
      }
    });
    if (current) groups.push(current);
    return groups;
  }

  async function run(session) {
    const segments = session.groups;
    const start = (segment) => {
      const request = synthesize(segment.text, session);
      request.catch(() => {}); // surfaced when awaited below
      return request;
    };
    let pending = start(segments[0]);
    for (let i = 0; i < segments.length; i++) {
      let blob;
      try {
        blob = await pending;
      } catch (error) {
        if (session.cancelled) return;
        throw error;
      }
      if (session.cancelled) return;
      pending = i + 1 < segments.length ? start(segments[i + 1]) : null;
      reveal(session, segments[i].end);
      if (session.cancelled) return;
      if (!blob) continue;
      S.indicator.setLabel("speaking", t("speech_speaking", "Speaking…"));
      await play(blob, session);
      if (session.blocked) {
        S.notify(
          t(
            "speech_autoplay_blocked",
            "The browser blocked audio playback. Press the speaker button to listen."
          ),
          "warning"
        );
        return;
      }
      if (session.cancelled) return;
    }
  }

  function end(session) {
    if (session.ended) return;
    session.ended = true;
    session.abort.abort();
    if (session.content?.isConnected) session.content.innerHTML = _renderMarkdown(session.full);
    if (S.session === session) S.session = null;
    S.paintSpeaking(false);
    S.indicator.hide("speaking");
  }

  S.lastAssistantContent = function () {
    const messages = document.querySelectorAll("#ai-ws-messages .ai-ws-msg");
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].querySelector(".ai-ws-msg-avatar.assistant"))
        return messages[i].querySelector(".ai-ws-msg-content");
    }
    return null;
  };

  S.speak = async function (markdown, options = {}) {
    S.stop();
    if (!S.caps.tts) return;
    const sentenceSegments = S.splitSegments(markdown);
    if (!sentenceSegments.length)
      return S.notify(t("speech_no_answer", "There is no answer to read aloud yet."), "warning");
    const content = options.content || null;
    const session = {
      groups: groupSegments(sentenceSegments),
      content,
      full: String(markdown),
      abort: new AbortController(),
      cancelled: false,
      ended: false,
      blocked: false,
      audio: null,
      stopPlayback: null,
    };
    S.session = session;
    S.paintSpeaking(true);
    const host = (content || S.lastAssistantContent())
      ?.closest(".ai-ws-msg-body")
      ?.querySelector(".ai-ws-msg-role");
    S.indicator.show(host, "speaking", t("speech_generating", "Preparing voice…"));
    if (content) {
      content.setAttribute("dir", "auto");
      content.innerHTML = "";
    }
    try {
      await run(session);
    } catch (error) {
      if (!session.cancelled)
        S.notify(error.message || t("speech_tts_failed", "Speech generation failed."), "error");
    } finally {
      end(session);
    }
  };

  S.stop = function () {
    const session = S.session;
    if (!session) return;
    session.cancelled = true;
    session.abort.abort();
    session.audio?.pause();
    session.stopPlayback?.();
    end(session);
  };

  S.speakLast = function () {
    const text = S.lastText.trim();
    if (!text)
      return S.notify(t("speech_no_answer", "There is no answer to read aloud yet."), "warning");
    return S.speak(text);
  };

  S.toggleSpeakLast = function () {
    return S.session ? S.stop() : S.speakLast();
  };

  /* Voice-originated question: speak the validated answer while it is revealed. */
  S.afterAnswer = function (text) {
    if (!S.voiceTurn || !S.caps.tts || !text) return;
    S.voiceTurn = false;
    const content = S.lastAssistantContent();
    if (content) S.speak(text, { content });
  };
})();
