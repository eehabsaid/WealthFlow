"use strict";
// Billing settings — Customers actions: suspend/unsuspend, extend trial, change plan, invoices, refund.
// This file is part of the settings module. Do not edit directly.

async function _postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, data };
}

function _custFind(userId) {
  return _customers.find((c) => c.user_id === userId);
}

async function _customerDone(result, doneKey, doneText) {
  if (result.ok) {
    showToast(t(doneKey, doneText), "success");
    await renderCustomersCard();
    return true;
  }
  showToast(result.data.message || t("customer_action_failed", "Action failed"), "error");
  return false;
}

async function customerAction(userId, action) {
  if (
    action === "suspend" &&
    !confirm(
      t("confirm_suspend_customer", "Suspend this account? The user loses access immediately.")
    )
  ) {
    return;
  }
  const r = await _postJson(`/api/settings/billing/customers/${userId}/action/`, { action });
  await _customerDone(r, "customer_action_done", "Done ✓");
}

function showExtendTrialModal(userId) {
  const c = _custFind(userId);
  showModal(`
        <div class="modal-header"><h5 class="modal-title" data-i18n="customer_extend_trial">${t("customer_extend_trial", "Extend trial")}</h5></div>
        <div class="modal-body">
            <div style="margin-bottom:8px;">${_custEsc(c.username)}</div>
            <label data-i18n="customer_days">${t("customer_days", "Days to add")}</label>
            <input type="number" min="1" max="365" class="form-control" id="extendTrialDays" value="7">
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="submitExtendTrial(${userId})" data-i18n="btn_save">${t("btn_save", "Save")}</button>
        </div>`);
  applyTranslations();
}

async function submitExtendTrial(userId) {
  const days = parseInt(document.getElementById("extendTrialDays").value, 10);
  const r = await _postJson(`/api/settings/billing/customers/${userId}/action/`, {
    action: "extend_trial",
    days,
  });
  if (await _customerDone(r, "customer_action_done", "Done ✓")) closeModal();
}

async function showChangePlanModal(userId) {
  const c = _custFind(userId);
  const res = await fetch("/api/settings/billing/plans/");
  const plans = ((await res.json()).plans || []).filter((p) => p.is_active);
  const options = plans
    .map(
      (p) =>
        `<option value="${p.id}" ${p.id === c.subscription.plan.id ? "selected" : ""}>${_custEsc(p.name)}</option>`
    )
    .join("");
  showModal(`
        <div class="modal-header"><h5 class="modal-title" data-i18n="customer_change_plan">${t("customer_change_plan", "Change plan")}</h5></div>
        <div class="modal-body">
            <div style="margin-bottom:8px;">${_custEsc(c.username)}</div>
            <select class="form-select" id="changePlanSelect">${options}</select>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="submitChangePlan(${userId})" data-i18n="btn_save">${t("btn_save", "Save")}</button>
        </div>`);
  applyTranslations();
}

async function submitChangePlan(userId) {
  const plan_id = parseInt(document.getElementById("changePlanSelect").value, 10);
  const r = await _postJson(`/api/settings/billing/customers/${userId}/action/`, {
    action: "change_plan",
    plan_id,
  });
  if (await _customerDone(r, "customer_action_done", "Done ✓")) closeModal();
}

window.customerAction = customerAction;
window.showExtendTrialModal = showExtendTrialModal;
window.submitExtendTrial = submitExtendTrial;
window.showChangePlanModal = showChangePlanModal;
window.submitChangePlan = submitChangePlan;
