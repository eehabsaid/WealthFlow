// exchange_rates.js — Exchange Rates refresh handler + module exports.
// Source: open.er-api.com (free, no key) → stored in Django DB
// CBE scrape runs locally via Python backend on user's machine
//
// Split out into a small file group to stay under the 200-line-per-file
// ceiling. Structural split only - no logic changes.
//
// Siblings (loaded before this file, in templates/index.html):
// - rates_meta.js: CURRENCY_META, TOP_CURRENCY_ORDER, sortRatesByPriority,
//   fmtRate.
// - rates_render.js: renderExchangeRates() - featured cards + full table.
//
// This file keeps the original exchange_rates.js entry point name and
// handles the refresh button plus the window.* exports for this module.

// ════════════════════════════════════════════════════════════════════════════
// EXCHANGE RATES REFRESH
// ════════════════════════════════════════════════════════════════════════════

async function refreshExchangeRates() {
  const btn = document.getElementById("btnRefreshRates");
  const status = document.getElementById("ratesStatus");
  const fetchingText = t("fetching", "Fetching…");
  const refreshText = t("refresh_internet", "Refresh from Internet");

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner-border spinner-border-sm"></div> ${fetchingText}`;
  }
  if (status) status.innerHTML = "";
  try {
    const res = await fetch("/api/rates/refresh/", { method: "POST" });
    const data = await res.json();
    if (data.error) {
      const errorMsg = t("error_prefix", "Error: ") + data.error;
      showToast(errorMsg, "error");
    } else {
      const successMsg = t("rates_updated", "Rates updated ✓");
      showToast(successMsg, "success");
      renderExchangeRates();
      return;
    }
  } catch (e) {
    const networkMsg = t("network_error_prefix", "Network error: ") + e.message;
    showToast(networkMsg, "error");
  }
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = `<i class="bi bi-arrow-clockwise"></i> ${refreshText}`;
  }
  applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.renderExchangeRates = renderExchangeRates;
window.refreshExchangeRates = refreshExchangeRates;
