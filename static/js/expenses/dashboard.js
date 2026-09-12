// dashboard.js — Expense Entries dashboard: KPI constants + main page render.
// Split out of the former expenses/index.js monolith; index.js is now the
// thin window.* export aggregator for this module. See its header comment
// for the sibling list.
"use strict";

/* ════════════════════════════════════════════════════════════════════════════
   expenses.js — Expense Entries + Categories + Dashboard KPIs
   ════════════════════════════════════════════════════════════════════════════ */
"use strict";

// ════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ════════════════════════════════════════════════════════════════════════════

const MONTHS_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const MONTH_I18N_KEYS = [
  "month_january",
  "month_february",
  "month_march",
  "month_april",
  "month_may",
  "month_june",
  "month_july",
  "month_august",
  "month_september",
  "month_october",
  "month_november",
  "month_december",
];
const PAYMENT_METHODS = [
  { value: "Cash", key: "payment_cash" },
  { value: "Card", key: "payment_card" },
  { value: "Bank", key: "payment_bank" },
  { value: "Bank Transfer", key: "payment_bank_transfer" },
  { value: "Other", key: "payment_other" },
];

// ════════════════════════════════════════════════════════════════════════════
// EXPENSE ENTRIES PAGE
// ════════════════════════════════════════════════════════════════════════════

async function renderExpenses() {
  const mc = document.getElementById("main-content");
  mc.innerHTML = loadingHTML
    ? loadingHTML()
    : '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

  const today = new Date();
  const [entRes, catRes, curRes, bankRes] = await Promise.all([
    fetch(`/api/expenses/?year=${today.getFullYear()}&month=${today.getMonth() + 1}`),
    fetch("/api/expense-categories/"),
    fetch("/api/currencies/"),
    fetch("/api/banks/"),
  ]);
  const entData = await entRes.json();
  const catData = await catRes.json();
  const curData = await curRes.json();
  const bankData = await bankRes.json();

  const entries = entData.entries || [];
  const categories = catData.categories || [];
  const currencies = curData.currencies || [];
  const banks = (bankData.banks || []).filter((b) => b.is_active !== false);

  window._expCategories = categories;
  window._expCurrencies = currencies;
  window._expBanks = banks;

  // KPI cards
  const totalExp = entries.reduce((s, e) => s + (e.amount_egp || 0), 0);
  const avgDaily = totalExp / today.getDate();
  const topCat = getTopCategory(entries);

  mc.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">💸 <span data-i18n="expenses">Expenses</span></div>
        <div class="page-subtitle" data-i18n="expenses_subtitle">Track your daily spending</div>
      </div>
      <button class="btn-primary-custom" onclick="showExpenseModal(null)">
        <i class="bi bi-plus-lg"></i> <span data-i18n="add_expense">Add Expense</span>
      </button>
    </div>

    <!-- KPIs -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <div class="kpi-card" style="--kpi-accent:var(--accent-red);--kpi-bg:var(--accent-red-bg)">
          <div class="kpi-icon"><i class="bi bi-wallet2"></i></div>
          <div class="kpi-label" data-i18n="this_month">This Month</div>
          <div class="kpi-value">${fmt(totalExp)}</div>
          <div class="kpi-sub"><span data-i18n="EGP">EGP</span> <span data-i18n="total">total</span></div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="kpi-card" style="--kpi-accent:var(--accent-yellow);--kpi-bg:var(--accent-yellow-bg)">
          <div class="kpi-icon"><i class="bi bi-calendar-day"></i></div>
          <div class="kpi-label" data-i18n="daily_average">Daily Average</div>
          <div class="kpi-value">${fmt(avgDaily)}</div>
          <div class="kpi-sub"><span data-i18n="EGP">EGP</span> / <span data-i18n="day">day</span></div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="kpi-card" style="--kpi-accent:var(--accent-primary);--kpi-bg:var(--accent-blue-dim)">
          <div class="kpi-icon"><i class="bi bi-tag"></i></div>
          <div class="kpi-label" data-i18n="top_category">Top Category</div>
          <div class="kpi-value" style="font-size:16px">${topCat.icon} ${topCat.name}</div>
          <div class="kpi-sub">${fmt(topCat.total)} <span data-i18n="EGP">EGP</span></div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="kpi-card" style="--kpi-accent:var(--accent-green);--kpi-bg:var(--accent-green-bg)">
          <div class="kpi-icon"><i class="bi bi-list-check"></i></div>
          <div class="kpi-label" data-i18n="entries">Entries</div>
          <div class="kpi-value">${entries.length}</div>
          <div class="kpi-sub" data-i18n="this_month">this month</div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="expense-filters mb-3">
      <select id="fYear" class="form-select form-select-sm" onchange="applyExpenseFilters()" style="width:auto">
        ${yearOptions(today.getFullYear())}
      </select>
      <select id="fMonth" class="form-select form-select-sm" onchange="applyExpenseFilters()" style="width:auto">
        <option value="" data-i18n="all_months">All Months</option>
        ${MONTHS_NAMES.map((m, i) => `<option value="${i + 1}" ${i + 1 === today.getMonth() + 1 ? "selected" : ""} data-i18n="${MONTH_I18N_KEYS[i]}">${m}</option>`).join("")}
      </select>
      <select id="fCategory" class="form-select form-select-sm" onchange="applyExpenseFilters()" style="width:auto">
        <option value="" data-i18n="all_categories">All Categories</option>
        ${categories.map((c) => `<option value="${c.id}">${c.icon} ${c.name}</option>`).join("")}
      </select>
      <div style="position:relative;flex:1;min-width:180px">
        <i class="bi bi-search" style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--text-muted)"></i>
        <input type="text" id="fSearch" class="form-control form-control-sm"
               placeholder="Search..." data-i18n-placeholder="search_placeholder" style="padding-left:32px"
               oninput="applyExpenseFilters()">
      </div>
      <button class="btn-secondary-custom" onclick="exportExpenses()" style="padding:5px 12px;font-size:12px">
        <i class="bi bi-download"></i> <span data-i18n="export">Export</span>
      </button>
    </div>

    <!-- Table -->
    <div class="table-container" id="expenseTableWrap">
      ${renderExpenseTableHTML(entries)}
    </div>`;
  applyTranslations();
}
