// i18n.js — Language engine (translation loading, applying, t() helper)

"use strict";

// ── Module state ──────────────────────────────────────────────────────────
let _t = {};
let _lang = localStorage.getItem("lang") || "en";

function t(key, fallback) {
  if (typeof _t === "undefined" || !_t) return fallback ?? key;

  const lang = localStorage.getItem("lang") || "en";

  // Nested: _t[lang][key]
  if (_t[lang]?.[key]) return _t[lang][key];

  // Flat: _t[key]
  if (_t[key]) return _t[key];

  return fallback !== undefined ? fallback : key;
}

// ════════════════════════════════════════════════════════════════════════════
// CURRENT LANGUAGE ACCESSOR
// ════════════════════════════════════════════════════════════════════════════

function currentLang() {
  return _lang;
}
