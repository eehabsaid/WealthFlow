"use strict";
// Billing Plans settings — list/table render
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
