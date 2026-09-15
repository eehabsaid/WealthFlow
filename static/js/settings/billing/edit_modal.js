"use strict";
// Billing Plans settings — edit modal (plan fields + its price rows)
// This file is part of the settings module. Do not edit directly.

async function showPlanEditModal(planId) {
  const [planRes, currenciesRes] = await Promise.all([
    fetch(`/api/settings/billing/plans/${planId}/`),
    fetch("/api/currencies/"),
  ]);
  const plan = await planRes.json();
  const { currencies = [] } = await currenciesRes.json();

  const pricedCodes = new Set((plan.prices || []).map((p) => p.currency_code));
  const availableCurrencies = currencies.filter(
    (c) => !pricedCodes.has(c.code) && c.code.toLowerCase() !== "gold"
  );

  const priceRows = (plan.prices || [])
    .map(
      (p) => `
        <tr>
            <td>${p.currency_code}</td>
            <td><input type="number" step="0.01" class="form-control form-control-sm" id="price_${p.id}" value="${p.amount}"></td>
            <td>
                <button class="btn-icon" onclick="savePlanPrice(${planId}, ${p.id})"><i class="bi bi-check2"></i></button>
                <button class="btn-icon del" onclick="deletePlanPrice(${planId}, ${p.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`
    )
    .join("");

  const addPriceRow = availableCurrencies.length
    ? `
        <div class="row g-2 align-items-end mt-2">
            <div class="col-5">
                <select class="form-select form-select-sm" id="newPriceCurrency">
                    ${availableCurrencies.map((c) => `<option value="${c.id}">${c.code} — ${c.name}</option>`).join("")}
                </select>
            </div>
            <div class="col-4">
                <input type="number" step="0.01" class="form-control form-control-sm" id="newPriceAmount" placeholder="${t("amount", "Amount")}">
            </div>
            <div class="col-3">
                <button class="btn-primary-custom btn-sm w-100" onclick="addPlanPrice(${planId})">${t("btn_add", "Add")}</button>
            </div>
        </div>`
    : `<div style="color:var(--text-muted);font-size:12px;margin-top:8px;" data-i18n="all_currencies_priced">${t("all_currencies_priced", "All configured currencies already have a price. Add more in Settings > Currency.")}</div>`;

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="edit_plan">${t("edit_plan", "Edit Plan")}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-8"><label data-i18n="plan_name">${t("plan_name", "Plan")}</label><input type="text" class="form-control" id="planName" value="${plan.name}"></div>
                <div class="col-4"><label data-i18n="billing_interval_days">${t("billing_interval_days", "Interval (days)")}</label><input type="number" class="form-control" id="planIntervalDays" value="${plan.billing_interval_days}"></div>
                <div class="col-4"><label data-i18n="active">${t("active", "Active")}</label><select class="form-select" id="planActive"><option value="true" ${plan.is_active ? "selected" : ""}>${t("yes", "Yes")}</option><option value="false" ${!plan.is_active ? "selected" : ""}>${t("no", "No")}</option></select></div>
            </div>
            <hr>
            <div style="font-weight:600;color:var(--text-secondary);margin-bottom:8px;" data-i18n="prices">${t("prices", "Prices")}</div>
            <table class="data-table">
                <thead><tr><th data-i18n="currency">${t("currency", "Currency")}</th><th data-i18n="amount">${t("amount", "Amount")}</th><th data-i18n="actions">${t("actions", "Actions")}</th></tr></thead>
                <tbody>${priceRows}</tbody>
            </table>
            ${addPriceRow}
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="savePlanFields(${planId})" data-i18n="btn_save">${t("btn_save", "Save")}</button>
        </div>
    `);
  applyTranslations();
}

async function savePlanFields(planId) {
  const body = {
    name: document.getElementById("planName").value.trim(),
    billing_interval_days: parseInt(document.getElementById("planIntervalDays").value) || 30,
    is_active: document.getElementById("planActive").value === "true",
  };

  if (!body.name) {
    showToast(t("plan_name_required", "Plan name is required"), "error");
    return;
  }

  const res = await fetch(`/api/settings/billing/plans/${planId}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    closeModal();
    showToast(t("plan_saved", "Plan saved ✓"), "success");
    renderBillingSettings();
  } else {
    showToast(t("error_saving_plan", "Error saving plan"), "error");
  }
}
