"use strict";
// Currency/bank dropdown helpers and USD price calculations
// This file is part of the fixed_assets module. Do not edit directly.

function updatePurchasePriceUSD() {
  const purchasePrice =
    parseFloat(document.getElementById("fa_purchase_price").value) || 0;
  const rate =
    parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0;
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

function getRateToEgp(row) {
  return parseFloat(row?.buy_rate) || 0;
}

function applyPurchaseUsdRateByCurrency(rates) {
  const purchaseCurrencyCode = getSelectedPurchaseCurrencyCode();
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  if (purchaseCurrencyCode === "USD") {
    usdRateField.value = "1.00000";
    updatePurchasePriceUSD();
    return;
  }

  const usd = rates.find((item) => String(item?.currency_code || "").toUpperCase() === "USD");
  const usdBuyRate = getRateToEgp(usd);
  if (!usdBuyRate) {
    throw new Error(t("error_loading_rates", "Error loading exchange rates."));
  }

  if (purchaseCurrencyCode === "EGP") {
    // Base currency is not stored in exchange-rate table; use implicit buy_rate = 1.00.
    const rate = usdBuyRate;
    usdRateField.value = rate.toFixed(5);
    updatePurchasePriceUSD();
    return;
  }

  let currencyBuyRate = 1;
  if (purchaseCurrencyCode && purchaseCurrencyCode !== "EGP") {
    const selectedCurrency = rates.find((item) => String(item?.currency_code || "").toUpperCase() === purchaseCurrencyCode);
    currencyBuyRate = getRateToEgp(selectedCurrency);
    if (!currencyBuyRate) {
      throw new Error(t("error_loading_rates", "Error loading exchange rates."));
    }
  }

  const rate = currencyBuyRate / usdBuyRate;
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
    const response = await fetch("/api/rates/");
    if (!response.ok) {
      throw new Error(t("error_loading_rates", "Error loading exchange rates."));
    }
    const payload = await response.json();
    const rates = Array.isArray(payload?.rates) ? payload.rates : [];
    applyPurchaseUsdRateByCurrency(rates);
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
    const purityConfig = (puritySettings || []).find((item) => String(item.key || "").toLowerCase() === purityKey);
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

function updateNetSaleAmount() {
  const salePrice =
    parseFloat(document.getElementById("fa_sale_price")?.value) || 0;
  const sellingExpenses =
    parseFloat(document.getElementById("fa_selling_expenses")?.value) || 0;
  const netSaleField = document.getElementById("fa_net_sale_amount");

  if (!netSaleField) return;

  netSaleField.value = (salePrice - sellingExpenses).toFixed(2);
}

function shouldRequireBankForMethod(methodValue) {
  const normalized = String(methodValue || "").trim().toLowerCase();
  return normalized !== "cash";
}

function renderPaymentMethodOptions(selected = "Cash") {
  return FIXED_ASSET_PAYMENT_METHODS
    .map((method) => {
      const key = `payment_${method.toLowerCase().replace(/\s+/g, "_")}`;
      return `<option value="${method}" ${String(selected) === method ? "selected" : ""} data-i18n="${key}">${t(key, method)}</option>`;
    })
    .join("");
}

function isMonetaryCurrency(currency) {
  const code = String(currency?.code || "").trim().toUpperCase();
  const name = String(currency?.name || "").trim().toLowerCase();
  return !["GOLD", "XAU", "CASH"].includes(code) && !name.includes("gold");
}

function getMonetaryCurrencies() {
  return fixedAssetSyncCurrencies.filter((currency) => isMonetaryCurrency(currency));
}

function renderCurrencyOptions(selectedCurrencyId = "") {
  return fixedAssetSyncCurrencies
    .map((currency) => {
      const selected = String(selectedCurrencyId) === String(currency.id) ? "selected" : "";
      return `<option value="${currency.id}" ${selected}>${currency.code}</option>`;
    })
    .join("");
}

function renderMonetaryCurrencyOptions(selectedCurrencyId = "") {
  return getMonetaryCurrencies()
    .map((currency) => {
      const selected = String(selectedCurrencyId) === String(currency.id) ? "selected" : "";
      return `<option value="${currency.id}" ${selected}>${currency.code}</option>`;
    })
    .join("");
}

function getDefaultMonetaryCurrencyId() {
  const monetaryCurrencies = getMonetaryCurrencies();
  const egp = monetaryCurrencies.find((row) => String(row.code).toUpperCase() === "EGP");
  return (egp || monetaryCurrencies[0] || {}).id || "";
}

function getDefaultPurchaseCurrencyId() {
  return getDefaultMonetaryCurrencyId();
}

function renderBankOptions(selectedBankId = "") {
  const rows = [`<option value="">${t("none_option", "--")}</option>`];
  fixedAssetSyncBanks.forEach((bank) => {
    const selected = String(selectedBankId) === String(bank.id) ? "selected" : "";
    rows.push(`<option value="${bank.id}" ${selected}>${bank.name}</option>`);
  });
  return rows.join("");
}

