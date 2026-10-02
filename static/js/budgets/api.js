"use strict";

async function saveBudget(id) {
  const body = {
    name: document.getElementById("bName").value.trim(),
    category_id: parseInt(document.getElementById("bCat").value) || null,
    period: document.getElementById("bPeriod").value,
    amount: parseFloat(document.getElementById("bAmount").value) || 0,
    currency_id: parseInt(document.getElementById("bCurrency").value) || null,
    alert_threshold_percent: parseInt(document.getElementById("bThreshold").value) || 80,
    is_active: true,
  };
  const url = id ? `/api/budgets/${id}/` : "/api/budgets/";
  const res = await fetch(url, {
    method: id ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast(t("budget_saved", "Budget saved ✓"), "success");
    renderBudgets();
  } else {
    const payload = await res.json().catch(() => ({}));
    showToast(payload.error || t("error_saving_budget", "Error saving budget"), "error");
  }
}

async function deleteBudget(id) {
  if (!confirm(t("confirm_delete_budget", "Delete this budget?"))) return;
  const res = await fetch(`/api/budgets/${id}/`, { method: "DELETE" });
  if (res.ok) {
    showToast(t("budget_deleted", "Budget deleted"), "success");
    renderBudgets();
  } else {
    showToast(t("error_deleting_budget", "Error deleting budget"), "error");
  }
}

async function saveRecurring(id) {
  const body = {
    name: document.getElementById("rName").value.trim(),
    category_id: parseInt(document.getElementById("rCat").value) || null,
    amount: parseFloat(document.getElementById("rAmount").value) || 0,
    currency_id: parseInt(document.getElementById("rCurrency").value) || null,
    payment_method: document.getElementById("rMethod").value,
    bank_id: parseInt(document.getElementById("rBank")?.value) || null,
    frequency: document.getElementById("rFrequency").value,
    interval: parseInt(document.getElementById("rInterval").value) || 1,
    start_date: document.getElementById("rStartDate").value,
    end_date: document.getElementById("rEndDate").value || null,
    notes: document.getElementById("rNotes").value.trim(),
    is_active: document.getElementById("rActive").checked,
  };
  const backfill = document.getElementById("rBackfill");
  if (!id && backfill) body.backfill_missed = backfill.checked;
  const url = id ? `/api/recurring-transactions/${id}/` : "/api/recurring-transactions/";
  const res = await fetch(url, {
    method: id ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast(t("recurring_saved", "Recurring transaction saved ✓"), "success");
    renderBudgets();
  } else {
    const payload = await res.json().catch(() => ({}));
    showToast(
      payload.error || t("error_saving_recurring", "Error saving recurring transaction"),
      "error"
    );
  }
}

async function deleteRecurring(id) {
  if (!confirm(t("confirm_delete_recurring", "Delete this recurring transaction?"))) return;
  const res = await fetch(`/api/recurring-transactions/${id}/`, { method: "DELETE" });
  if (res.ok) {
    showToast(t("recurring_deleted", "Recurring transaction deleted"), "success");
    renderBudgets();
  } else {
    showToast(t("error_deleting_recurring", "Error deleting recurring transaction"), "error");
  }
}

async function toggleRecurringActive(id, isActive) {
  const res = await fetch(`/api/recurring-transactions/${id}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  });
  if (res.ok) {
    renderBudgets();
  } else {
    showToast(t("error_saving_recurring", "Error saving recurring transaction"), "error");
  }
}

async function processDueRecurring() {
  const previewRes = await fetch("/api/recurring-transactions/due-preview/");
  if (!previewRes.ok) {
    showToast(t("error_processing_recurring", "Error processing recurring transactions"), "error");
    return;
  }
  const due = (await previewRes.json()).due || [];
  if (!due.length) {
    showToast(t("no_recurring_due", "No recurring transactions due"), "success");
    return;
  }
  const lines = due.slice(0, 15).map((d) => `${d.date}  ${d.name}  ${d.amount} ${d.currency_code}`);
  if (due.length > 15) lines.push(`… +${due.length - 15}`);
  const message = `${t("recurring_confirm_post", "These expenses will be created and deducted from your balances:")}\n\n${lines.join("\n")}\n\n${due.length} ${t("recurring_confirm_count_suffix", "expense(s) in total. Continue?")}`;
  if (!confirm(message)) return;

  const res = await fetch("/api/recurring-transactions/process-due/", { method: "POST" });
  if (res.ok) {
    const data = await res.json();
    const count = (data.created || []).length;
    showToast(
      count
        ? `${count} ${t("recurring_posted_suffix", "recurring transaction(s) posted")}`
        : t("no_recurring_due", "No recurring transactions due"),
      "success"
    );
    renderBudgets();
    refreshFinancialViewsAfterExpenseChange();
  } else {
    showToast(t("error_processing_recurring", "Error processing recurring transactions"), "error");
  }
}
