// filter_bar.js — advanced expense filters: subcategory, payment method,
// bank, date range, amount range; clear-all; matching-entries count.
"use strict";

function expenseSubsForCategory(catId) {
  const cats = window._expCategories || [];
  const subs = [];
  cats.forEach((c) => {
    if (catId && String(c.id) !== String(catId)) return;
    (c.subcategories || []).forEach((s) => subs.push({ id: s.id, name: s.name }));
  });
  return subs;
}

function updateExpenseSubcategoryOptions(catId) {
  const sel = document.getElementById("fSubcategory");
  if (!sel) return;
  if (!window._expCategories || !window._expCategories.length) {
    fetch("/api/expense-categories/", { headers: { Accept: "application/json" } })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        const list = Array.isArray(data) ? data : data.categories || [];
        if (list.length) window._expCategories = list;
        rebuildExpenseSubcategoryOptions(sel, catId);
      })
      .catch(() => rebuildExpenseSubcategoryOptions(sel, catId));
    return;
  }
  rebuildExpenseSubcategoryOptions(sel, catId);
}

function rebuildExpenseSubcategoryOptions(sel, catId) {
  const current = sel.value;
  const subs = expenseSubsForCategory(catId);
  sel.innerHTML =
    '<option value="" data-i18n="all_subcategories">All Subcategories</option>' +
    subs.map((s) => `<option value="${s.id}">${s.name}</option>`).join("");
  if (catId !== "" && !subs.some((s) => String(s.id) === String(current))) sel.value = "";
  if (typeof applyTranslations === "function") applyTranslations();
}

function expenseFilterOptions() {
  const subs = expenseSubsForCategory("");
  return {
    subs,
    banks: window._expBanks || [],
    methods: [
      { value: "Cash", key: "payment_cash" },
      { value: "Card", key: "payment_card" },
      { value: "Bank Transfer", key: "payment_bank_transfer" },
      { value: "Other", key: "payment_other" },
    ],
  };
}

function renderExpenseFilterBar() {
  const el = document.getElementById("expenseFilterBar");
  if (!el) return;
  const { subs, banks, methods } = expenseFilterOptions();
  el.innerHTML = `
    <div class="d-flex flex-wrap gap-2 align-items-center">
      <select id="fSubcategory" class="form-select form-select-sm" style="width:auto" onchange="applyExpenseFilters()">
        <option value="" data-i18n="all_subcategories">All Subcategories</option>
        ${subs.map((s) => `<option value="${s.id}">${s.name}</option>`).join("")}
      </select>
      <select id="fPaymentMethod" class="form-select form-select-sm" style="width:auto" onchange="applyExpenseFilters()">
        <option value="" data-i18n="all_payment_methods">All Payment Methods</option>
        ${methods.map((m) => `<option value="${m.value}" data-i18n="${m.key}">${m.value}</option>`).join("")}
      </select>
      <select id="fBank" class="form-select form-select-sm" style="width:auto" onchange="applyExpenseFilters()">
        <option value="" data-i18n="all_banks">All Banks</option>
        ${banks.map((b) => `<option value="${b.id}">${b.name}</option>`).join("")}
      </select>
      <input type="date" id="fDateFrom" class="form-control form-control-sm" style="width:auto" onchange="applyExpenseFilters()" aria-label="${typeof t === "function" ? t("date_from") : "From"}">
      <input type="date" id="fDateTo" class="form-control form-control-sm" style="width:auto" onchange="applyExpenseFilters()" aria-label="${typeof t === "function" ? t("date_to") : "To"}">
      <input type="number" id="fAmountMin" class="form-control form-control-sm" style="width:110px" min="0" step="0.01" placeholder="${typeof t === "function" ? t("amount_min") : "Min"}" data-i18n-placeholder="amount_min" onchange="applyExpenseFilters()">
      <input type="number" id="fAmountMax" class="form-control form-control-sm" style="width:110px" min="0" step="0.01" placeholder="${typeof t === "function" ? t("amount_max") : "Max"}" data-i18n-placeholder="amount_max" onchange="applyExpenseFilters()">
      <button class="btn-secondary-custom" onclick="clearExpenseFilters()" style="padding:5px 12px;font-size:12px">
        <i class="bi bi-x-circle"></i> <span data-i18n="clear_all_filters">Clear All</span>
      </button>
    </div>
    <div class="expense-match-count text-muted small mt-2" id="expenseMatchCount"></div>`;
}

function updateExpenseMatchCount(n) {
  const el = document.getElementById("expenseMatchCount");
  if (!el) return;
  const text = typeof t === "function" ? t("matching_expenses") : "{0} matching expenses";
  el.textContent = text.replace("{0}", String(n));
}

function clearExpenseFilters() {
  [
    "fSubcategory",
    "fPaymentMethod",
    "fBank",
    "fDateFrom",
    "fDateTo",
    "fAmountMin",
    "fAmountMax",
    "fSearch",
  ].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  applyExpenseFilters();
}
