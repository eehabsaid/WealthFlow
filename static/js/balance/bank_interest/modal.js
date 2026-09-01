"use strict";

// balance/bank_interest/modal.js — Bank Interest create/edit modal
// ════════════════════════════════════════════════════════════════════════════

let _editingBankInterestId = null;

function showBankInterestModal(id = null) {
  _editingBankInterestId = id;
  const isEdit = id !== null;
  let bi = {
    interest_date: new Date().toISOString().split("T")[0],
    bank_id: "",
    currency_id: 1,
    amount: "",
    notes: "",
  };

  if (isEdit) {
    bi = _bankInterestData.find((x) => x.id === id) || bi;
  }

  const titleText = isEdit
    ? t("edit_bank_interest", "Edit Bank Interest")
    : t("new_bank_interest", "New Bank Interest");
  const cancelText = t("btn_cancel", "Cancel");
  const saveText = t("btn_save", "Save");

  // Bank dropdown is sourced dynamically from Settings > Bank list (_banks).
  const bankOptions = _banks
    .map(
      (b) => `<option value="${b.id}" ${bi.bank_id === b.id ? "selected" : ""}>${b.name}</option>`
    )
    .join("");

  const curOptions = (_currencies || [])
    .map((c) => {
      const key = c.code === "Gold" ? "type_gold" : c.code;
      let translatedName = _t && _t[key] ? _t[key] : `${c.code} - ${c.name}`;
      if (c.code === "Gold" && _t && _t["type_gold"]) {
        translatedName = _t["type_gold"].replace(/[\u{1F300}-\u{1F9FF}]/gu, "").trim();
      }
      const displayName = `${c.flag || "💵"} ${translatedName}`;
      return `<option value="${c.id}" data-i18n="${key}" ${bi.currency_id === c.id ? "selected" : ""}>${displayName}</option>`;
    })
    .join("");

  const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${isEdit ? "edit_bank_interest" : "new_bank_interest"}">
                ${titleText}
            </h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="bankInterestForm" onsubmit="event.preventDefault(); saveBankInterest();">
                <div class="row g-3">
                    <div class="col-12">
                        <label data-i18n="interest_bank">${t("interest_bank", "Bank")}</label>
                        <select class="form-select" id="bi_bank" required>
                            <option value="" disabled ${bi.bank_id ? "" : "selected"} data-i18n="select_bank">${t("select_bank", "Select Bank...")}</option>
                            ${bankOptions}
                        </select>
                    </div>

                    <div class="col-6">
                        <label data-i18n="currency">${t("currency", "Currency")}</label>
                        <select class="form-select" id="bi_currency" required>
                            ${curOptions}
                        </select>
                    </div>

                    <div class="col-6">
                        <label data-i18n="amount">${t("amount", "Amount")}</label>
                        <input type="number" step="0.01" class="form-control" id="bi_amount" required min="0.01">
                    </div>

                    <div class="col-12">
                        <label data-i18n="interest_date">${t("interest_date", "Date")}</label>
                        <input type="date" class="form-control" id="bi_date" required>
                    </div>

                    <div class="col-12">
                        <label data-i18n="notes">${t("notes", "Notes")}</label>
                        <input type="text" class="form-control" id="bi_notes">
                    </div>
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button type="submit" form="bankInterestForm" class="btn-primary-custom" id="saveBankInterestBtn" data-i18n="btn_save">${saveText}</button>
        </div>
    `;

  showModal(html);

  document.getElementById("bi_date").value = bi.interest_date;
  document.getElementById("bi_amount").value = bi.amount;
  document.getElementById("bi_notes").value = bi.notes;
  if (bi.bank_id) document.getElementById("bi_bank").value = bi.bank_id;

  applyTranslations();
}
