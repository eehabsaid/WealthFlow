"use strict";
// Asset details > Rental tab: "Rent received" for the current month.
// Recording the real deposit settles the month's expected (virtual) rental income, so it is counted once.
// This file is part of the fixed assets module. Do not edit directly.

async function _rentReceiptsFetch(assetId) {
  const res = await fetch(`/api/fixed-assets/${assetId}/rent-receipts/`);
  return res.ok ? res.json() : null;
}

function _rentReceiptsHtml(assetId, data) {
  const current = data.receipts.find((r) => r.period === data.current_period);
  const status = current
    ? `<span data-i18n="rent_received_done">${t("rent_received_done", "Received")}</span>: ${fmt(current.amount)} ${current.currency_code}
       <button type="button" class="btn btn-outline-secondary btn-sm ms-2" id="rentUndoBtn" onclick="undoRentReceipt(${current.id}, ${assetId})" data-i18n="rent_received_undo">${t("rent_received_undo", "Undo")}</button>`
    : `<input type="number" step="0.01" min="0.01" class="form-control form-control-sm d-inline-block" style="width:140px" id="rentAmountInput" placeholder="${t("rent_received_amount", "Amount (blank = expected)")}">
       <button type="button" class="btn-primary-custom btn-sm ms-2" id="rentReceivedBtn" onclick="submitRentReceipt(${assetId})" data-i18n="rent_received_btn">${t("rent_received_btn", "Rent received")}</button>`;
  return `<div class="asset-attribute-row"><span class="label" data-i18n="rent_received_this_month">${t("rent_received_this_month", "This month's rent")} (${data.current_period})</span>
      <span class="value" id="rentReceiptStatus">${status}</span></div>
      <div class="text-muted small mt-1" data-i18n="rent_received_hint">${t("rent_received_hint", "Recording the rent you receive replaces this month's expected rental income in your balances, so it is counted once.")}</div>`;
}

async function renderRentReceipts() {
  const mount = document.getElementById("rentReceiptMount");
  if (!mount) return;
  const assetId = mount.dataset.assetId;
  const data = await _rentReceiptsFetch(assetId);
  if (!data) return;
  mount.innerHTML = _rentReceiptsHtml(assetId, data);
  applyTranslations();
}

async function _rentReceiptCall(url, options, okKey, okDefault) {
  const res = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
  });
  const body = await res.json().catch(() => ({}));
  if (res.ok) {
    showToast(t(okKey, okDefault), "success");
  } else {
    showToast(body.error || t("rent_received_error", "Could not record the rent"), "error");
  }
  return res.ok;
}

async function submitRentReceipt(assetId) {
  const amount = document.getElementById("rentAmountInput").value.trim();
  const payload = amount ? { amount } : {};
  const ok = await _rentReceiptCall(
    `/api/fixed-assets/${assetId}/rent-receipts/`,
    { method: "POST", body: JSON.stringify(payload) },
    "rent_received_saved",
    "Rent recorded ✓"
  );
  if (ok) renderRentReceipts();
}

async function undoRentReceipt(receiptId) {
  const ok = await _rentReceiptCall(
    `/api/rent-receipts/${receiptId}/`,
    { method: "DELETE" },
    "rent_received_undone",
    "Rent receipt removed"
  );
  if (ok) renderRentReceipts();
}

document.addEventListener("shown.bs.tab", (event) => {
  if (event.target && event.target.id === "asset-rental-tab") renderRentReceipts();
});

window.renderRentReceipts = renderRentReceipts;
window.submitRentReceipt = submitRentReceipt;
window.undoRentReceipt = undoRentReceipt;
