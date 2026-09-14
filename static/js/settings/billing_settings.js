"use strict";
// Billing Plans settings (admin-only pricing management)
// This file is part of the settings module. Do not edit directly.

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
            <td class="num-fmt" data-value="${p.price_egp}">${fmt(p.price_egp)} EGP</td>
            <td class="num-fmt" data-value="${p.price_usd}">$${fmt(p.price_usd)}</td>
            <td>${p.billing_interval_days}</td>
            <td><span style="color:${p.is_active ? "var(--accent-green)" : "var(--accent-red)"}" data-i18n="${p.is_active ? "active" : "inactive"}">${p.is_active ? t("active", "Active") : t("inactive", "Inactive")}</span></td>
            <td>
                <button class="btn-icon" onclick="showPlanEditModal(${p.id})"><i class="bi bi-pencil"></i></button>
            </td>
        </tr>
    `
    )
    .join("");

  document.getElementById("settingsContent").innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;">
            <div style="font-weight:600;color:var(--text-secondary);margin-bottom:10px;" data-i18n="billing_plans">
                ${t("billing_plans", "Billing Plans")}
            </div>
            <div style="margin-bottom:8px;color:var(--text-muted);font-size:12px;" data-i18n="billing_plans_hint">
                ${t("billing_plans_hint", "These prices are shown to customers on checkout and the trial banner.")}
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="plan_name">${t("plan_name", "Plan")}</th>
                            <th data-i18n="price_egp">${t("price_egp", "Price (EGP)")}</th>
                            <th data-i18n="price_usd">${t("price_usd", "Price (USD)")}</th>
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

async function showPlanEditModal(planId) {
  const res = await fetch(`/api/settings/billing/plans/${planId}/`);
  const plan = await res.json();

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="edit_plan">${t("edit_plan", "Edit Plan")}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12"><label data-i18n="plan_name">${t("plan_name", "Plan")}</label><input type="text" class="form-control" id="planName" value="${plan.name}"></div>
                <div class="col-6"><label data-i18n="price_egp">${t("price_egp", "Price (EGP)")}</label><input type="number" step="0.01" class="form-control" id="planPriceEgp" value="${plan.price_egp}"></div>
                <div class="col-6"><label data-i18n="price_usd">${t("price_usd", "Price (USD)")}</label><input type="number" step="0.01" class="form-control" id="planPriceUsd" value="${plan.price_usd}"></div>
                <div class="col-6"><label data-i18n="billing_interval_days">${t("billing_interval_days", "Interval (days)")}</label><input type="number" class="form-control" id="planIntervalDays" value="${plan.billing_interval_days}"></div>
                <div class="col-6"><label data-i18n="active">${t("active", "Active")}</label><select class="form-select" id="planActive"><option value="true" ${plan.is_active ? "selected" : ""}>${t("yes", "Yes")}</option><option value="false" ${!plan.is_active ? "selected" : ""}>${t("no", "No")}</option></select></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="savePlanEdit(${planId})" data-i18n="btn_save">${t("btn_save", "Save")}</button>
        </div>
    `);
  applyTranslations();
}

async function savePlanEdit(planId) {
  const body = {
    name: document.getElementById("planName").value.trim(),
    price_egp: parseFloat(document.getElementById("planPriceEgp").value) || 0,
    price_usd: parseFloat(document.getElementById("planPriceUsd").value) || 0,
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
