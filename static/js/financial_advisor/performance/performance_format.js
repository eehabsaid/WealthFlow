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
  // Used only when no historical archive exists yet for this currency —
  // in that fallback branch, current_rate really is the live snapshot
  // value vs the viewer's own base currency (see performance_service.py).
  const num = Number(val) || 0;
  return `${num.toFixed(2)} ${baseCurrencyCode()}`;
}

function formatRatePivot(val, pivotCode) {
  // Used when historical data exists — the ExchangeRateHistory archive is
  // captured against the platform's shared rate pivot, not the viewer's
  // own base currency (one archive can't be per-viewer), so this must be
  // labeled with the pivot code, not baseCurrencyCode() (batch 5 fix —
  // fixes mislabeling as base as well as fixes an originally-hardcoded
  // "EGP" label that would go stale if the pivot ever changes).
  const num = Number(val) || 0;
  return `${num.toFixed(2)} ${pivotCode || baseCurrencyCode()}`;
}
