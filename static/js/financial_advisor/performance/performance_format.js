"use strict";

// Performance tab — pure formatting helpers. Split out of performance.js
// (200-line backlog). Bare globals (no external call sites; used only
// within the performance_* sibling files).
// ════════════════════════════════════════════════════════════════════════════

function formatMoneyEgp(val) {
  const num = Number(val) || 0;
  if (typeof fmtpresent === "function") {
    return `EGP ${fmtpresent(num)}`;
  }
  return `EGP ${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatImpactEgp(val) {
  const num = Number(val) || 0;
  const sign = num >= 0 ? "+" : "-";
  const absVal = Math.abs(num);
  if (typeof fmtpresent === "function") {
    return `${sign}EGP ${fmtpresent(absVal)}`;
  }
  return `${sign}EGP ${absVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatRateEgp(val) {
  const num = Number(val) || 0;
  return `${num.toFixed(2)} EGP`;
}
