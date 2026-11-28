"use strict";

function getNumberLocale() {
  const currentLang = localStorage.getItem("lang") || "en";
  // 'ar-EG-u-nu-arab' explicitly forces the localized Arabic-Indic digits (١, ٢, ٣)
  return currentLang === "ar" ? "ar-EG-u-nu-arab" : "en-US";
}

function fmt(n) {
  if (n === null || n === undefined) return "-";
  return Number(n).toLocaleString(getNumberLocale(), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  });
}

function fmtpresent(n) {
  if (n === null || n === undefined) return "-";
  return Number(n).toLocaleString(getNumberLocale(), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  });
}

// Money amounts: always exactly 2 decimals so every KPI/card/table reads the
// same. Rates, percentages and ratios keep using fmt / fmtpresent / fmtRate.
function fmtMoney(n) {
  if (n === null || n === undefined) return "-";
  return Number(n).toLocaleString(getNumberLocale(), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// Rewritten into a super compact format to keep your file line-count ultra-low:

function fmtInt(n) {
  return n === null || n === undefined ? "-" : Number(n).toLocaleString(getNumberLocale());
}

function amtClass(n) {
  if (n > 0) return "amt-negative";
  if (n < 0) return "amt-positive";
  return "amt-zero";
}

// ════════════════════════════════════════════════════════════════════════════
// LOADING HELPERS
// ════════════════════════════════════════════════════════════════════════════

// Escape user-entered text before it is placed into innerHTML / attribute values.
function wfEsc(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Escape regex metacharacters so user text (bank names such as "A+B (Egypt)") can be used in new RegExp().
function _escapeRegExp(value) {
  return String(value === null || value === undefined ? "" : value).replace(
    /[.*+?^${}()|[\]\\]/g,
    "\\$&"
  );
}
