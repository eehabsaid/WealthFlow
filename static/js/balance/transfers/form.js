"use strict";

// balance/transfers module

function showTransferModal(id = null) {
  _editingTransferId = id;
  const isEdit = id !== null;
  let tr = {
    transfer_type: "bank_to_bank",
    transfer_date: new Date().toISOString().split("T")[0],
    amount: "",
    fee: 0,
    notes: "",
    currency_id: 1,
  };

  if (isEdit) {
    tr = _balanceTransfersData.find((x) => x.id === id) || tr;
  }

  const titleText = isEdit
    ? t("edit_transfer", "Edit Transfer")
    : t("new_transfer", "New Transfer");
  const cancelText = t("btn_cancel", "Cancel");
  const saveText = t("btn_save", "Save");

  const bankOptions = _banks.map((b) => `<option value="${b.id}">${b.name}</option>`).join("");

  // Format currency options like modal.js
  const curOptions = (_currencies || [])
    .map((c) => {
      const key = c.code === "Gold" ? "type_gold" : c.code;
      let translatedName = _t && _t[key] ? _t[key] : `${c.code} - ${c.name}`;
      if (c.code === "Gold" && _t && _t["type_gold"]) {
        translatedName = _t["type_gold"].replace(/[\u{1F300}-\u{1F9FF}]/gu, "").trim();
      }
      const displayName = `${c.flag || "💵"} ${translatedName}`;
      return `<option value="${c.id}" data-i18n="${key}" ${tr.currency_id === c.id ? "selected" : ""}>${displayName}</option>`;
    })
    .join("");

  const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${isEdit ? "edit_transfer" : "new_transfer"}">
                ${titleText}
            </h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="transferForm" onsubmit="event.preventDefault(); saveTransfer();">
                <div class="row g-3">
                    <div class="col-12">
                        <label data-i18n="transfer_type">${t("transfer_type", "Transfer Type")}</label>
                        <select class="form-select" id="tr_type" required onchange="onTransferTypeChange()">
                            <option value="bank_to_bank" data-i18n="type_bank_to_bank">${t("type_bank_to_bank", "Bank → Bank")}</option>
                            <option value="bank_to_cash" data-i18n="type_bank_to_cash">${t("type_bank_to_cash", "Bank → Cash")}</option>
                            <option value="cash_to_bank" data-i18n="type_cash_to_bank">${t("type_cash_to_bank", "Cash → Bank")}</option>
                        </select>
                    </div>
                    
                    <div class="col-6" id="from_bank_container">
                        <label data-i18n="transfer_from">${t("transfer_from", "From Bank")}</label>
                        <select class="form-select" id="tr_from_bank">
                            <option value="" disabled selected data-i18n="select_bank">${t("select_bank", "Select Bank...")}</option>
                            ${bankOptions}
                        </select>
                    </div>
                    
                    <div class="col-6" id="to_bank_container">
                        <label data-i18n="transfer_to">${t("transfer_to", "To Bank")}</label>
                        <select class="form-select" id="tr_to_bank">
                            <option value="" disabled selected data-i18n="select_bank">${t("select_bank", "Select Bank...")}</option>
                            ${bankOptions}
                        </select>
                    </div>
                    
                    <div class="col-4">
                        <label data-i18n="currency">${t("currency", "Currency")}</label>
                        <select class="form-select" id="tr_currency" required>
                            ${curOptions}
                        </select>
                    </div>
                    
                    <div class="col-4">
                        <label data-i18n="amount">${t("amount", "Amount")}</label>
                        <input type="number" step="0.01" class="form-control" id="tr_amount" required min="0.01">
                    </div>
                    
                    <div class="col-4">
                        <label data-i18n="transfer_fee">${t("transfer_fee", "Fee")}</label>
                        <input type="number" step="0.01" class="form-control" id="tr_fee" value="0" min="0">
                    </div>
                    
                    <div class="col-12">
                        <label data-i18n="transfer_date">${t("transfer_date", "Date")}</label>
                        <input type="date" class="form-control" id="tr_date" required>
                    </div>
                    
                    <div class="col-12">
                        <label data-i18n="notes">${t("notes", "Notes")}</label>
                        <input type="text" class="form-control" id="tr_notes">
                    </div>
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button type="submit" form="transferForm" class="btn-primary-custom" id="saveTransferBtn" data-i18n="btn_save">${saveText}</button>
        </div>
    `;

  // showModal is globally available from modals.js
  showModal(html);

  // Set values after render
  document.getElementById("tr_type").value = tr.transfer_type;
  document.getElementById("tr_date").value = tr.transfer_date;
  document.getElementById("tr_amount").value = tr.amount;
  document.getElementById("tr_fee").value = tr.fee;
  document.getElementById("tr_notes").value = tr.notes;

  if (tr.from_bank_id) document.getElementById("tr_from_bank").value = tr.from_bank_id;
  if (tr.to_bank_id) document.getElementById("tr_to_bank").value = tr.to_bank_id;

  onTransferTypeChange();
  applyTranslations();
}

function onTransferTypeChange() {
  const type = document.getElementById("tr_type").value;
  const fromContainer = document.getElementById("from_bank_container");
  const toContainer = document.getElementById("to_bank_container");
  const fromSelect = document.getElementById("tr_from_bank");
  const toSelect = document.getElementById("tr_to_bank");

  fromContainer.style.display = "block";
  toContainer.style.display = "block";
  fromSelect.required = true;
  toSelect.required = true;

  if (type === "bank_to_cash") {
    toContainer.style.display = "none";
    toSelect.required = false;
    toSelect.value = "";
  } else if (type === "cash_to_bank") {
    fromContainer.style.display = "none";
    fromSelect.required = false;
    fromSelect.value = "";
  }
}

async function saveTransfer() {
  const btn = document.getElementById("saveTransferBtn");
  if (btn) btn.disabled = true;

  const payload = {
    transfer_type: document.getElementById("tr_type").value,
    transfer_date: document.getElementById("tr_date").value,
    currency_id: document.getElementById("tr_currency").value,
    amount: document.getElementById("tr_amount").value,
    fee: document.getElementById("tr_fee").value || 0,
    notes: document.getElementById("tr_notes").value,
  };

  if (payload.transfer_type !== "cash_to_bank") {
    payload.from_bank_id = document.getElementById("tr_from_bank").value;
  }
  if (payload.transfer_type !== "bank_to_cash") {
    payload.to_bank_id = document.getElementById("tr_to_bank").value;
  }

  try {
    const url = _editingTransferId
      ? `/api/balance-transfers/${_editingTransferId}/`
      : "/api/balance-transfers/";
    const method = _editingTransferId ? "PUT" : "POST";

    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      const errMsg = err.error
        ? t(err.error, err.error)
        : t("error_failed_to_save", "Failed to save transfer");
      throw new Error(errMsg);
    }

    if (typeof closeModal === "function") closeModal();
    showToast(t("success_saved", "Saved successfully"), "success");

    // Re-render whole balance to reflect balance entry changes globally
    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function deleteTransfer(id) {
  if (!confirm(t("confirm_delete", "Are you sure you want to delete this?"))) return;
  try {
    const res = await fetch(`/api/balance-transfers/${id}/`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");

    showToast(t("success_deleted", "Deleted successfully"), "success");

    // Re-render whole balance to reflect balance entry changes globally
    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  }
}
