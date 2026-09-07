"use strict";
// Shared module state + getTranslatedBalanceTitle helper.
// Part of the balance module (split from the former monolithic
// currency_exchange.js, 200-line rule). Do not edit directly.

// balance/currency_exchange.js — Currency Exchange tab renderer & interactions
// All calculations, conversions, validations, options, and reversals are done in Django backend.
// ════════════════════════════════════════════════════════════════════════════

let _currencyExchangesData = [];
let _editingExchangeId = null;
let _exchangeFormOptions = { balances: [], currencies: [] };

function getTranslatedBalanceTitle(b) {
  if (!b) return "";
  const rawTitle = b.title || "";
  if (typeof _t !== "undefined" && _t && _t[rawTitle]) {
    return _t[rawTitle];
  }
  let title = rawTitle;

  // Strip duplicate trailing (BANK_NAME) or (CURRENCY_CODE) from title if present
  if (b.bank_name) {
    const dupBank = new RegExp(`\\s*\\(${b.bank_name}\\)\\s*$`, "i");
    title = title.replace(dupBank, "");
  }
  if (b.currency_code) {
    const dupCurr = new RegExp(`\\s*\\(${b.currency_code}\\)\\s*$`, "i");
    title = title.replace(dupCurr, "");
  }

  if (typeof t === "function") {
    title = title
      .replace(/Bank Account Balance/gi, t("bank_account_balance", "Bank Account Balance"))
      .replace(/Bank Account/gi, t("bank_account", "Bank Account"))
      .replace(/Home Balance/gi, t("home_balance", "Home Balance"))
      .replace(/Cash/gi, t("label_cash", "Cash"))
      .replace(/Wallet/gi, t("wallet", "Wallet"));
  }

  let bankStr = "";
  if (b.bank_name && !title.toLowerCase().includes(b.bank_name.toLowerCase())) {
    bankStr = ` (${b.bank_name})`;
  }
  return `${title}${bankStr} - ${b.currency_code}`;
}

