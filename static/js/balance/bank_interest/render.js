"use strict";

// balance/bank_interest/render.js — Bank Interest tab renderer
// ════════════════════════════════════════════════════════════════════════════

let _bankInterestData = [];

function renderBalanceBankInterest(data) {
  const pane = document.getElementById("bal-pane-bank_interest");
  if (!pane) return;

  _bankInterestData = data.bank_interests || [];

  const dateText = t("interest_date", "Date");
  const bankText = t("interest_bank", "Bank");
  const currencyText = t("currency", "Currency");
  const amountText = t("amount", "Amount");
  const notesText = t("notes", "Notes");
  const actionsText = t("actions", "Actions");
  const newText = t("new_bank_interest", "New Bank Interest");
  const noneText = t("no_bank_interests_found", "No bank interest entries found.");
  const editText = t("edit", "Edit");
  const deleteText = t("delete", "Delete");

  let rowsHtml = "";

  if (_bankInterestData.length === 0) {
    rowsHtml = `<tr><td colspan="6" class="text-center py-4" style="opacity:0.8; font-weight:500;" data-i18n="no_bank_interests_found">${noneText}</td></tr>`;
  } else {
    rowsHtml = _bankInterestData
      .map(
        (bi) => `
            <tr>
                <td>${formatDate(bi.interest_date)}</td>
                <td>${bi.bank_name || "-"}</td>
                <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${bi.currency_flag || "💱"} ${bi.currency_code}</span></td>
                <td class="text-end amt-positive num-fmt" data-value="${bi.amount}">${fmt(bi.amount)}</td>
                <td class="text-truncate" style="max-width: 150px;" title="${bi.notes}">${bi.notes || "-"}</td>
                <td>
                    <button class="btn-icon" onclick="showBankInterestModal(${bi.id})" title="${editText}"><i class="bi bi-pencil"></i></button>
                    <button class="btn-icon del" onclick="deleteBankInterest(${bi.id})" title="${deleteText}"><i class="bi bi-trash"></i></button>
                </td>
            </tr>
        `
      )
      .join("");
  }

  pane.innerHTML = `
        <div class="d-flex justify-content-end align-items-center mb-3">
            <button class="btn-primary-custom" onclick="showBankInterestModal()">
                <i class="bi bi-plus-lg me-1"></i>
                <span data-i18n="new_bank_interest">${newText}</span>
            </button>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="interest_date">${dateText}</th>
                            <th data-i18n="interest_bank">${bankText}</th>
                            <th data-i18n="currency">${currencyText}</th>
                            <th class="text-end" data-i18n="amount">${amountText}</th>
                            <th data-i18n="notes">${notesText}</th>
                            <th data-i18n="actions">${actionsText}</th>
                        </tr>
                    </thead>
                    <tbody id="bankInterestTableBody">
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}
