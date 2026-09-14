"use strict";
// Billing Plans settings — per-currency price CRUD
// This file is part of the settings module. Do not edit directly.

async function savePlanPrice(planId, priceId) {
  const amount = parseFloat(document.getElementById(`price_${priceId}`).value) || 0;
  const res = await fetch(`/api/settings/billing/plans/${planId}/prices/${priceId}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount }),
  });
  if (res.ok) {
    showToast(t("plan_saved", "Plan saved ✓"), "success");
    showPlanEditModal(planId);
    renderBillingSettings();
  } else {
    showToast(t("error_saving_plan", "Error saving plan"), "error");
  }
}

async function deletePlanPrice(planId, priceId) {
  const res = await fetch(`/api/settings/billing/plans/${planId}/prices/${priceId}/`, {
    method: "DELETE",
  });
  if (res.ok) {
    showToast(t("plan_saved", "Plan saved ✓"), "success");
    showPlanEditModal(planId);
    renderBillingSettings();
  } else {
    showToast(t("error_saving_plan", "Error saving plan"), "error");
  }
}

async function addPlanPrice(planId) {
  const currencyEl = document.getElementById("newPriceCurrency");
  const amountEl = document.getElementById("newPriceAmount");
  if (!currencyEl) {
    return;
  }
  const body = {
    currency: parseInt(currencyEl.value),
    amount: parseFloat(amountEl.value) || 0,
  };

  const res = await fetch(`/api/settings/billing/plans/${planId}/prices/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    showToast(t("plan_saved", "Plan saved ✓"), "success");
    showPlanEditModal(planId);
    renderBillingSettings();
  } else {
    const err = await res.json().catch(() => ({}));
    showToast(err.error || t("error_saving_plan", "Error saving plan"), "error");
  }
}
