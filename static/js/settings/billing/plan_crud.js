"use strict";
// Billing Plans settings — create/delete a plan
// This file is part of the settings module. Do not edit directly.

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
