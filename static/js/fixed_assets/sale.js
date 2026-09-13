"use strict";
// Asset sale form helpers
// This file is part of the fixed_assets module. Do not edit directly.

function resetSaleForm() {
  const saleDateField = document.getElementById("fa_sale_date");
  const salePriceField = document.getElementById("fa_sale_price");
  const sellingExpensesField = document.getElementById("fa_selling_expenses");
  const saleNotesField = document.getElementById("fa_sale_notes");
  const currencySelect = document.getElementById("fa_deposit_currency");
  const methodSelect = document.getElementById("fa_deposit_method");
  const bankSelect = document.getElementById("fa_deposit_bank");

  const defaultCurrency = getDefaultMonetaryCurrencyId();

  if (saleDateField) saleDateField.value = "";
  if (salePriceField) salePriceField.value = "";
  if (sellingExpensesField) sellingExpensesField.value = "0";
  if (saleNotesField) saleNotesField.value = "";
  if (currencySelect) currencySelect.value = String(defaultCurrency || "");
  if (methodSelect) methodSelect.value = "Cash";
  if (bankSelect) bankSelect.value = "";

  updateNetSaleAmount();
  toggleSaleDepositBankField();
}

function populateSaleForm(sale) {
  resetSaleForm();

  if (!sale) return;

  document.getElementById("fa_sale_date").value = sale.sale_date || "";
  document.getElementById("fa_sale_price").value = sale.sale_price || 0;
  document.getElementById("fa_selling_expenses").value = sale.selling_expenses || 0;
  document.getElementById("fa_sale_notes").value = sale.notes || "";

  if (sale.deposit_currency_id !== null && sale.deposit_currency_id !== undefined) {
    document.getElementById("fa_deposit_currency").value = String(sale.deposit_currency_id);
  }
  if (sale.deposit_method) {
    document.getElementById("fa_deposit_method").value = sale.deposit_method;
  }
  if (sale.deposit_bank_id !== null && sale.deposit_bank_id !== undefined) {
    document.getElementById("fa_deposit_bank").value = String(sale.deposit_bank_id);
  }

  updateNetSaleAmount();
  toggleSaleDepositBankField();
}

function maybeRefreshPurchaseUsdRateOnLoad() {
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  const currentValue = String(usdRateField.value ?? "").trim();
  const numericRate = parseFloat(currentValue);

  // Keep existing stored/manual value; refresh only when missing or invalid.
  if (!currentValue || !Number.isFinite(numericRate) || numericRate <= 0) {
    handlePurchaseCurrencyChange();
    return;
  }

  updatePurchasePriceUSD();
}

function toggleSaleDepositBankField() {
  const methodEl = document.getElementById("fa_deposit_method");
  const wrap = document.getElementById("faDepositBankWrap");
  const bankEl = document.getElementById("fa_deposit_bank");
  if (!methodEl || !wrap || !bankEl) return;

  const required = shouldRequireBankForMethod(methodEl.value);
  wrap.classList.toggle("d-none", !required);
  bankEl.required = required;
  if (!required) {
    bankEl.value = "";
  }
}

function toggleSaleTabVisibility() {
  const statusField = document.getElementById("fa_status");
  const saleTabItem = document.getElementById("sale-tab-item");
  const salePane = document.getElementById("sale-pane");
  const saleTabButton = document.getElementById("sale-tab");
  const generalTabButton = document.getElementById("general-tab");
  const isSold = statusField?.value === "Sold";

  if (!saleTabItem || !salePane || !saleTabButton) return;

  saleTabItem.classList.toggle("d-none", !isSold);
  salePane.classList.toggle("d-none", !isSold);

  if (!isSold && saleTabButton.classList.contains("active") && generalTabButton) {
    bootstrap.Tab.getOrCreateInstance(generalTabButton).show();
  }
}
