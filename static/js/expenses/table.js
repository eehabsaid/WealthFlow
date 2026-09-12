// table.js — Expense entries table rendering (used by dashboard.js render
// and by filters.js refresh). Split out of the former expenses/index.js
// monolith. See index.js header comment for the sibling list.
"use strict";

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
    .map(
      (e) => `
    <tr>
      <td>${formatDate(e.date)}</td>
      <td><span style="background:${e.category_color}22;color:${e.category_color};
                       padding:2px 8px;border-radius:10px;font-size:12px;font-weight:700">
        ${e.category_icon} ${e.category_name || "—"}
      </span></td>
      <td style="color:var(--text-muted);font-size:12px">${e.subcategory_name || "—"}</td>
      <td>${e.description || "—"}${e.is_readonly ? ` <i class="bi bi-link-45deg" style="color:var(--text-muted)" title="${t("linked_asset_record", "Linked to a fixed asset record")}"></i>` : ""}</td>
      <td><span style="font-size:11px;color:var(--text-muted)">${e.payment_method || "—"}</span></td>
      <td class="text-end num-col amt-negative">${fmt(e.amount)} <span style="font-size:10px;color:var(--text-muted)">${e.currency_code}</span></td>
      <td style="white-space:nowrap">
        ${
          e.is_readonly
            ? `<button class="btn-icon" onclick="showExpenseModal(${e.id})" title="${t("view_linked_expense", "View (linked to asset)")}">
              <i class="bi bi-lock"></i></button>`
            : `<button class="btn-icon edit" onclick="showExpenseModal(${e.id})" title="Edit">
              <i class="bi bi-pencil"></i></button>
            <button class="btn-icon del" onclick="deleteExpense(${e.id})" title="Delete">
              <i class="bi bi-trash"></i></button>`
        }
      </td>
    </tr>`
    )
    .join("");

  const total = entries.reduce((s, e) => s + (e.amount_egp || 0), 0);
  return `<table class="data-table">
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
