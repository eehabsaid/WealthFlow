"use strict";

// balance/bank_interest/api.js — Bank Interest save/delete calls
// ════════════════════════════════════════════════════════════════════════════

async function saveBankInterest() {
  const btn = document.getElementById("saveBankInterestBtn");
  if (btn) btn.disabled = true;

  const payload = {
    interest_date: document.getElementById("bi_date").value,
    bank_id: document.getElementById("bi_bank").value,
    currency_id: document.getElementById("bi_currency").value,
    amount: document.getElementById("bi_amount").value,
    notes: document.getElementById("bi_notes").value,
  };

  try {
    const url = _editingBankInterestId
      ? `/api/bank-interests/${_editingBankInterestId}/`
      : "/api/bank-interests/";
    const method = _editingBankInterestId ? "PUT" : "POST";

    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      const errMsg = err.error
        ? t(err.error, err.error)
        : t("error_failed_to_save", "Failed to save bank interest");
      throw new Error(errMsg);
    }

    if (typeof closeModal === "function") closeModal();
    showToast(t("success_saved", "Saved successfully"), "success");

    // Re-render whole balance to reflect the balance entry change globally
    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function deleteBankInterest(id) {
  if (!confirm(t("confirm_delete", "Are you sure you want to delete this?"))) return;
  try {
    const res = await fetch(`/api/bank-interests/${id}/`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");

    showToast(t("success_deleted", "Deleted successfully"), "success");

    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  }
}
