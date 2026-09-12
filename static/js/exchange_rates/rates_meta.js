// rates_meta.js — Currency metadata, priority ordering, and formatting
// helpers for the Exchange Rates page. Split out of the former
// exchange_rates.js monolith; see exchange_rates.js header comment for
// the sibling list.

"use strict";

// ════════════════════════════════════════════════════════════════════════════
// CURRENCY METADATA
// ════════════════════════════════════════════════════════════════════════════

const CURRENCY_META = {
  USD: { flag: "🇺🇸", name: "US Dollar" },
  EUR: { flag: "🇪🇺", name: "Euro" },
  GBP: { flag: "🇬🇧", name: "Pound Sterling" },
  SAR: { flag: "🇸🇦", name: "Saudi Riyal" },
  AED: { flag: "🇦🇪", name: "UAE Dirham" },
  KWD: { flag: "🇰🇼", name: "Kuwaiti Dinar" },
  CAD: { flag: "🇨🇦", name: "Canadian Dollar" },
  CHF: { flag: "🇨🇭", name: "Swiss Franc" },
  JPY: { flag: "🇯🇵", name: "Japanese Yen" },
  CNY: { flag: "🇨🇳", name: "Chinese Yuan" },
  QAR: { flag: "🇶🇦", name: "Qatari Riyal" },
  BHD: { flag: "🇧🇭", name: "Bahraini Dinar" },
  OMR: { flag: "🇴🇲", name: "Omani Riyal" },
  JOD: { flag: "🇯🇴", name: "Jordanian Dinar" },
  NOK: { flag: "🇳🇴", name: "Norwegian Krone" },
  SEK: { flag: "🇸🇪", name: "Swedish Krona" },
  DKK: { flag: "🇩🇰", name: "Danish Krone" },
  AUD: { flag: "🇦🇺", name: "Australian Dollar" },
};

const TOP_CURRENCY_ORDER = ["USD", "EUR", "SAR", "AED", "QAR", "OMR", "BHD", "JOD", "KWD", "GBP"];

// ════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ════════════════════════════════════════════════════════════════════════════

function sortRatesByPriority(rates) {
  const priority = new Map(TOP_CURRENCY_ORDER.map((code, index) => [code, index]));
  return [...rates].sort((a, b) => {
    const aIndex = priority.has(a.currency_code)
      ? priority.get(a.currency_code)
      : TOP_CURRENCY_ORDER.length;
    const bIndex = priority.has(b.currency_code)
      ? priority.get(b.currency_code)
      : TOP_CURRENCY_ORDER.length;
    if (aIndex !== bIndex) return aIndex - bIndex;
    return a.currency_code.localeCompare(b.currency_code);
  });
}

function fmtRate(n) {
  const num = Number(n);
  if (!num) return "—";
  const decimals = num > 10 ? 4 : 6;
  return num.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
