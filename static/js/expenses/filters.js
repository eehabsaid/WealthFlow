// filters.js — Expense entries filter-bar handler (year/month/category/
// search) that re-fetches and re-renders the table. Split out of the
// former expenses/index.js monolith. See index.js header comment for the
// sibling list.
"use strict";

async function applyExpenseFilters() {
  const year = document.getElementById("fYear")?.value || "";
  const month = document.getElementById("fMonth")?.value || "";
  const catId = document.getElementById("fCategory")?.value || "";
  const subId = document.getElementById("fSubcategory")?.value || "";
  const pm = document.getElementById("fPaymentMethod")?.value || "";
  const bankId = document.getElementById("fBank")?.value || "";
  const dateFrom = document.getElementById("fDateFrom")?.value || "";
  const dateTo = document.getElementById("fDateTo")?.value || "";
  const amountMin = document.getElementById("fAmountMin")?.value || "";
  const amountMax = document.getElementById("fAmountMax")?.value || "";
  const search = document.getElementById("fSearch")?.value || "";

  let url = "/api/expenses/?";
  if (year) url += `year=${year}&`;
  if (month) url += `month=${month}&`;
  if (catId) url += `category=${catId}&`;
  if (subId) url += `subcategory=${subId}&`;
  if (pm) url += `payment_method=${encodeURIComponent(pm)}&`;
  if (bankId) url += `bank=${bankId}&`;
  if (dateFrom) url += `start=${dateFrom}&`;
  if (dateTo) url += `end=${dateTo}&`;
  if (amountMin) url += `amount_min=${encodeURIComponent(amountMin)}&`;
  if (amountMax) url += `amount_max=${encodeURIComponent(amountMax)}&`;
  if (search) url += `search=${encodeURIComponent(search)}&`;

  const res = await fetch(url);
  const data = await res.json();
  const entries = data.entries || [];
  const wrap = document.getElementById("expenseTableWrap");
  if (wrap) {
    wrap.innerHTML = renderExpenseTableHTML(entries);
    applyTranslations();
  }
  if (typeof updateExpenseMatchCount === "function") updateExpenseMatchCount(entries.length);
}
