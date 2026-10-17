"use strict";
// Billing settings — Customers: invoice list modal with mark paid / void / refund.
// This file is part of the settings module. Do not edit directly.

function _invoiceButtons(userId, inv) {
  const b = (cls, key, text, fn) =>
    `<button class="btn-secondary-custom btn-sm ${cls}" onclick="${fn}" data-i18n="${key}">${t(key, text)}</button>`;
  if (inv.status === "pending" || inv.status === "failed") {
    return (
      b("", "invoice_mark_paid", "Mark paid", `invoiceAction(${userId}, ${inv.id}, 'mark_paid')`) +
      " " +
      b("", "invoice_void", "Void", `invoiceAction(${userId}, ${inv.id}, 'void')`)
    );
  }
  if (inv.status === "paid")
    return b("", "invoice_refund", "Refund", `showRefundForm(${userId}, ${inv.id})`);
  return "";
}

function _invoiceRowHtml(userId, inv) {
  const refund = inv.refund_amount ? ` (${_custEsc(inv.refund_amount)})` : "";
  return `<tr>
        <td>#${inv.id}</td><td>${_custEsc(inv.plan_name)}</td>
        <td>${_custEsc(inv.amount)} ${_custEsc(inv.currency)}</td>
        <td>${t(`inv_status_${inv.status}`, inv.status)}${refund}</td>
        <td>${_custDate(inv.issued_at)}</td>
        <td>${_invoiceButtons(userId, inv)}</td>
    </tr><tr id="refundRow_${inv.id}" style="display:none"><td colspan="6"></td></tr>`;
}

function _invoiceMoreHtml(c) {
  if (c.invoice_count <= c.invoices.length) return "";
  return `<div class="modal-body pt-0" style="text-align:center;"><button class="btn-secondary-custom btn-sm" id="invoicesShowMore" onclick="loadMoreInvoices(${c.user_id})"><span data-i18n="invoices_show_more">${t("invoices_show_more", "Show more invoices")}</span> (${c.invoices.length}/${c.invoice_count})</button></div>`;
}

async function loadMoreInvoices(userId) {
  const c = _custFind(userId);
  const res = await fetch(
    `/api/settings/billing/customers/${userId}/invoices/?offset=${c.invoices.length}&limit=10`
  );
  if (!res.ok) return;
  const data = await res.json();
  const known = new Set(c.invoices.map((i) => i.id));
  c.invoices = c.invoices.concat((data.invoices || []).filter((i) => !known.has(i.id)));
  c.invoice_count = data.total;
  showCustomerInvoices(userId);
}

function showCustomerInvoices(userId) {
  const c = _custFind(userId);
  const rows = c.invoices.map((i) => _invoiceRowHtml(userId, i)).join("");
  showModal(`
        <div class="modal-header"><h5 class="modal-title">${t("customer_invoices", "Invoices")} — ${_custEsc(c.username)}</h5></div>
        <div class="modal-body">
            ${
              rows
                ? `<table class="data-table"><thead><tr><th>#</th><th data-i18n="customer_plan">${t("customer_plan", "Plan")}</th><th data-i18n="amount">${t("amount", "Amount")}</th><th data-i18n="customer_status">${t("customer_status", "Status")}</th><th></th><th data-i18n="actions">${t("actions", "Actions")}</th></tr></thead><tbody>${rows}</tbody></table>`
                : `<div style="color:var(--text-muted)" data-i18n="no_invoices">${t("no_invoices", "No invoices yet.")}</div>`
            }
        </div>
        ${_invoiceMoreHtml(c)}
        <div class="modal-footer"><button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_close">${t("btn_close", "Close")}</button></div>`);
  applyTranslations();
}

async function invoiceAction(userId, invoiceId, action) {
  if (action === "void" && !confirm(t("confirm_void_invoice", "Void this invoice?"))) return;
  const r = await _postJson(`/api/settings/billing/invoices/${invoiceId}/action/`, { action });
  if (await _customerDone(r, "customer_action_done", "Done ✓")) showCustomerInvoices(userId);
}

function showRefundForm(userId, invoiceId) {
  const inv = _custFind(userId).invoices.find((i) => i.id === invoiceId);
  const cell = document.querySelector(`#refundRow_${invoiceId} td`);
  cell.parentElement.style.display = "";
  cell.innerHTML = `<div class="row g-2 align-items-end">
        <div class="col-3"><label data-i18n="refund_amount">${t("refund_amount", "Refund amount")}</label>
            <input type="number" step="0.01" min="0.01" max="${_custEsc(inv.amount)}" class="form-control form-control-sm" id="refundAmount_${invoiceId}" value="${_custEsc(inv.amount)}"></div>
        <div class="col-4"><label data-i18n="refund_note">${t("refund_note", "Note")}</label>
            <input type="text" maxlength="255" class="form-control form-control-sm" id="refundNote_${invoiceId}"></div>
        <div class="col-3"><div class="form-check"><input type="checkbox" class="form-check-input" id="refundRevoke_${invoiceId}" checked>
            <label class="form-check-label" for="refundRevoke_${invoiceId}" data-i18n="refund_revoke_access">${t("refund_revoke_access", "Revoke access")}</label></div>
            <div class="form-check"><input type="checkbox" class="form-check-input" id="refundManual_${invoiceId}">
            <label class="form-check-label" for="refundManual_${invoiceId}" data-i18n="refund_manual_only">${t("refund_manual_only", "Record only (I returned the money myself)")}</label></div></div>
        <div class="col-2"><button class="btn-primary-custom btn-sm" onclick="submitRefund(${userId}, ${invoiceId})" data-i18n="invoice_refund">${t("invoice_refund", "Refund")}</button></div>
    </div>`;
  applyTranslations();
}

async function submitRefund(userId, invoiceId) {
  const body = {
    action: "refund",
    amount: document.getElementById(`refundAmount_${invoiceId}`).value,
    note: document.getElementById(`refundNote_${invoiceId}`).value.trim(),
    revoke_access: document.getElementById(`refundRevoke_${invoiceId}`).checked,
    manual: document.getElementById(`refundManual_${invoiceId}`).checked,
  };
  const r = await _postJson(`/api/settings/billing/invoices/${invoiceId}/action/`, body);
  if (await _customerDone(r, "refund_recorded", "Refund recorded ✓")) {
    if (r.data.gateway_refund === "manual") {
      showToast(
        t(
          "refund_manual_notice",
          "This refund was only recorded: return the money from the payment gateway's dashboard."
        ),
        "warning"
      );
    }
    showCustomerInvoices(userId);
  }
}

window.showCustomerInvoices = showCustomerInvoices;
window.loadMoreInvoices = loadMoreInvoices;
window.invoiceAction = invoiceAction;
window.showRefundForm = showRefundForm;
window.submitRefund = submitRefund;
