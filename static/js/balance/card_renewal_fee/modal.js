"use strict";

// balance/card_renewal_fee/modal.js — Card Renewal Fee create/edit modal
// ════════════════════════════════════════════════════════════════════════════

let _editingCardRenewalFeeId = null;

function showCardRenewalFeeModal(id = null) {
  _editingCardRenewalFeeId = id;
  const isEdit = id !== null;
  let crf = {
    fee_date: new Date().toISOString().split("T")[0],
    bank_id: "",
    card_label: "",
    amount_egp: "",
    notes: "",
  };

  if (isEdit) {
    crf = _cardRenewalFeeData.find((x) => x.id === id) || crf;
  }

  const titleText = isEdit
    ? t("edit_card_renewal_fee", "Edit Card Renewal Fee")
    : t("new_card_renewal_fee", "New Card Renewal Fee");
  const cancelText = t("btn_cancel", "Cancel");
  const saveText = t("btn_save", "Save");

  // Bank dropdown is sourced dynamically from Settings > Bank list (_banks).
  const bankOptions = _banks
    .map(
      (b) => `<option value="${b.id}" ${crf.bank_id === b.id ? "selected" : ""}>${b.name}</option>`
    )
    .join("");

  const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${isEdit ? "edit_card_renewal_fee" : "new_card_renewal_fee"}">
                ${titleText}
            </h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="cardRenewalFeeForm" onsubmit="event.preventDefault(); saveCardRenewalFee();">
                <div class="row g-3">
                    <div class="col-12">
                        <label data-i18n="crf_bank">${t("crf_bank", "Bank")}</label>
                        <select class="form-select" id="crf_bank" required>
                            <option value="" disabled ${crf.bank_id ? "" : "selected"} data-i18n="select_bank">${t("select_bank", "Select Bank...")}</option>
                            ${bankOptions}
                        </select>
                    </div>

                    <div class="col-6">
                        <label data-i18n="amount">${t("amount", "Amount")}</label>
                        <input type="number" step="0.01" class="form-control" id="crf_amount" required min="0.01">
                    </div>

                    <div class="col-6">
                        <label data-i18n="crf_date">${t("crf_date", "Date")}</label>
                        <input type="date" class="form-control" id="crf_date" required>
                    </div>

                    <div class="col-12">
                        <label data-i18n="crf_card_label">${t("crf_card_label", "Card")}</label>
                        <input type="text" class="form-control" id="crf_card_label" placeholder="Visa Debit ****1234">
                    </div>

                    <div class="col-12">
                        <label data-i18n="notes">${t("notes", "Notes")}</label>
                        <input type="text" class="form-control" id="crf_notes">
                    </div>
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button type="submit" form="cardRenewalFeeForm" class="btn-primary-custom" id="saveCardRenewalFeeBtn" data-i18n="btn_save">${saveText}</button>
        </div>
    `;

  showModal(html);

  document.getElementById("crf_date").value = crf.fee_date;
  document.getElementById("crf_amount").value = crf.amount_egp;
  document.getElementById("crf_card_label").value = crf.card_label;
  document.getElementById("crf_notes").value = crf.notes;
  if (crf.bank_id) document.getElementById("crf_bank").value = crf.bank_id;

  applyTranslations();
}
