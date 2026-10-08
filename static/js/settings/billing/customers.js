"use strict";
// Billing settings — Customers (sysadmin): plan / status / trial end / period end / invoices per user.
// This file is part of the settings module. Do not edit directly.

let _customers = [];

function _custEsc(value) {
  const d = document.createElement("div");
  d.textContent = value == null ? "" : String(value);
  return d.innerHTML;
}

function _custDate(value) {
  return value ? formatDate(value) : "-";
}

function _custStatus(status) {
  return t(`sub_status_${status}`, status);
}

function _custRowHtml(c) {
  const s = c.subscription;
  const suspended = s && s.status === "suspended";
  const btn = (icon, titleKey, title, fn) =>
    `<button class="btn-icon" title="${t(titleKey, title)}" onclick="${fn}"><i class="bi ${icon}"></i></button>`;
  const actions = s
    ? [
        suspended
          ? btn(
              "bi-play-circle",
              "customer_unsuspend",
              "Unsuspend",
              `customerAction(${c.user_id}, 'unsuspend')`
            )
          : btn(
              "bi-pause-circle",
              "customer_suspend",
              "Suspend",
              `customerAction(${c.user_id}, 'suspend')`
            ),
        btn(
          "bi-calendar-plus",
          "customer_extend_trial",
          "Extend trial",
          `showExtendTrialModal(${c.user_id})`
        ),
        btn(
          "bi-arrow-left-right",
          "customer_change_plan",
          "Change plan",
          `showChangePlanModal(${c.user_id})`
        ),
        btn("bi-receipt", "customer_invoices", "Invoices", `showCustomerInvoices(${c.user_id})`),
      ].join("")
    : `<span style="color:var(--text-muted)" data-i18n="customer_no_subscription">${t("customer_no_subscription", "No subscription")}</span>`;
  return `<tr>
        <td>${_custEsc(c.username)}<div style="color:var(--text-muted);font-size:12px;">${_custEsc(c.email)}</div></td>
        <td>${s ? _custEsc(s.plan.name) : "-"}</td>
        <td>${s ? _custStatus(s.status) : "-"}</td>
        <td>${s ? _custDate(s.trial_end) : "-"}</td>
        <td>${s ? _custDate(s.current_period_end) : "-"}</td>
        <td>${c.invoice_count}</td>
        <td>${actions}</td>
    </tr>`;
}

function _customersCardHtml() {
  const rows = _customers.map(_custRowHtml).join("");
  const body = rows
    ? `<div class="table-container"><table class="data-table" id="customersTable">
            <thead><tr>
                <th data-i18n="customer_user">${t("customer_user", "User")}</th>
                <th data-i18n="customer_plan">${t("customer_plan", "Plan")}</th>
                <th data-i18n="customer_status">${t("customer_status", "Status")}</th>
                <th data-i18n="customer_trial_end">${t("customer_trial_end", "Trial ends")}</th>
                <th data-i18n="customer_period_end">${t("customer_period_end", "Period ends")}</th>
                <th data-i18n="customer_invoices">${t("customer_invoices", "Invoices")}</th>
                <th data-i18n="actions">${t("actions", "Actions")}</th>
            </tr></thead><tbody>${rows}</tbody></table></div>`
    : `<div style="color:var(--text-muted)" data-i18n="no_customers">${t("no_customers", "No customers found.")}</div>`;
  return `<div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px;">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="customers_title">${t("customers_title", "Customers")}</div>
            <input type="search" class="form-control form-control-sm" style="max-width:220px;" id="customersSearch" placeholder="${t("customers_search", "Search users")}" onkeydown="if(event.key==='Enter')renderCustomersCard()">
        </div>
        ${body}
    </div>`;
}

async function renderCustomersCard(keepSearch = true) {
  const mount = document.getElementById("customersMount");
  if (!mount) return;
  const prev = keepSearch ? (document.getElementById("customersSearch") || {}).value || "" : "";
  const res = await fetch(`/api/settings/billing/customers/?q=${encodeURIComponent(prev)}`);
  if (!res.ok) return;
  _customers = (await res.json()).customers || [];
  mount.innerHTML = _customersCardHtml();
  const input = document.getElementById("customersSearch");
  if (input) input.value = prev;
  const table = document.getElementById("customersTable");
  if (table && window.AIA && AIA.resetCollapsible) AIA.resetCollapsible(table);
  if (typeof initCollapsibleTables === "function") initCollapsibleTables();
  applyTranslations();
}

window.renderCustomersCard = renderCustomersCard;
