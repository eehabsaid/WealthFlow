"use strict";

/* Splits an answer (Markdown) into sentence-sized segments for progressive speech.
   Structural only: tables and code fences stay whole, sentences come from Intl.Segmenter. */
(function () {
  const FALLBACK = /[\s\S]*?[.!?؟۔…]+(?=\s|$)\s*|[\s\S]+$/g;
  const MARKER_ONLY = /^(?:[-*+•]|\d+[.)])$/;

  function sentencePieces(line) {
    let raw;
    try {
      const segmenter = new Intl.Segmenter(document.documentElement.lang || undefined, {
        granularity: "sentence",
      });
      raw = Array.from(segmenter.segment(line), (s) => s.segment);
    } catch (_error) {
      raw = line.match(FALLBACK) || [line];
    }
    const pieces = [];
    let carry = "";
    raw.forEach((piece) => {
      const joined = carry + piece;
      if (MARKER_ONLY.test(joined.trim())) {
        carry = joined; // a bare "1." or "-" belongs to the sentence that follows
        return;
      }
      pieces.push(joined);
      carry = "";
    });
    if (carry) pieces.push(carry);
    return pieces;
  }

  function blocks(text) {
    const out = [];
    let inFence = false;
    const lines = text.match(/[^\n]*\n|[^\n]+$/g) || [];
    let pos = 0;
    lines.forEach((line) => {
      const trimmed = line.trim();
      const start = pos;
      pos += line.length;
      const last = out[out.length - 1];
      if (inFence) {
        last.end = pos;
        if (trimmed.startsWith("```")) inFence = false;
      } else if (trimmed.startsWith("```")) {
        out.push({ start, end: pos, whole: true });
        inFence = !(trimmed.length > 3 && trimmed.endsWith("```"));
      } else if (trimmed.startsWith("|")) {
        if (last && last.table) last.end = pos;
        else out.push({ start, end: pos, whole: true, table: true });
      } else {
        out.push({ start, end: pos, whole: false });
      }
    });
    return out;
  }

  window.WFSpeech = window.WFSpeech || {};
  window.WFSpeech.splitSegments = function (markdown) {
    const text = String(markdown || "");
    const raw = [];
    blocks(text).forEach((block) => {
      if (block.whole) {
        raw.push({ text: text.slice(block.start, block.end), end: block.end });
        return;
      }
      let pos = block.start;
      sentencePieces(text.slice(block.start, block.end)).forEach((piece) => {
        pos += piece.length;
        raw.push({ text: piece, end: pos });
      });
    });
    const segments = [];
    raw.forEach((seg) => {
      if (seg.text.trim() || !segments.length) {
        if (seg.text.trim()) segments.push({ text: seg.text.trim(), end: seg.end });
      } else {
        segments[segments.length - 1].end = seg.end; // blank lines extend the previous segment
      }
    });
    if (segments.length) segments[segments.length - 1].end = text.length;
    return segments;
  };
})();
