"use strict";

// balance/transfers module

// balance/transfers.js — Transfers tab renderer
// ════════════════════════════════════════════════════════════════════════════

let _balanceTransfersData = [];
let _editingTransferId = null;

function renderBalanceTransfers(data) {
  const pane = document.getElementById("bal-pane-transfers");
  if (!pane) return;

  _balanceTransfersData = data.transfers || [];

  const dateText = t("transfer_date", "Date");
  const typeText = t("transfer_type", "Type");
  const fromText = t("transfer_from", "From");
  const toText = t("transfer_to", "To");
  const currencyText = t("currency", "Currency");
  const amountText = t("amount", "Amount");
  const feeText = t("transfer_fee", "Fee");
  const notesText = t("notes", "Notes");
  const actionsText = t("actions", "Actions");
  const newTransText = t("new_transfer", "New Transfer");
  const noTransText = t("no_transfers_found", "No transfers found.");
  const editText = t("edit", "Edit");
  const deleteText = t("delete", "Delete");

  let rowsHtml = "";

  if (_balanceTransfersData.length === 0) {
    rowsHtml = `<tr><td colspan="9" class="text-center py-4" style="opacity:0.8; font-weight:500;" data-i18n="no_transfers_found">${noTransText}</td></tr>`;
  } else {
    rowsHtml = _balanceTransfersData
      .map((tr) => {
        const typeLabels = {
          bank_to_bank: t("type_bank_to_bank", "Bank → Bank"),
          bank_to_cash: t("type_bank_to_cash", "Bank → Cash"),
          cash_to_bank: t("type_cash_to_bank", "Cash → Bank"),
        };
        const typeLabel = typeLabels[tr.transfer_type] || tr.transfer_type;
        const fromLabel =
          tr.from_bank_name ||
          (tr.transfer_type === "cash_to_bank" ? t("label_cash", "Cash") : "-");
        const toLabel =
          tr.to_bank_name || (tr.transfer_type === "bank_to_cash" ? t("label_cash", "Cash") : "-");

        return `
                <tr>
                    <td>${formatDate(tr.transfer_date)}</td>
                    <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${typeLabel}</span></td>
                    <td>${fromLabel}</td>
                    <td>${toLabel}</td>
                    <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${tr.currency_flag || "💱"} ${tr.currency_code}</span></td>
                    <td class="text-end amt-positive num-fmt" data-value="${tr.amount}">${fmt(tr.amount)}</td>
                    <td class="text-end amt-negative num-fmt" data-value="${tr.fee}">${fmt(tr.fee)}</td>
                    <td class="text-truncate" style="max-width: 150px;" title="${tr.notes}">${tr.notes || "-"}</td>
                    <td>
                        <button class="btn-icon" onclick="showTransferModal(${tr.id})" title="${editText}"><i class="bi bi-pencil"></i></button>
                        <button class="btn-icon del" onclick="deleteTransfer(${tr.id})" title="${deleteText}"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `;
      })
      .join("");
  }

  pane.innerHTML = `
        <div class="d-flex justify-content-end align-items-center mb-3">
            <button class="btn-primary-custom" onclick="showTransferModal()">
                <i class="bi bi-plus-lg me-1"></i>
                <span data-i18n="new_transfer">${newTransText}</span>
            </button>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="transfer_date">${dateText}</th>
                            <th data-i18n="transfer_type">${typeText}</th>
                            <th data-i18n="transfer_from">${fromText}</th>
                            <th data-i18n="transfer_to">${toText}</th>
                            <th data-i18n="currency">${currencyText}</th>
                            <th class="text-end" data-i18n="amount">${amountText}</th>
                            <th class="text-end" data-i18n="transfer_fee">${feeText}</th>
                            <th data-i18n="notes">${notesText}</th>
                            <th data-i18n="actions">${actionsText}</th>
                        </tr>
                    </thead>
                    <tbody id="transfersTableBody">
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}
