"use strict";
// Currency/bank dropdown helpers and USD price calculations
// This file is part of the fixed_assets module. Do not edit directly.

function updatePurchasePriceUSD() {
  const purchasePrice = parseFloat(document.getElementById("fa_purchase_price").value) || 0;
  const rate = parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0;
  const purchaseCurrencyCode = getSelectedPurchaseCurrencyCode();
  const usdField = document.getElementById("fa_purchase_price_usd");

  if (!usdField) return;

  if (purchaseCurrencyCode === "USD") {
    usdField.value = purchasePrice > 0 ? purchasePrice.toFixed(2) : "0.00";
    return;
  }

  if (purchaseCurrencyCode === "EGP") {
    if (rate > 0) {
      usdField.value = (purchasePrice / rate).toFixed(2);
    } else {
      usdField.value = "";
    }
    return;
  }

  if (rate > 0) {
    usdField.value = (purchasePrice * rate).toFixed(2);
  } else {
    usdField.value = "";
  }
}

function getSelectedPurchaseCurrency() {
  const selectedId = parseInt(document.getElementById("fa_purchase_currency")?.value, 10) || null;
  if (!selectedId) return null;
  return fixedAssetSyncCurrencies.find((item) => parseInt(item?.id, 10) === selectedId) || null;
}

function getSelectedPurchaseCurrencyCode() {
  return String(getSelectedPurchaseCurrency()?.code || "").toUpperCase();
}

// Shared by every "Now" button across the Fixed Asset tabs (General,
// Furniture, Acquisition Costs, Renovation). The rate math itself now
// lives server-side in UsdRateService - this just calls it. Output is
// unchanged from the previous in-browser calculation.
async function fetchCurrentUsdRateForCurrency(currencyId) {
  const response = await fetch(`/api/fixed-assets/usd-rate/?currency_id=${currencyId || ""}`);
  if (!response.ok) {
    let message = t("error_loading_rates", "Error loading exchange rates.");
    try {
      const payload = await response.json();
      if (payload?.error) message = payload.error;
    } catch (_) {
      // Keep fallback message.
    }
    throw new Error(message);
  }
  const payload = await response.json();
  return parseFloat(payload?.rate) || 0;
}

async function applyPurchaseUsdRateByCurrency() {
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  const currencyId = document.getElementById("fa_purchase_currency")?.value;
  const rate = await fetchCurrentUsdRateForCurrency(currencyId);
  usdRateField.value = rate.toFixed(5);
  updatePurchasePriceUSD();
}

async function handlePurchaseCurrencyChange() {
  const purchaseCurrencyCode = getSelectedPurchaseCurrencyCode();
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  const isGold = isGoldAssetType(document.getElementById("fa_type")?.value);
  if (purchaseCurrencyCode === "USD") {
    usdRateField.value = "1.00000";
    if (!isGold) {
      usdRateField.readOnly = true;
    }
    updatePurchasePriceUSD();
    return;
  } else if (!isGold) {
    usdRateField.readOnly = false;
  }

  try {
    await applyPurchaseUsdRateByCurrency();
  } catch (error) {
    showToast(error.message, "danger");
  }
}

function applyGoldReadOnlyState(isGold) {
  const purchaseUsdRateField = document.getElementById("fa_purchase_usd_rate");
  const purchaseUsdField = document.getElementById("fa_purchase_price_usd");
  const currentMarketValueField = document.getElementById("fa_current_value");
  const goldMarketPriceField = document.getElementById("gd_market_price");
  const valuationSourceRow = document.getElementById("valuation-source-row");
  const valuationSourceField = document.getElementById("fa_val_source");

  if (purchaseUsdRateField) purchaseUsdRateField.readOnly = isGold;
  if (purchaseUsdField) purchaseUsdField.readOnly = true;
  if (currentMarketValueField) currentMarketValueField.readOnly = isGold;
  if (goldMarketPriceField) goldMarketPriceField.readOnly = true;

  if (valuationSourceRow) {
    valuationSourceRow.classList.toggle("d-none", isGold);
  }
  if (valuationSourceField && isGold) {
    valuationSourceField.value = "Automatic";
  }
}

async function refreshGoldCalculatedFields(forcePriceFetch = false) {
  if (!isGoldAssetType(document.getElementById("fa_type")?.value)) {
    return;
  }

  try {
    const gold = await getLatestGoldPrice(forcePriceFetch);
    if (!gold) return;

    // Do not overwrite existing USD rate for gold on load/edit.
    // Only populate when missing/invalid (same behavior as other asset types).
    maybeRefreshPurchaseUsdRateOnLoad();

    const purity = document.getElementById("gd_purity")?.value || "24K";
    const unit = document.getElementById("gd_unit")?.value || "gram";
    const weight = parseFloat(document.getElementById("gd_weight")?.value) || 0;

    const puritySettings = await getGoldPuritySettings(forcePriceFetch);
    const purityKey = normalizeGoldPurity(purity);
    const purityConfig = (puritySettings || []).find(
      (item) => String(item.key || "").toLowerCase() === purityKey
    );
    const cashbackPerGram = parseFloat(purityConfig?.cashback_per_gram) || 0;

    const sellPerGram = getGoldSellPerGram(gold, purityKey);
    const unitFactor = getGoldUnitFactor(unit);
    const marketPricePerUnit = sellPerGram * unitFactor;
    const weightInGrams = weight * unitFactor;
    const currentMarketValue = (sellPerGram + cashbackPerGram) * weightInGrams;

    const marketPriceField = document.getElementById("gd_market_price");
    if (marketPriceField) {
      marketPriceField.value = marketPricePerUnit > 0 ? marketPricePerUnit.toFixed(4) : "";
    }

    const currentValueField = document.getElementById("fa_current_value");
    if (currentValueField) {
      currentValueField.value = currentMarketValue > 0 ? currentMarketValue.toFixed(2) : "0.00";
    }

    const cashbackField = document.getElementById("gd_cashback_per_gram");
    if (cashbackField) {
      cashbackField.value = cashbackPerGram.toFixed(4);
    }

    const valuationSourceField = document.getElementById("fa_val_source");
    if (valuationSourceField) {
      valuationSourceField.value = "Automatic";
    }
  } catch (err) {
    showToast(err.message, "danger");
  }
}

// Shared "Now" handler for per-row USD rate fields (Furniture,
// Acquisition Costs, Renovation). Fetches the same backend rate used by
// the General tab's "Now" button, fills the row's own rate field, then
// re-runs that row's existing (unchanged) USD recalculation.
async function fillRowUsdRateNow(buttonEl, rateSelector, recalcFn) {
  const row = buttonEl.closest(".furniture-row, .acquisition-row, .renovation-row");
  if (!row) return;
  const rateInput = row.querySelector(rateSelector);
  if (!rateInput) return;

  const currencyId = document.getElementById("fa_purchase_currency")?.value;
  try {
    const rate = await fetchCurrentUsdRateForCurrency(currencyId);
    rateInput.value = rate.toFixed(5);
    recalcFn(rateInput);
  } catch (error) {
    showToast(error.message, "danger");
  }
}
