// filters.js — Expense entries filter-bar handler (year/month/category/
// search) that re-fetches and re-renders the table. Split out of the
// former expenses/index.js monolith. See index.js header comment for the
// sibling list.
"use strict";

async function applyExpenseFilters() {
  const year = document.getElementById("fYear")?.value || "";
  const month = document.getElementById("fMonth")?.value || "";
  const catId = document.getElementById("fCategory")?.value || "";
  const search = document.getElementById("fSearch")?.value || "";

  let url = "/api/expenses/?";
  if (year) url += `year=${year}&`;
  if (month) url += `month=${month}&`;
  if (catId) url += `category=${catId}&`;
  if (search) url += `search=${encodeURIComponent(search)}&`;

  const res = await fetch(url);
  const data = await res.json();
  const wrap = document.getElementById("expenseTableWrap");
  if (wrap) {
    wrap.innerHTML = renderExpenseTableHTML(data.entries || []);
    applyTranslations();
  }
}
