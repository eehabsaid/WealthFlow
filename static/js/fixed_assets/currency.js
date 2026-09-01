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

function updateNetSaleAmount() {
  const salePrice = parseFloat(document.getElementById("fa_sale_price")?.value) || 0;
  const sellingExpenses = parseFloat(document.getElementById("fa_selling_expenses")?.value) || 0;
  const netSaleField = document.getElementById("fa_net_sale_amount");

  if (!netSaleField) return;

  netSaleField.value = (salePrice - sellingExpenses).toFixed(2);
}

function shouldRequireBankForMethod(methodValue) {
  const normalized = String(methodValue || "")
    .trim()
    .toLowerCase();
  return normalized !== "cash";
}

function renderPaymentMethodOptions(selected = "Cash") {
  return FIXED_ASSET_PAYMENT_METHODS.map((method) => {
    const key = `payment_${method.toLowerCase().replace(/\s+/g, "_")}`;
    return `<option value="${method}" ${String(selected) === method ? "selected" : ""} data-i18n="${key}">${t(key, method)}</option>`;
  }).join("");
}

function isMonetaryCurrency(currency) {
  const code = String(currency?.code || "")
    .trim()
    .toUpperCase();
  const name = String(currency?.name || "")
    .trim()
    .toLowerCase();
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

function renderBankWithBalanceOptions(selectedBankId = "") {
  const rows = [`<option value="">${t("select_bank_account", "Select bank account")}</option>`];
  fixedAssetBanksWithBalance.forEach((bank) => {
    const selected = String(selectedBankId) === String(bank.id) ? "selected" : "";
    rows.push(`<option value="${bank.id}" ${selected}>${bank.name}</option>`);
  });
  return rows.join("");
}

function renderMoneyMovementFields(prefix, method = "Cash", bankId = "", labels = {}) {
  const required = shouldRequireBankForMethod(method);
  const methodLabel = labels.methodLabel || "payment_method";
  const methodLabelDefault = labels.methodLabelDefault || "Payment Method";
  const bankLabel = labels.bankLabel || "bank_account";
  const bankLabelDefault = labels.bankLabelDefault || "Bank Account";
  return `
    <div class="field">
      <label class="form-label small" data-i18n="${methodLabel}">${t(methodLabel, methodLabelDefault)}</label>
      <select class="form-select ${prefix}-payment-method" onchange="toggleMoneyMovementBankField(this, '${prefix}')">${renderPaymentMethodOptions(method)}</select>
    </div>
    <div class="field ${prefix}-bank-wrap" ${required ? "" : 'style="display:none;"'}>
      <label class="form-label small" data-i18n="${bankLabel}">${t(bankLabel, bankLabelDefault)}<span class="text-danger"> *</span></label>
      <select class="form-select ${prefix}-bank">${renderBankWithBalanceOptions(bankId)}</select>
    </div>
  `;
}

function toggleMoneyMovementBankField(selectEl, prefix) {
  const row = selectEl.closest(`.${prefix}-row`) || selectEl.closest("form") || document;
  const method = selectEl.value;
  const required = shouldRequireBankForMethod(method);
  const wrap = row.querySelector(`.${prefix}-bank-wrap`);
  const bankSelect = row.querySelector(`.${prefix}-bank`);

  if (wrap) wrap.style.display = required ? "" : "none";
  if (bankSelect) {
    bankSelect.required = required;
    if (!required) bankSelect.value = "";
  }
}

function renderFurnitureLinkOptions(selectedFurnitureId = "") {
  const rows = [`<option value="">${t("none_option", "— None —")}</option>`];
  (currentAssetFurnitureOptions || []).forEach((item) => {
    const selected = String(selectedFurnitureId) === String(item.id) ? "selected" : "";
    rows.push(`<option value="${item.id}" ${selected}>${item.name}</option>`);
  });
  return rows.join("");
}
