"use strict";
// The signed-in user's default (primary) currency. Loaded once by initApp()
// before any screen renders. Screens must use these helpers instead of
// writing a currency code. Translations may contain a {base} token; it is
// replaced with the user's currency code whenever a language is loaded.

window.WF_BASE = { code: "", symbol: "", pivot_currency: "", multi_currency_enabled: false };

function baseCurrencyCode() {
  return window.WF_BASE.code || "";
}

function baseCurrencySymbol() {
  return window.WF_BASE.symbol || window.WF_BASE.code || "";
}

// Value of one unit of `code` in the user's default currency, from a
// /api/rates/ list (rates are quoted against the pivot currency).
function wfRateToBase(code, rates) {
  const pivot = window.WF_BASE.pivot_currency;
  const quote = (c) => {
    if (c === pivot) return 1;
    const row = (rates || []).find((r) => r.currency_code === c);
    return row ? Number(row.buy_rate) || 0 : 0;
  };
  const base = quote(baseCurrencyCode());
  return base > 0 ? quote(code) / base : 0;
}

function applyBaseCurrencyToTranslations() {
  const code = baseCurrencyCode();
  if (!code || typeof _t === "undefined" || !_t) return;
  Object.keys(_t).forEach((key) => {
    if (typeof _t[key] === "string" && _t[key].includes("{base}")) {
      _t[key] = _t[key].split("{base}").join(code);
    }
  });
}

async function loadBaseCurrency() {
  try {
    const res = await fetch("/api/base-currency/");
    if (res.ok) window.WF_BASE = await res.json();
  } catch (err) {
    // Not signed in (auth pages): nothing to load.
  }
  applyBaseCurrencyToTranslations();
  if (typeof applyTranslations === "function") applyTranslations();
}

window.baseCurrencyCode = baseCurrencyCode;
window.baseCurrencySymbol = baseCurrencySymbol;
window.wfRateToBase = wfRateToBase;
window.applyBaseCurrencyToTranslations = applyBaseCurrencyToTranslations;
window.loadBaseCurrency = loadBaseCurrency;
