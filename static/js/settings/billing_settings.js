"use strict";
// Billing Plans settings (admin-only pricing management)
// Prices are always drawn from the app's configured Currency list
// (Settings > Currency) — never hardcoded to a fixed set of currencies.
// This file is part of the settings module. Do not edit directly.

function _planPricesSummary(plan) {
  if (!plan.prices || !plan.prices.length) {
    return `<span style="color:var(--text-muted)">${t("no_prices_set", "No prices set")}</span>`;
  }
  return plan.prices
    .map((p) => `${fmt(p.amount)} ${p.currency_code}`)
    .join(", ");
}

async function renderBillingSettings() {
  const res = await fetch("/api/settings/billing/plans/");
  if (res.status === 403 || res.status === 401) {
    document.getElementById("settingsContent").innerHTML = `
        <div style="padding:20px;color:var(--text-muted)" data-i18n="admin_access_required">
            ${t("admin_access_required", "Admin access required.")}
        </div>`;
    return;
  }
  const data = await res.json();
  const plans = data.plans || [];

  const rows = plans
    .map(
      (p) => `
        <tr>
            <td>${p.name}</td>
            <td>${_planPricesSummary(p)}</td>
            <td>${p.billing_interval_days}</td>
            <td><span style="color:${p.is_active ? "var(--accent-green)" : "var(--accent-red)"}" data-i18n="${p.is_active ? "active" : "inactive"}">${p.is_active ? t("active", "Active") : t("inactive", "Inactive")}</span></td>
            <td>
                <button class="btn-icon" onclick="showPlanEditModal(${p.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deletePlan(${p.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="billing_plans">
                    ${t("billing_plans", "Billing Plans")}
                </div>
                <button class="btn-primary-custom" onclick="showPlanCreateModal()" data-i18n="add_plan">${t("add_plan", "Add Plan")}</button>
            </div>
            <div style="margin-bottom:8px;color:var(--text-muted);font-size:12px;" data-i18n="billing_plans_hint">
                ${t("billing_plans_hint", "Prices use the currencies configured in Settings > Currency.")}
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="plan_name">${t("plan_name", "Plan")}</th>
                            <th data-i18n="prices">${t("prices", "Prices")}</th>
                            <th data-i18n="billing_interval_days">${t("billing_interval_days", "Interval (days)")}</th>
                            <th data-i18n="active">${t("active", "Active")}</th>
                            <th data-i18n="actions">${t("actions", "Actions")}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>
    `;

  applyTranslations();
}

async function showPlanCreateModal() {
  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="add_plan">${t("add_plan", "Add Plan")}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-8"><label data-i18n="plan_name">${t("plan_name", "Plan")}</label><input type="text" class="form-control" id="newPlanName" placeholder="${t("plan_name_placeholder", "e.g. Enterprise")}"></div>
                <div class="col-4"><label data-i18n="billing_interval_days">${t("billing_interval_days", "Interval (days)")}</label><input type="number" class="form-control" id="newPlanIntervalDays" value="30"></div>
                <div class="col-4"><label data-i18n="active">${t("active", "Active")}</label><select class="form-select" id="newPlanActive"><option value="true" selected>${t("yes", "Yes")}</option><option value="false">${t("no", "No")}</option></select></div>
                <div class="col-4"><label data-i18n="sort_order">${t("sort_order", "Sort order")}</label><input type="number" class="form-control" id="newPlanSortOrder" value="0"></div>
            </div>
            <div style="color:var(--text-muted);font-size:12px;margin-top:8px;" data-i18n="add_plan_prices_hint">${t("add_plan_prices_hint", "You can add prices for this plan after creating it.")}</div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="createPlan()" data-i18n="btn_save">${t("btn_save", "Save")}</button>
        </div>
    `);
  applyTranslations();
}

async function createPlan() {
  const body = {
    name: document.getElementById("newPlanName").value.trim(),
    billing_interval_days: parseInt(document.getElementById("newPlanIntervalDays").value) || 30,
    is_active: document.getElementById("newPlanActive").value === "true",
    sort_order: parseInt(document.getElementById("newPlanSortOrder").value) || 0,
  };

  if (!body.name) {
    showToast(t("plan_name_required", "Plan name is required"), "error");
    return;
  }

  const res = await fetch("/api/settings/billing/plans/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    const plan = await res.json();
    closeModal();
    showToast(t("plan_saved", "Plan saved ✓"), "success");
    await renderBillingSettings();
    showPlanEditModal(plan.id);
  } else {
    showToast(t("error_saving_plan", "Error saving plan"), "error");
  }
}

async function deletePlan(planId) {
  if (!confirm(t("confirm_delete_plan", "Delete this plan? This can't be undone."))) {
    return;
  }
  const res = await fetch(`/api/settings/billing/plans/${planId}/`, { method: "DELETE" });
  if (res.ok) {
    showToast(t("plan_deleted", "Plan deleted"), "success");
    renderBillingSettings();
  } else {
    const err = await res.json().catch(() => ({}));
    showToast(err.error || t("error_deleting_plan", "Error deleting plan"), "error");
  }
}

async function showPlanEditModal(planId) {
  const [planRes, currenciesRes] = await Promise.all([
    fetch(`/api/settings/billing/plans/${planId}/`),
    fetch("/api/currencies/"),
  ]);
  const plan = await planRes.json();
  const { currencies = [] } = await currenciesRes.json();

  const pricedCodes = new Set((plan.prices || []).map((p) => p.currency_code));
  const availableCurrencies = currencies.filter((c) => !pricedCodes.has(c.code) && c.code.toLowerCase() !== "gold");

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
