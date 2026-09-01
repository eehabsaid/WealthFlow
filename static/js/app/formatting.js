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
