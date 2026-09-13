"use strict";
// Gold price: refresh handler + window exports
// This file is part of the gold_price module. Do not edit directly.

async function refreshGoldPrice() {
  const btn = document.getElementById("btnRefreshGold");
  const fetchingText = t("fetching", "Fetching…");
  const refreshText = t("refresh_prices", "Refresh Prices");

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner-border spinner-border-sm"></div> ${fetchingText}`;
  }
  try {
    const res = await fetch("/api/gold/refresh/", { method: "POST" });
    const data = await res.json();
    if (data.error) {
      const errorMsg = t("error_prefix", "Error: ") + data.error;
      showToast(errorMsg, "error");
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i class="bi bi-arrow-clockwise"></i> ${refreshText}`;
      }
    } else {
      const successMsg = t("gold_updated", "Gold prices updated");
      showToast(successMsg, "success");
      renderGoldPrice();
    }
  } catch (e) {
    const networkMsg = t("network_error_prefix", "Network error: ") + e.message;
    showToast(networkMsg, "error");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-arrow-clockwise"></i> ${refreshText}`;
    }
  }
}

// ════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.renderGoldPrice = renderGoldPrice;
window.refreshGoldPrice = refreshGoldPrice;
window.refreshGoldPrice = refreshGoldPrice;
