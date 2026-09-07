"use strict";
// Sync-source dropdown data + live USD exchange rate prefill.
// Part of the fixed_assets module (split from the former monolithic
// validation.js, 200-line rule). Do not edit directly.

async function loadFixedAssetSyncDropdownData() {
  if (!fixedAssetSyncCurrencies.length || !fixedAssetSyncBanks.length) {
    const [currRes, bankRes] = await Promise.all([fetch("/api/currencies/"), fetch("/api/banks/")]);

    if (!currRes.ok) {
      throw new Error(t("error_loading_currencies", "Error loading currencies"));
    }
    if (!bankRes.ok) {
      throw new Error(t("error_loading_banks", "Error loading banks"));
    }

    const currData = await currRes.json();
    const bankData = await bankRes.json();

    fixedAssetSyncCurrencies = Array.isArray(currData.currencies) ? currData.currencies : [];
    fixedAssetSyncBanks = Array.isArray(bankData.banks)
      ? bankData.banks.filter((b) => b?.is_active !== false)
      : [];
  }

  if (!fixedAssetBanksWithBalance.length) {
    const withBalanceRes = await fetch("/api/banks/with-balance/");
    if (withBalanceRes.ok) {
      const withBalanceData = await withBalanceRes.json();
      fixedAssetBanksWithBalance = Array.isArray(withBalanceData.banks)
        ? withBalanceData.banks
        : [];
    }
  }

  const saleCurrency = document.getElementById("fa_deposit_currency");
  if (saleCurrency) {
    saleCurrency.innerHTML = renderMonetaryCurrencyOptions();
  }

  const purchaseCurrency = document.getElementById("fa_purchase_currency");
  if (purchaseCurrency) {
    purchaseCurrency.innerHTML = renderMonetaryCurrencyOptions();
    purchaseCurrency.value = String(getDefaultPurchaseCurrencyId() || "");
  }

  const saleMethod = document.getElementById("fa_deposit_method");
  if (saleMethod) {
    saleMethod.innerHTML = renderPaymentMethodOptions("Cash");
  }

  const saleBank = document.getElementById("fa_deposit_bank");
  if (saleBank) {
    saleBank.innerHTML = renderBankOptions();
  }
}

async function fillCurrentUsdRate() {
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  try {
    await applyPurchaseUsdRateByCurrency();
  } catch (error) {
    showToast(error.message, "danger");
  }
}

