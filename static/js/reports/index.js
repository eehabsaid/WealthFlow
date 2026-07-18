'use strict';

/* ════════════════════════════════════════════════════════════════════════════
   reports.js — Reports Page (Monthly / Yearly / Custom)
   Income vs Expenses analysis and PDF export
   ════════════════════════════════════════════════════════════════════════════ */
"use strict";

// ════════════════════════════════════════════════════════════════════════════
// MODULE STATE
// ════════════════════════════════════════════════════════════════════════════

var currentReportYear = 2026;
let _currentTab = "monthly";
const REPORT_MONTH_I18N_KEYS = [
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

// ════════════════════════════════════════════════════════════════════════════
// REPORTS RENDERING
// ════════════════════════════════════════════════════════════════════════════

async function renderReports() {
  const mc = document.getElementById("main-content");
  const today = new Date();

  currentReportYear = today.getFullYear();
  const month = today.getMonth() + 1;
  _currentTab = "monthly";

  const reportsTitle = t('reports_title', '📊 Reports');
  const reportsDesc = t('reports_income_expenses_analysis', 'Income vs Expenses analysis and PDF export');
  const monthlyText = t('tab_monthly', 'Monthly');
  const yearlyText = t('tab_yearly', 'Yearly');
  const customText = t('tab_custom_range', 'Custom Range');

  mc.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title reports-page-title" data-i18n="tab_monthly">${monthlyText}</div>
        <div class="page-subtitle" data-i18n="reports_income_expenses_analysis">${reportsDesc}</div>
      </div>
    </div>

    <div class="wf-tabs-shell mb-4">
      <div class="wf-tabs-row" id="reportsTabsBar">
        <button class="wf-tab active" id="tabMonthly" onclick="switchReportTab('monthly')" data-i18n="tab_monthly">${monthlyText}</button>
        <button class="wf-tab" id="tabYearly"  onclick="switchReportTab('yearly')" data-i18n="tab_yearly">${yearlyText}</button>
        <button class="wf-tab" id="tabCustom"  onclick="switchReportTab('custom')" data-i18n="tab_custom_range">${customText}</button>
      </div>
    </div>

    <div id="ctrlMonthly" class="report-controls mb-4">
      <select class="form-select" id="rYear" style="width:auto" onchange="handleYearChange(this.value)">
        ${yearOpts(currentReportYear)}
      </select>
      <select class="form-select" id="rMonth" style="width:auto" onchange="loadReportData()">
        ${monthOpts(month)}

      </select>
      <button class="btn-primary-custom" onclick="generatePDF('monthly')">
        <i class="bi bi-file-earmark-pdf"></i> <span data-i18n="generate_pdf">Generate PDF</span>
      </button>
    </div>

    <div id="ctrlYearly" class="report-controls mb-4" style="display:none">
      <select class="form-select" id="rYearOnly" style="width:auto" onchange="handleYearChange(this.value)">
        ${yearOpts(currentReportYear)}
      </select>
      <button class="btn-primary-custom" onclick="generatePDF('yearly')">
        <i class="bi bi-file-earmark-pdf"></i> <span data-i18n="generate_pdf">Generate PDF</span>
      </button>
    </div>

    <div id="ctrlCustom" class="report-controls mb-4" style="display:none">
      <input type="date" class="form-control" id="rStart" style="width:auto"
             value="${currentReportYear}-01-01" onchange="loadReportData()">
      <span style="color:var(--text-muted);padding:0 4px" data-i18n="report_to">to</span>
      <input type="date" class="form-control" id="rEnd" style="width:auto"
             value="${today.toISOString().split("T")[0]}" onchange="loadReportData()">
      <button class="btn-primary-custom" onclick="generatePDF('custom')">
        <i class="bi bi-file-earmark-pdf"></i> <span data-i18n="generate_pdf">Generate PDF</span>
      </button>
    </div>

    <div class="row g-3 mb-4" id="reportKPIs"></div>

    <div class="row g-3 mb-4 align-items-stretch">
      <div class="col-lg-8">
        <div class="chart-container h-100">
          <div class="chart-title" data-i18n="income_vs_expenses">Income vs Expenses</div>
          <canvas id="chartIncomeExpense" height="110"></canvas>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="chart-container h-100">
          <div class="chart-title" data-i18n="expense_categories">Expense Categories</div>
          <canvas id="chartCategories" height="220"></canvas>
        </div>
      </div>
    </div>

    <div class="chart-container mb-4">
      <div class="chart-title" id="trendTitle">${t("monthly_expense_trend", "Monthly Expense Trend")} (${currentReportYear})</div>
      <canvas id="chartTrend" height="80"></canvas>
    </div>`;

  applyTranslations();
  if (typeof window.initTabsWithMoreMenu === 'function') {
    window.initTabsWithMoreMenu({
      containerId: 'reportsTabsBar',
      visibleCount: 4,
      moreLabel: t('financial_advisor_tab_more', 'More'),
      tabSelector: '.wf-tab',
      activeClass: 'active',
    });
  }
  await loadReportData();
}

function switchReportTab(tab) {
  _currentTab = tab;
  ["monthly", "yearly", "custom"].forEach((t) => {
    const ctrlEl = document.getElementById(
      `ctrl${t.charAt(0).toUpperCase() + t.slice(1)}`,
    );
    const tabEl = document.getElementById(
      `tab${t.charAt(0).toUpperCase() + t.slice(1)}`,
    );
    if (ctrlEl) ctrlEl.style.display = t === tab ? "flex" : "none";
    if (tabEl) tabEl.classList.toggle("active", t === tab);
  });
  
  const title = document.querySelector('.reports-page-title');
  if (title) {
    if (tab === 'monthly') { title.setAttribute('data-i18n', 'tab_monthly'); title.textContent = t('tab_monthly', 'Monthly'); }
    else if (tab === 'yearly') { title.setAttribute('data-i18n', 'tab_yearly'); title.textContent = t('tab_yearly', 'Yearly'); }
    else if (tab === 'custom') { title.setAttribute('data-i18n', 'tab_custom_range'); title.textContent = t('tab_custom_range', 'Custom Range'); }
  }
  
  loadReportData();
}

async function loadReportData() {
  const tab = _currentTab;
  let year = currentReportYear;
  const month = parseInt(document.getElementById("rMonth")?.value || 0);
  const startVal = document.getElementById("rStart")?.value || "";
  const endVal = document.getElementById("rEnd")?.value || "";

  const MONTH_NAMES_I18N = REPORT_MONTH_I18N_KEYS.map((key) => t(key));
  const MONTH_NAMES_EN = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
  ];

  const trendTitleEl = document.getElementById("trendTitle");
  if (trendTitleEl) {
    if (tab === "monthly" && month > 0) {
      trendTitleEl.innerText = `${t("monthly_expense_trend")} (${MONTH_NAMES_I18N[month - 1]} - ${year})`;
    } else if (tab === "yearly") {
      trendTitleEl.innerText = `${t("monthly_expense_trend")} (${year})`;
    } else {
      trendTitleEl.innerText = `${t("monthly_expense_trend")} (${startVal} ${t("report_to")} ${endVal})`;
    }
  }

  let expUrl = "";
  let sumUrl = "";

  if (tab === "monthly") {
    expUrl = `/api/expenses/?year=${year}&month=${month}`;
    sumUrl = `/api/expenses/summary/?year=${year}&month=${month}`;
  } else if (tab === "yearly") {
    expUrl = `/api/expenses/?year=${year}`;
    sumUrl = `/api/expenses/summary/?year=${year}`;
  } else {
    if (startVal) {
      year = new Date(startVal).getFullYear();
    }
    expUrl = `/api/expenses/?start=${startVal}&end=${endVal}`;
    sumUrl = `/api/expenses/summary/?year=${year}`;
  }

  const [expRes, sumRes] = await Promise.all([
    fetch(expUrl),
    fetch(sumUrl),
  ]);

  const expData = await expRes.json();
  const sumData = await sumRes.json();

  // FIX: Separate custom dashboard metrics tracking completely from backend calculations
  let totalExp = 0;
  let byCat = [];
  let trend = [];

  if (tab === "custom") {
    // 1. Calculate explicit expense values strictly from filtered date rows
    const rawExpenses = expData.entries || [];
    if (Array.isArray(rawExpenses)) {
      totalExp = rawExpenses.reduce(
        (sum, item) => sum + (parseFloat(item.amount) || 0),
        0,
      );
      //console.log('TOTAL EXPENSES CALCULATED', totalExp);
      // 2. Compute category groupings dynamically on frontend
      const catMap = {};
      rawExpenses.forEach((item) => {
        if (!item.category_name) return;

        const key = item.category_name;

        if (!catMap[key]) {
          catMap[key] = {
            name: item.category_name,
            icon: item.category_icon || "📦",
            color: item.category_color || "#1a6ef5",
            total: 0,
          };
        }

        catMap[key].total += parseFloat(item.amount || 0);
      });
      byCat = Object.values(catMap);

      // 3. Populate matching trend graphs
      const monthlyTrendMap = Array(12)
        .fill(0)
        .map((_, i) => ({ month: i + 1, total: 0 }));
      rawExpenses.forEach((item) => {
        if (item.date) {
          const itemMonth = new Date(item.date).getMonth(); // 0-11
          if (itemMonth >= 0 && itemMonth < 12) {
            monthlyTrendMap[itemMonth].total += parseFloat(item.amount) || 0;
          }
        }
      });
      trend = monthlyTrendMap;
    }
  } else {
    // Fall back safely to native endpoints for monthly and yearly metrics
    totalExp = expData.total || 0;
    byCat = sumData.by_category || [];
    trend = sumData.monthly_trend || [];
  }

  let manualIncome = parseFloat(localStorage.getItem("manualIncome") || 0);
  const incomeSummary = sumData.income_summary || {};
  let totalInc = parseFloat(incomeSummary.total_income || 0) + manualIncome;
  const netSav = totalInc - totalExp;
  const savRate = totalInc > 0 ? (netSav / totalInc) * 100 : 0;

  // KPI Rendering
  const kpiEl = document.getElementById("reportKPIs");
  if (kpiEl) {
    kpiEl.innerHTML = `
        <div class="col-6 col-lg-3" onclick="editIncome()" style="cursor:pointer">
            <div class="kpi-card h-100">
                <div class="kpi-label" data-i18n="total_income_edit">${t("total_income_edit", "Total Income (edit)")}</div>
                <div class="kpi-value">${fmt(totalInc)}</div>
            </div>
        </div>
      ${repKPI("total_expenses", fmt(totalExp), "bi-cart-x", "var(--accent-red)", "var(--accent-red-bg)")}
      ${repKPI("net_savings", fmt(netSav), "bi-piggy-bank", netSav >= 0 ? "var(--accent-green)" : "var(--accent-red)", netSav >= 0 ? "var(--accent-green-bg)" : "var(--accent-red-bg)")}
      ${repKPI("savings_rate", savRate.toFixed(1) + "%", "bi-percent", "var(--accent-yellow)", "var(--accent-yellow-bg)")}`;
  }

  drawIncomeExpenseChart(totalInc, totalExp);
  drawCategoryChart(byCat);
  drawTrendChart(trend);
  applyTranslations();
}

function editIncome() {
  const current = localStorage.getItem("manualIncome") || 0;
  const val = prompt(t("enter_additional_manual_income"), current);
  if (val !== null && !isNaN(val)) {
    localStorage.setItem("manualIncome", val);
    loadReportData();
  }
}


// ════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.editIncome = editIncome;
window.switchReportTab = switchReportTab;
window.switchTab = switchReportTab;
window.loadReportData = loadReportData;
window.generatePDF = generatePDF;
window.renderReports = renderReports;
window.handleYearChange = handleYearChange;
window.renderYearlyReport = renderYearlyReport;

function handleYearChange(selectedYear) {
  if (!selectedYear) return;
  currentReportYear = parseInt(selectedYear);

  const rYear = document.getElementById("rYear");
  const rYearOnly = document.getElementById("rYearOnly");
  if (rYear) rYear.value = currentReportYear;
  if (rYearOnly) rYearOnly.value = currentReportYear;

  loadReportData();
}
