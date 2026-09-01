"use strict";

// balance/card_renewal_fee/api.js — Card Renewal Fee save/delete calls
// ════════════════════════════════════════════════════════════════════════════

async function saveCardRenewalFee() {
  const btn = document.getElementById("saveCardRenewalFeeBtn");
  if (btn) btn.disabled = true;

  const payload = {
    fee_date: document.getElementById("crf_date").value,
    bank_id: document.getElementById("crf_bank").value,
    card_label: document.getElementById("crf_card_label").value,
    amount_egp: document.getElementById("crf_amount").value,
    notes: document.getElementById("crf_notes").value,
  };

  try {
    const url = _editingCardRenewalFeeId
      ? `/api/card-renewal-fees/${_editingCardRenewalFeeId}/`
      : "/api/card-renewal-fees/";
    const method = _editingCardRenewalFeeId ? "PUT" : "POST";

    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      const errMsg = err.error
        ? t(err.error, err.error)
        : t("error_failed_to_save", "Failed to save card renewal fee");
      throw new Error(errMsg);
    }

    if (typeof closeModal === "function") closeModal();
    showToast(t("success_saved", "Saved successfully"), "success");

    // Re-render whole balance to reflect the balance entry + expense mirror change globally
    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function deleteCardRenewalFee(id) {
  if (!confirm(t("confirm_delete", "Are you sure you want to delete this?"))) return;
  try {
    const res = await fetch(`/api/card-renewal-fees/${id}/`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");

    showToast(t("success_deleted", "Deleted successfully"), "success");

    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  }
}
