"use strict";

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

  const reportsDesc = t(
    "reports_income_expenses_analysis",
    "Income vs Expenses analysis and PDF export"
  );
  const monthlyText = t("tab_monthly", "Monthly");
  const yearlyText = t("tab_yearly", "Yearly");
  const customText = t("tab_custom_range", "Custom Range");

  mc.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title reports-page-title" data-i18n="tab_monthly">${monthlyText}</div>
        <div class="page-subtitle" data-i18n="reports_income_expenses_analysis">${reportsDesc}</div>
      </div>
    </div>

    <div class="wf-tabs-shell mb-4">
      <div class="wf-tabs-row" id="reportsTabsBar" role="tablist">
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
  if (typeof window.initTabsWithMoreMenu === "function") {
    window.initTabsWithMoreMenu({
      containerId: "reportsTabsBar",
      visibleCount: 4,
      moreLabel: t("financial_advisor_tab_more", "More"),
      tabSelector: ".wf-tab",
      activeClass: "active",
    });
  }
  await loadReportData();
}

function switchReportTab(tab) {
  _currentTab = tab;
  ["monthly", "yearly", "custom"].forEach((t) => {
    const ctrlEl = document.getElementById(`ctrl${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const tabEl = document.getElementById(`tab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (ctrlEl) ctrlEl.style.display = t === tab ? "flex" : "none";
    if (tabEl) tabEl.classList.toggle("active", t === tab);
  });

  const title = document.querySelector(".reports-page-title");
  if (title) {
    if (tab === "monthly") {
      title.setAttribute("data-i18n", "tab_monthly");
      title.textContent = t("tab_monthly", "Monthly");
    } else if (tab === "yearly") {
      title.setAttribute("data-i18n", "tab_yearly");
      title.textContent = t("tab_yearly", "Yearly");
    } else if (tab === "custom") {
      title.setAttribute("data-i18n", "tab_custom_range");
      title.textContent = t("tab_custom_range", "Custom Range");
    }
  }

  loadReportData();
}
