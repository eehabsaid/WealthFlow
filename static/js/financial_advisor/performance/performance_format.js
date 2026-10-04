"use strict";

// Performance tab — pure formatting helpers. Split out of performance.js
// (200-line backlog). Bare globals (no external call sites; used only
// within the performance_* sibling files).
// ════════════════════════════════════════════════════════════════════════════

// Gold prices come with their own currency code (EGP dealer prices, or the
// viewer's base currency for Gulf-market spot prices). Never hardcode it.
function formatMoneyGold(val, code) {
  const num = Number(val) || 0;
  const cur = code || baseCurrencyCode();
  if (typeof fmtpresent === "function") {
    return `${cur} ${fmtpresent(num)}`;
  }
  return `${cur} ${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatImpactBase(val) {
  // gold_impact_7d/30d are already converted to the user's base currency
  // upstream (see performance_service.py); this only formats, it never
  // was EGP-specific — fixed mislabeling here (batch 5).
  const num = Number(val) || 0;
  const sign = num >= 0 ? "+" : "-";
  const absVal = Math.abs(num);
  const code = baseCurrencyCode();
  if (typeof fmtpresent === "function") {
    return `${sign}${code} ${fmtpresent(absVal)}`;
  }
  return `${sign}${code} ${absVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatRateBase(val) {
  // current_rate is already expressed in the viewer's own default currency
  // (history is re-based server-side; see performance_service.py).
  const num = Number(val) || 0;
  return `${num.toFixed(2)} ${baseCurrencyCode()}`;
}
