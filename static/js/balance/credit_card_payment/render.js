"use strict";

// balance/credit_card_payment/render.js — Credit Card Payment tab renderer
// ════════════════════════════════════════════════════════════════════════════

let _creditCardPaymentData = [];

function renderBalanceCreditCardPayment(data) {
  const pane = document.getElementById("bal-pane-credit_card_payment");
  if (!pane) return;

  _creditCardPaymentData = data.credit_card_payments || [];

  const dateText = t("ccp_date", "Date");
  const bankText = t("ccp_paid_from_bank", "Paid From");
  const methodText = t("ccp_payment_method", "Method");
  const cardText = t("ccp_card_label", "Card");
  const amountText = t("amount", "Amount");
  const notesText = t("notes", "Notes");
  const actionsText = t("actions", "Actions");
  const newText = t("new_credit_card_payment", "New Credit Card Payment");
  const noneText = t("no_credit_card_payments_found", "No credit card payments found.");
  const editText = t("edit", "Edit");
  const deleteText = t("delete", "Delete");

  let rowsHtml = "";

  if (_creditCardPaymentData.length === 0) {
    rowsHtml = `<tr><td colspan="7" class="text-center py-4" style="opacity:0.8; font-weight:500;" data-i18n="no_credit_card_payments_found">${noneText}</td></tr>`;
  } else {
    rowsHtml = _creditCardPaymentData
      .map(
        (cp) => `
            <tr>
                <td>${formatDate(cp.payment_date)}</td>
                <td>${cp.bank_name || "-"}</td>
                <td><span style="background:rgba(220,53,69,.15);color:#dc3545;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${cp.payment_method}</span></td>
                <td>${cp.card_label || "-"}</td>
                <td class="text-end amt-negative num-fmt" data-value="${cp.amount_egp}">${fmt(cp.amount_egp)}</td>
                <td class="text-truncate" style="max-width: 150px;" title="${cp.notes}">${cp.notes || "-"}</td>
                <td>
                    <button class="btn-icon" onclick="showCreditCardPaymentModal(${cp.id})" title="${editText}"><i class="bi bi-pencil"></i></button>
                    <button class="btn-icon del" onclick="deleteCreditCardPayment(${cp.id})" title="${deleteText}"><i class="bi bi-trash"></i></button>
                </td>
            </tr>
        `
      )
      .join("");
  }

  pane.innerHTML = `
        <div class="d-flex justify-content-end align-items-center mb-3">
            <button class="btn-primary-custom" onclick="showCreditCardPaymentModal()">
                <i class="bi bi-plus-lg me-1"></i>
                <span data-i18n="new_credit_card_payment">${newText}</span>
            </button>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="ccp_date">${dateText}</th>
                            <th data-i18n="ccp_paid_from_bank">${bankText}</th>
                            <th data-i18n="ccp_payment_method">${methodText}</th>
                            <th data-i18n="ccp_card_label">${cardText}</th>
                            <th class="text-end" data-i18n="amount">${amountText}</th>
                            <th data-i18n="notes">${notesText}</th>
                            <th data-i18n="actions">${actionsText}</th>
                        </tr>
                    </thead>
                    <tbody id="creditCardPaymentTableBody">
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}
