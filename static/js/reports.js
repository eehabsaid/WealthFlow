/* ============================================================
   reports.js — Reports Page (Monthly / Yearly / Custom)
   ============================================================ */
'use strict';

var currentReportYear = 2026;
let _currentTab = 'monthly';
const REPORT_MONTH_I18N_KEYS = ['month_january','month_february','month_march','month_april','month_may','month_june',
  'month_july','month_august','month_september','month_october','month_november','month_december'];

async function renderReports() {
  const mc = document.getElementById('main-content');
  const today = new Date();

  currentReportYear = today.getFullYear();
  const month = today.getMonth() + 1;
  _currentTab = 'monthly';

  mc.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title" data-i18n="reports_title">📊 Reports</div>
        <div class="page-subtitle" data-i18n="reports_income_expenses_analysis">Income vs Expenses analysis and PDF export</div>
      </div>
    </div>

    <div class="settings-tabs mb-4">
      <button class="settings-tab active" id="tabMonthly" onclick="switchReportTab('monthly')" data-i18n="tab_monthly">Monthly</button>
      <button class="settings-tab" id="tabYearly"  onclick="switchReportTab('yearly')" data-i18n="tab_yearly">Yearly</button>
      <button class="settings-tab" id="tabCustom"  onclick="switchReportTab('custom')" data-i18n="tab_custom_range">Custom Range</button>
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
             value="${today.toISOString().split('T')[0]}" onchange="loadReportData()">
      <button class="btn-primary-custom" onclick="generatePDF('custom')">
        <i class="bi bi-file-earmark-pdf"></i> <span data-i18n="generate_pdf">Generate PDF</span>
      </button>
    </div>

    <div class="row g-3 mb-4" id="reportKPIs"></div>

    <div class="row g-3 mb-4">
      <div class="col-md-8">
        <div class="chart-container">
          <div class="chart-title" data-i18n="income_vs_expenses">Income vs Expenses</div>
          <canvas id="chartIncomeExpense" height="110"></canvas>
        </div>
      </div>
      <div class="col-md-4">
        <div class="chart-container">
          <div class="chart-title" data-i18n="expense_categories">Expense Categories</div>
          <canvas id="chartCategories" height="220"></canvas>
        </div>
      </div>
    </div>

    <div class="chart-container mb-4">
      <div class="chart-title" id="trendTitle">${t('monthly_expense_trend')} (${currentReportYear})</div>
      <canvas id="chartTrend" height="80"></canvas>
    </div>`;

  applyTranslations();
  await loadReportData();
}

function handleYearChange(selectedYear) {
  if (!selectedYear) return;
  currentReportYear = parseInt(selectedYear);

  const rYear = document.getElementById('rYear');
  const rYearOnly = document.getElementById('rYearOnly');
  if (rYear) rYear.value = currentReportYear;
  if (rYearOnly) rYearOnly.value = currentReportYear;

  loadReportData();
}

function switchReportTab(tab) {
  _currentTab = tab;
  ['monthly', 'yearly', 'custom'].forEach(t => {
    const ctrlEl = document.getElementById(`ctrl${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const tabEl = document.getElementById(`tab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (ctrlEl) ctrlEl.style.display = t === tab ? 'flex' : 'none';
    if (tabEl) tabEl.classList.toggle('active', t === tab);
  });
  loadReportData();
}

async function loadReportData() {
  const tab = _currentTab;
  let year = currentReportYear;
  const month = parseInt(document.getElementById('rMonth')?.value || 0);
  const startVal = document.getElementById('rStart')?.value || '';
  const endVal = document.getElementById('rEnd')?.value || '';

  const MONTH_NAMES_I18N = REPORT_MONTH_I18N_KEYS.map(key => t(key));
  const MONTH_NAMES_EN = [
    'january', 'february', 'march', 'april', 'may', 'june', 
    'july', 'august', 'september', 'october', 'november', 'december'
  ];

const trendTitleEl = document.getElementById('trendTitle');
  if (trendTitleEl) {
    if (tab === 'monthly' && month > 0) {
      trendTitleEl.innerText = `${t('monthly_expense_trend')} (${MONTH_NAMES_I18N[month - 1]} - ${year})`;
    } else if (tab === 'yearly') {
      trendTitleEl.innerText = `${t('monthly_expense_trend')} (${year})`;
    } else {
      trendTitleEl.innerText = `${t('monthly_expense_trend')} (${startVal} ${t('report_to')} ${endVal})`;
    }
  }

  let expUrl = '';
  let sumUrl = '';

  if (tab === 'monthly') {
    expUrl = `/api/expenses/?year=${year}&month=${month}`;
    sumUrl = `/api/expenses/summary/?year=${year}&month=${month}`;
  } else if (tab === 'yearly') {
    expUrl = `/api/expenses/?year=${year}`;
    sumUrl = `/api/expenses/summary/?year=${year}`;
  } else {
    if (startVal) { year = new Date(startVal).getFullYear(); }
    expUrl = `/api/expenses/?start=${startVal}&end=${endVal}`;
    sumUrl = `/api/expenses/summary/?year=${year}`;
  }

  const [expRes, bankRes, sumRes] = await Promise.all([
    fetch(expUrl),
    fetch('/api/bank-certificates/'),
    fetch(sumUrl),
  ]);

  const expData = await expRes.json();
  const bankData = await bankRes.json();
  const sumData = await sumRes.json();

  // FIX: Separate custom dashboard metrics tracking completely from backend calculations
  let totalExp = 0;
  let byCat = [];
  let trend = [];

  if (tab === 'custom') {
    // 1. Calculate explicit expense values strictly from filtered date rows
    const rawExpenses = expData.entries || [];
    if (Array.isArray(rawExpenses)) {
      totalExp = rawExpenses.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
      //console.log('TOTAL EXPENSES CALCULATED', totalExp);
      // 2. Compute category groupings dynamically on frontend
      const catMap = {};
      rawExpenses.forEach(item => {

        if (!item.category_name) return;

        const key = item.category_name;

        if (!catMap[key]) {

          catMap[key] = {
            name: item.category_name,
            icon: item.category_icon || '📦',
            color: item.category_color || '#1a6ef5',
            total: 0
          };
        }

        catMap[key].total += parseFloat(item.amount || 0);

      });
      byCat = Object.values(catMap);

      // 3. Populate matching trend graphs
      const monthlyTrendMap = Array(12).fill(0).map((_, i) => ({ month: i + 1, total: 0 }));
      rawExpenses.forEach(item => {
        if (item.date) {
          const itemMonth = new Date(item.date).getMonth(); // 0-11
          if (itemMonth >= 0 && itemMonth < 12) {
            monthlyTrendMap[itemMonth].total += (parseFloat(item.amount) || 0);
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

  // Certificate Interest Parsers
  let totalInterest = 0;
  (bankData.certificates || []).forEach(c => {
    totalInterest += parseFloat(c.interest_value || 0);
  });

  // Dynamic Salary Engine
let totalSalary = 0;
  if (tab === 'monthly') {
    let prevMonth = month - 1;
    let prevYear = year;
    if (prevMonth === 0) { prevMonth = 12; prevYear -= 1; }

    const sRes = await fetch(`/api/salary/?year=${prevYear}`);
    const sData = await sRes.json();
    totalSalary = (sData.entries || [])
      .filter(e => parseInt(e.year) === prevYear && e.month.toLowerCase() === MONTH_NAMES_EN[prevMonth - 1])
      .reduce((s, e) => s + (parseFloat(e.paid) || 0), 0);

  } else if (tab === 'yearly') {
    const sRes = await fetch(`/api/salary/?year=${year}`);
    const sData = await sRes.json();
    totalSalary = (sData.entries || []).reduce((s, e) => s + (parseFloat(e.paid) || 0), 0);

  } else if (tab === 'custom' && startVal && endVal) {
    const startDateObj = new Date(startVal);
    const endDateObj = new Date(endVal);

    let combinedEntries = [];
    for (let y = startDateObj.getFullYear(); y <= endDateObj.getFullYear(); y++) {
      try {
        const sRes = await fetch(`/api/salary/?year=${y}`);
        const sData = await sRes.json();
        if (sData.entries) combinedEntries = combinedEntries.concat(sData.entries);
      } catch (err) { console.error(err); }
    }

    totalSalary = combinedEntries
      .filter(e => {
        const mIdx = MONTH_NAMES_EN.findIndex(m => m === e.month.toLowerCase());
        if (mIdx === -1) return false;
        const entryDate = new Date(parseInt(e.year), mIdx, 1);
        const compStart = new Date(startDateObj.getFullYear(), startDateObj.getMonth(), 1);
        const compEnd = new Date(endDateObj.getFullYear(), endDateObj.getMonth(), 1);
        return entryDate >= compStart && entryDate <= compEnd;
      })
      .reduce((s, e) => s + (parseFloat(e.paid) || 0), 0);
  }

  let manualIncome = parseFloat(localStorage.getItem('manualIncome') || 0);
  let totalInc = totalSalary + totalInterest + manualIncome;
  const netSav = totalInc - totalExp;
  const savRate = totalInc > 0 ? (netSav / totalInc * 100) : 0;

// KPI Rendering
  const kpiEl = document.getElementById('reportKPIs');
  if (kpiEl) {
    kpiEl.innerHTML = `
        <div class="col-6 col-md-3" onclick="editIncome()" style="cursor:pointer">
            <div class="card h-100 kpi-card"> 
                <div class="card-body">
                    <div class="kpi-label" data-i18n="total_income_edit"></div>
                    <div class="kpi-value">${fmt(totalInc)}</div>
                </div>
            </div>
        </div>
      ${repKPI('total_expenses', fmt(totalExp), 'bi-cart-x', 'var(--accent-red)', 'var(--accent-red-bg)')}
      ${repKPI('net_savings', fmt(netSav), 'bi-piggy-bank', netSav >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', netSav >= 0 ? 'var(--accent-green-bg)' : 'var(--accent-red-bg)')}
      ${repKPI('savings_rate', savRate.toFixed(1) + '%', 'bi-percent', 'var(--accent-yellow)', 'var(--accent-yellow-bg)')}`;
  }

  drawIncomeExpenseChart(totalInc, totalExp);
  drawCategoryChart(byCat);
  drawTrendChart(trend);
  applyTranslations();
}

function editIncome() {
  const current = localStorage.getItem('manualIncome') || 0;
  const val = prompt(t('enter_additional_manual_income'), current);
  if (val !== null && !isNaN(val)) {
    localStorage.setItem('manualIncome', val);
    loadReportData();
  }
}

function repKPI(label, value, icon, accent, bg) {
  return `<div class="col-6 col-md-3">
    <div class="kpi-card" style="--kpi-accent:${accent};--kpi-bg:${bg}">
      <div class="kpi-icon"><i class="bi ${icon}"></i></div>
      <div class="kpi-label" data-i18n="${label}"></div>
      <div class="kpi-value">${value}</div>
    </div></div>`;
}

function drawIncomeExpenseChart(income, expense) {
  const canvas = document.getElementById('chartIncomeExpense');
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: ['Income', 'Expenses', 'Net Savings'],
      datasets: [{
        data: [income, expense, Math.max(0, income - expense)],
        backgroundColor: ['rgba(0,214,143,0.7)', 'rgba(255,77,109,0.7)', 'rgba(26,110,245,0.7)'],
        borderColor: ['#00d68f', '#ff4d6d', '#1a6ef5'],
        borderWidth: 1, borderRadius: 8,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ' ' + fmt(ctx.parsed.y) + ' EGP' } }
      },
      scales: {
        x: { ticks: { color: '#7b97cc' }, grid: { color: '#1a346022' } },
        y: { ticks: { color: '#7b97cc', callback: v => fmt(v) }, grid: { color: '#1a346022' } }
      }
    }
  });
}

function drawCategoryChart(byCat) {
  const canvas = document.getElementById('chartCategories');
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  if (!byCat.length) return;
  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: byCat.map(c => c.icon + ' ' + c.name),
      datasets: [{
        data: byCat.map(c => c.total),
        backgroundColor: byCat.map(c => c.color + 'cc'),
        borderColor: byCat.map(c => c.color),
        borderWidth: 1,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#7b97cc', font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => ' ' + fmt(ctx.parsed) + ' EGP' } }
      }
    }
  });
}

function drawTrendChart(monthly) {
  const canvas = document.getElementById('chartTrend');
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  const MONTH_ABBR = REPORT_MONTH_I18N_KEYS.map(key => t(key));
  new Chart(canvas, {
    type: 'line',
    data: {
      labels: MONTH_ABBR,
      datasets: [{
        label: 'Expenses',
        data: monthly.map(m => m.total),
        borderColor: '#ff4d6d',
        backgroundColor: 'rgba(255,77,109,0.1)',
        fill: true, tension: 0.4, pointRadius: 4,
        pointBackgroundColor: '#ff4d6d',
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#7b97cc' } },
        tooltip: { callbacks: { label: ctx => ' ' + fmt(ctx.parsed.y) + ' EGP' } }
      },
      scales: {
        x: { ticks: { color: '#7b97cc' }, grid: { color: '#1a346022' } },
        y: { ticks: { color: '#7b97cc', callback: v => fmt(v) }, grid: { color: '#1a346022' } }
      }
    }
  });
}

async function generatePDF(type) {
  let year = parseInt(document.getElementById('rYear')?.value || document.getElementById('rYearOnly')?.value || new Date().getFullYear());
  let month = parseInt(document.getElementById('rMonth')?.value || new Date().getMonth() + 1);
  const start = document.getElementById('rStart')?.value || '';
  const end = document.getElementById('rEnd')?.value || '';

  if (type === 'custom') {
    if (start) { year = new Date(start).getFullYear(); }
    month = 1;
  }

  const body = { 
    type, year, month, 
    start_date: start, end_date: end, 
    lang: currentLang() 
  };
  
  const btn = event?.target;
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner-border spinner-border-sm"></div> Generating…'; }

  try {
    const res = await fetch('/api/reports/generate/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    
    if (!res.ok) {
      const err = await res.json();
      showToast('Error: ' + (err.error || 'Unknown error'), 'error');
      return;
    }
    
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const cd = res.headers.get('Content-Disposition') || '';
    const fnMatch = cd.match(/filename="(.+)"/);
    a.download = fnMatch ? fnMatch[1] : 'report.pdf';
    a.href = url;
    a.click();
    URL.revokeObjectURL(url);
    showToast('PDF downloaded ✓', 'success');
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-file-earmark-pdf"></i> Generate PDF'; }
  }
  applyTranslations();
}

function yearOpts(current) {
  let o = '';
  for (let y = current > 2026 ? current : 2026; y >= 2020; y--)
    o += `<option value="${y}" ${y === current ? 'selected' : ''}>${y}</option>`;
  return o;
}

function monthOpts(selectedMonth) {
    return MONTHS_NAMES.map((m, i) => {
        const monthValue = i + 1;
        const isSelected = monthValue === selectedMonth ? 'selected' : '';
        const i18nKey = MONTH_I18N_KEYS[i];
        
        return `<option value="${monthValue}" ${isSelected} data-i18n="${i18nKey}">${m}</option>`;
    }).join('');
}

function renderYearlyReport() { switchReportTab('yearly'); }

// Standard Window Object Mappings
window.editIncome = editIncome;
window.switchReportTab = switchReportTab;
window.switchTab = switchReportTab;
window.loadReportData = loadReportData;
window.generatePDF = generatePDF;
window.renderReports = renderReports;
window.handleYearChange = handleYearChange;
window.renderYearlyReport = renderYearlyReport;
