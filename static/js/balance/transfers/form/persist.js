"use strict";
// Transfer save/delete API calls.
// Part of the balance/transfers module (split from the former monolithic
// form.js, 200-line rule). Do not edit directly.

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
