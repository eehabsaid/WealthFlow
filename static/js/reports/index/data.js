"use strict";
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

  const [expRes, sumRes] = await Promise.all([fetch(expUrl), fetch(sumUrl)]);

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
      totalExp = rawExpenses.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
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
