// table.js — Expense entries table rendering (used by dashboard.js render
// and by filters.js refresh). Split out of the former expenses/index.js
// monolith. See index.js header comment for the sibling list.
"use strict";

// Payment-method pill meta (visual only — value display is unchanged).
const EXP_METHOD_META = {
  Cash: { cls: "cash", icon: "bi-cash-coin", key: "payment_cash" },
  Card: { cls: "card", icon: "bi-credit-card", key: "payment_card" },
  Bank: { cls: "bank", icon: "bi-bank", key: "payment_bank" },
  "Bank Transfer": {
    cls: "bank-transfer",
    icon: "bi-arrow-left-right",
    key: "payment_bank_transfer",
  },
  Other: { cls: "other", icon: "bi-receipt", key: "payment_other" },
};

// Escape user-entered text before it goes into innerHTML (names, descriptions, colors).
function _expEsc(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderExpenseTableHTML(entries) {
  if (!entries.length) {
    return `<div class="empty-state">
      <div class="empty-icon">💸</div>
      <div class="empty-title" data-i18n="no_expenses_found">No expenses found.</div>
      <div class="empty-sub" style="margin-top:12px">
        <button class="btn-primary-custom" onclick="showExpenseModal(null)">
          <i class="bi bi-plus-lg"></i> <span data-i18n="add_first_expense">Add your first expense</span>
        </button>
      </div></div>`;
  }
  const rows = entries
    .map((e) => {
      const m = EXP_METHOD_META[e.payment_method] || {
        cls: "other",
        icon: "bi-receipt",
        key: "payment_other",
      };
      return `
    <tr>
      <td class="exp-date" data-label="${t("date", "Date")}">${formatDate(e.date)}</td>
      <td data-label="${t("category", "Category")}"><span class="exp-cat-pill" style="background:${_expEsc(e.category_color)}22;color:${_expEsc(e.category_color)}">
        ${_expEsc(e.category_icon)} ${_expEsc(e.category_name) || "—"}
      </span></td>
      <td class="exp-subcat" data-label="${t("subcategory", "Subcategory")}">${_expEsc(e.subcategory_name) || "—"}</td>
      <td class="exp-desc-cell" data-label="${t("description", "Description")}">${_expEsc(e.description) || "—"}${e.is_readonly ? ` <i class="bi bi-link-45deg" style="color:var(--text-muted)" title="${t("linked_asset_record", "Linked to a fixed asset record")}"></i>` : ""}</td>
      <td data-label="${t("method", "Method")}"><span class="exp-method exp-method-${m.cls}"><i class="bi ${m.icon}"></i>${e.payment_method ? _expEsc(t(m.key, e.payment_method)) : "—"}</span></td>
      <td class="text-end num-col amt-negative" data-label="${t("amount", "Amount")}"><span class="exp-amount">${fmt(e.amount)}</span> <span class="exp-cur">${_expEsc(e.currency_code)}</span></td>
      <td class="exp-actions" style="white-space:nowrap" data-label="${t("actions", "Actions")}">
        ${
          e.is_readonly
            ? `<button class="btn-icon" onclick="showExpenseModal(${e.id})" title="${t("view_linked_expense", "View (linked to asset)")}">
              <i class="bi bi-lock"></i></button>`
            : `<button class="btn-icon edit" onclick="showExpenseModal(${e.id})" title="${t("btn_edit", "Edit")}">
              <i class="bi bi-pencil"></i></button>
            <button class="btn-icon del" onclick="deleteExpense(${e.id})" title="${t("btn_delete", "Delete")}">
              <i class="bi bi-trash"></i></button>`
        }
      </td>
    </tr>`;
    })
    .join("");

  const total = entries.reduce((s, e) => s + (e.amount_base || 0), 0);
  return `<table class="data-table expense-table">
    <thead><tr>
      <th data-i18n="date">Date</th><th data-i18n="category">Category</th><th data-i18n="subcategory">Subcategory</th>
      <th data-i18n="description">Description</th><th data-i18n="method">Method</th>
      <th class="text-end" data-i18n="amount">Amount</th><th data-i18n="actions">Actions</th>
    </tr></thead>
    <tbody>${rows}</tbody>
    <tfoot><tr class="total-row">
      <td colspan="5" data-i18n="total">Total</td>
      <td class="text-end num-col">${fmt(total)}</td>
      <td></td>
    </tr></tfoot>
  </table>`;
}
