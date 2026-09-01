"use strict";

async function saveBalanceEntry(entryId) {
  const bankVal = document.getElementById("bBank").value;
  const typeVal = document.getElementById("bbalance_type").value;

  const body = {
    title: document.getElementById("bTitle").value,
    balance_type: typeVal || null,
    bank_id: bankVal ? parseInt(bankVal) : null,
    currency_id: parseInt(document.getElementById("bCurrency").value) || 1,
    purity: typeVal === "gold" ? document.getElementById("bPurity")?.value || "" : "",
    amount: parseFloat(document.getElementById("bAmount").value) || 0,
    notes: document.getElementById("bNotes").value,
  };

  const url = entryId ? `/api/balance/${entryId}/` : "/api/balance/";
  const method = entryId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    closeModal();
    showToast(t("balance_entry_saved", "Balance entry saved ✓"), "success");
    renderBalance();
  } else {
    showToast(t("error_saving_entry", "Error saving entry"), "error");
  }
}

async function deleteBalanceEntry(entryId) {
  if (!confirm(t("confirm_delete_entry", "Delete this entry?"))) return;
  const res = await fetch(`/api/balance/${entryId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast(t("entry_deleted", "Entry deleted"), "success");
    renderBalance();
  }
}

// ════════════════════════════════════════════════════════════════════════════
// ALLOCATION BAR HELPER
// ════════════════════════════════════════════════════════════════════════════
