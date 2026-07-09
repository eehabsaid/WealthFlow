"use strict";
// Purchase payment rows management
// This file is part of the fixed_assets module. Do not edit directly.

function addPurchasePaymentRow(initial = {}) {
  const container = document.getElementById("purchasePaymentsContainer");
  if (!container) return;

  const method = initial.payment_method || "Cash";
  const bankId = initial.bank_id || "";
  const amount = initial.amount ?? "";

  const row = document.createElement("div");
  row.className = "row g-2 align-items-end mb-2 purchase-payment-row";
  row.innerHTML = `
    <div class="col-md-4">
      <label class="form-label text-light" data-i18n="payment_method">Payment Method</label>
      <select class="form-select purchase-method" onchange="togglePurchasePaymentBankField(this)">${renderPaymentMethodOptions(method)}</select>
    </div>
    <div class="col-md-3 purchase-bank-wrap">
      <label class="form-label text-light" data-i18n="bank">Bank</label>
      <select class="form-select purchase-bank">${renderBankOptions(bankId)}</select>
    </div>
    <div class="col-md-4">
      <label class="form-label text-light" data-i18n="amount">Amount</label>
      <input type="number" step="0.01" class="form-control purchase-amount" value="${amount}">
    </div>
    <div class="col-md-1 d-grid">
      <button type="button" class="btn btn-outline-danger" onclick="removePurchasePaymentRow(this)"><i class="bi bi-trash"></i></button>
    </div>
  `;

  container.appendChild(row);
  togglePurchasePaymentBankField(row.querySelector(".purchase-method"));
  applyTranslations();
}

function removePurchasePaymentRow(button) {
  const row = button?.closest(".purchase-payment-row");
  if (!row) return;
  row.remove();
}

function togglePurchasePaymentBankField(methodSelect) {
  const row = methodSelect?.closest(".purchase-payment-row");
  if (!row) return;
  const method = methodSelect.value;
  const bankWrap = row.querySelector(".purchase-bank-wrap");
  const bankSelect = row.querySelector(".purchase-bank");
  const required = shouldRequireBankForMethod(method);

  if (bankWrap) bankWrap.classList.toggle("d-none", !required);
  if (bankSelect) {
    bankSelect.required = required;
    if (!required) bankSelect.value = "";
  }
}

function resetPurchasePaymentsForm() {
  const container = document.getElementById("purchasePaymentsContainer");
  if (!container) return;
  container.innerHTML = "";
}

function populatePurchasePaymentsForm(rows, fallbackAmount = 0, defaultIfEmpty = true) {
  resetPurchasePaymentsForm();
  const values = Array.isArray(rows) ? rows : [];
  const purchaseCurrencySelect = document.getElementById("fa_purchase_currency");

  if (purchaseCurrencySelect) {
    const fromRows = values.find((item) => item && item.currency_id)?.currency_id;
    purchaseCurrencySelect.value = String(fromRows || getDefaultPurchaseCurrencyId() || "");
  }

  if (!values.length) {
    if (defaultIfEmpty) {
      addPurchasePaymentRow({ amount: fallbackAmount || "" });
    }
    return;
  }
  values.forEach((row) => addPurchasePaymentRow(row));
}

function collectPurchasePaymentsPayload() {
  const rows = Array.from(document.querySelectorAll("#purchasePaymentsContainer .purchase-payment-row"));
  return rows.map((row) => ({
    payment_method: row.querySelector(".purchase-method")?.value || "Cash",
    bank_id: parseInt(row.querySelector(".purchase-bank")?.value, 10) || null,
    amount: parseFloat(row.querySelector(".purchase-amount")?.value) || 0,
  }));
}

function validatePurchasePayments(purchasePrice) {
  const purchaseCurrencyId = parseInt(document.getElementById("fa_purchase_currency")?.value, 10) || null;
  if (!purchaseCurrencyId) {
    throw new Error(t("currency_required", "Currency is required."));
  }

  const rows = collectPurchasePaymentsPayload();
  if (!rows.length) {
    if (currentEditingAssetId !== null && !currentAssetHasPurchaseSync) {
      return [];
    }
    throw new Error(t("purchase_payment_required", "Add at least one payment source."));
  }

  rows.forEach((row) => {
    if (shouldRequireBankForMethod(row.payment_method) && !row.bank_id) {
      throw new Error(t("bank_account_required", "Bank account is required for this payment method"));
    }
    if (!row.amount || row.amount <= 0) {
      throw new Error(t("amount_required", "Amount is required."));
    }
  });

  const total = rows.reduce((sum, row) => sum + (parseFloat(row.amount) || 0), 0);
  if (Math.abs(total - purchasePrice) > 0.01) {
    throw new Error(t("purchase_payment_total_mismatch", "Total payment sources must equal purchase price."));
  }

  return rows;
}

