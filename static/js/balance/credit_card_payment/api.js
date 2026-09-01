"use strict";

// balance/credit_card_payment/api.js — Credit Card Payment save/delete calls
// ════════════════════════════════════════════════════════════════════════════

async function saveCreditCardPayment() {
  const btn = document.getElementById("saveCreditCardPaymentBtn");
  if (btn) btn.disabled = true;

  const payload = {
    payment_date: document.getElementById("ccp_date").value,
    bank_id: document.getElementById("ccp_bank").value,
    payment_method: document.getElementById("ccp_method").value,
    card_label: document.getElementById("ccp_card_label").value,
    amount_egp: document.getElementById("ccp_amount").value,
    notes: document.getElementById("ccp_notes").value,
  };

  try {
    const url = _editingCreditCardPaymentId
      ? `/api/credit-card-payments/${_editingCreditCardPaymentId}/`
      : "/api/credit-card-payments/";
    const method = _editingCreditCardPaymentId ? "PUT" : "POST";

    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      const errMsg = err.error
        ? t(err.error, err.error)
        : t("error_failed_to_save", "Failed to save credit card payment");
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

async function deleteCreditCardPayment(id) {
  if (!confirm(t("confirm_delete", "Are you sure you want to delete this?"))) return;
  try {
    const res = await fetch(`/api/credit-card-payments/${id}/`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");

    showToast(t("success_deleted", "Deleted successfully"), "success");

    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  }
}
