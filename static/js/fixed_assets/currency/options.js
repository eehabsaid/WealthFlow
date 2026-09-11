"use strict";

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
