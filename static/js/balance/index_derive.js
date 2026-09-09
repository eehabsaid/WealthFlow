"use strict";

// balance/index_derive.js — Phase 3-4 of renderBalance: pre-compute derived
// summary values and build i18n template helpers. Split out of index.js
// (200-line backlog).
// ════════════════════════════════════════════════════════════════════════════

function deriveBalanceSummary(bData) {
  const summary = bData.summary || {};
  const totals = summary.totals_by_currency || {};
  const totalEGP = totals.EGP || 0;
  const cashEGP = summary.liquid_egp_cash ?? summary.cash_egp ?? 0;
  const usdAmount = totals.USD || 0;
  const eurAmount = totals.EUR || 0;
  const sarAmount = totals.SAR || 0;
  const usdRate = summary.usd_rate || 0;
  const eurRate = summary.eur_rate || 0;
  const sarRate = summary.sar_rate || 0;
  const goldValue = summary.gold_value || 0;
  const grandTotal = summary.grand_total || 0;
  const netWorth = summary.net_worth || grandTotal || 0;
  const allocationValues = summary.allocation_values || {};
  const cashAllocationValue = (allocationValues.type_cash || 0) + (allocationValues.type_bank || 0);

  return {
    totals,
    totalEGP,
    cashEGP,
    usdAmount,
    eurAmount,
    sarAmount,
    usdRate,
    eurRate,
    sarRate,
    goldValue,
    grandTotal,
    netWorth,
    allocationValues,
    cashAllocationValue,
  };
}

function buildBalanceI18nHelpers() {
  const resolveI18nTemplate = (key, fallback, params = {}) => {
    let text = t(key, fallback || key);
    Object.entries(params || {}).forEach(([k, raw]) => {
      let val = raw;
      const n = Number(raw);
      if (Number.isFinite(n)) {
        if (/days/i.test(k)) val = fmtInt(n);
        else if (/(ratio|trend|signal|gap|coverage|pct)/i.test(k)) val = fmt(n);
        else val = fmtpresent(n);
      }
      text = text.split(`{${k}}`).join(String(val));
    });
    return text;
  };
  const encodeI18nParams = (params = {}) => encodeURIComponent(JSON.stringify(params || {}));
  const getRecommendationText = (item) => {
    if (!item) return "";
    return item.key
      ? resolveI18nTemplate(item.key, item.text || item.key, item.params || {})
      : item.text || "";
  };
  const getReasonText = (item) => {
    if (!item) return "";
    return item.reason_key
      ? resolveI18nTemplate(
          item.reason_key,
          item.reason_text || item.reason_key,
          item.reason_params || {}
        )
      : item.reason_text || "";
  };

  return { resolveI18nTemplate, encodeI18nParams, getRecommendationText, getReasonText };
}
