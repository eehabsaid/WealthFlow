"use strict";
// Backend live-calculation + save/delete handlers.
// Part of the balance module (split from the former monolithic
// currency_exchange.js, 200-line rule). Do not edit directly.

async function calculateBackendExchange(isUserRateChange = false) {
  const fromId = document.getElementById("ce_from_balance")?.value;
  const toId = document.getElementById("ce_to_balance")?.value;
  const fromAmt = document.getElementById("ce_from_amount")?.value || 0;
  const userRate = isUserRateChange ? document.getElementById("ce_rate")?.value || null : null;

  if (!fromId) return;

  try {
    const payload = {
      from_balance_id: fromId,
      to_balance_id: toId,
      from_amount: fromAmt,
      exchange_rate: userRate,
    };

    const res = await fetch("/api/currency-exchanges/calculate/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) return;

    const calc = await res.json();

    const fromCurrEl = document.getElementById("ce_from_currency");
    const availEl = document.getElementById("ce_available_balance");
    const fromLbl = document.getElementById("ce_from_curr_label");
    const toCurrEl = document.getElementById("ce_to_currency");
    const rateEl = document.getElementById("ce_rate");
    const toAmtEl = document.getElementById("ce_to_amount");
    const toLbl = document.getElementById("ce_to_curr_label");

    if (fromCurrEl) fromCurrEl.value = `${calc.from_currency_flag} ${calc.from_currency_code}`;
    if (availEl) availEl.value = `${fmt(calc.available_balance)} ${calc.from_currency_code}`;
    if (fromLbl) fromLbl.textContent = calc.from_currency_code;

    if (toCurrEl && calc.to_currency_code)
      toCurrEl.value = `${calc.to_currency_flag} ${calc.to_currency_code}`;
    if (toLbl && calc.to_currency_code) toLbl.textContent = calc.to_currency_code;

    if (rateEl && !isUserRateChange) {
      rateEl.value = calc.exchange_rate;
    }

    if (toAmtEl) {
      toAmtEl.value = fmt(calc.to_amount);
    }
  } catch (e) {
    // Silently ignore backend calculation failures.
  }
}

async function saveExchange() {
  const btn = document.getElementById("saveExchangeBtn");
  if (btn) btn.disabled = true;

  const payload = {
    exchange_date: document.getElementById("ce_date").value,
    from_balance_id: document.getElementById("ce_from_balance").value,
    to_balance_id: document.getElementById("ce_to_balance").value,
    from_amount: document.getElementById("ce_from_amount").value,
    exchange_rate: document.getElementById("ce_rate").value,
    notes: document.getElementById("ce_notes").value,
  };

  try {
    const url = _editingExchangeId
      ? `/api/currency-exchanges/${_editingExchangeId}/`
      : "/api/currency-exchanges/";
    const method = _editingExchangeId ? "PUT" : "POST";

    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      const errMsg = err.error
        ? t(err.error, err.error)
        : t("error_failed_to_save", "Failed to save exchange");
      throw new Error(errMsg);
    }

    if (typeof closeModal === "function") closeModal();
    showToast(t("success_saved", "Saved successfully"), "success");

    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function deleteExchange(id) {
  if (
    !confirm(
      t(
        "confirm_delete",
        "Are you sure you want to delete this exchange transaction? It will be reversed automatically."
      )
    )
  )
    return;
  try {
    const res = await fetch(`/api/currency-exchanges/${id}/`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Delete failed");
    }

    showToast(t("success_reversed", "Transaction reversed successfully"), "success");

    if (typeof renderBalance === "function") {
      await renderBalance();
    }
  } catch (e) {
    showToast(e.message, "danger");
  }
}

