'use strict';

function drawIncomeExpenseChart(income, expense) {
  const canvas = document.getElementById("chartIncomeExpense");
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: ["Income", "Expenses", "Net Savings"],
      datasets: [
        {
          data: [income, expense, Math.max(0, income - expense)],
          backgroundColor: [
            "rgba(0,214,143,0.7)",
            "rgba(255,77,109,0.7)",
            "rgba(26,110,245,0.7)",
          ],
          borderColor: ["#00d68f", "#ff4d6d", "#1a6ef5"],
          borderWidth: 1,
          borderRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: (ctx) => " " + fmt(ctx.parsed.y) + " EGP" },
        },
      },
      scales: {
        x: { ticks: { color: "#7b97cc" }, grid: { color: "#1a346022" } },
        y: {
          ticks: { color: "#7b97cc", callback: (v) => fmt(v) },
          grid: { color: "#1a346022" },
        },
      },
    },
  });
}

function drawCategoryChart(byCat) {
  const canvas = document.getElementById("chartCategories");
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  if (!byCat.length) return;
  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: byCat.map((c) => c.icon + " " + c.name),
      datasets: [
        {
          data: byCat.map((c) => c.total),
          backgroundColor: byCat.map((c) => c.color + "cc"),
          borderColor: byCat.map((c) => c.color),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#7b97cc", font: { size: 11 } },
        },
        tooltip: {
          callbacks: { label: (ctx) => " " + fmt(ctx.parsed) + " EGP" },
        },
      },
    },
  });
}

function drawTrendChart(monthly) {
  const canvas = document.getElementById("chartTrend");
  if (!canvas) return;
  const existing = Chart.getChart(canvas);
  if (existing) existing.destroy();
  const MONTH_ABBR = REPORT_MONTH_I18N_KEYS.map((key) => t(key));
  new Chart(canvas, {
    type: "line",
    data: {
      labels: MONTH_ABBR,
      datasets: [
        {
          label: "Expenses",
          data: monthly.map((m) => m.total),
          borderColor: "#ff4d6d",
          backgroundColor: "rgba(255,77,109,0.1)",
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: "#ff4d6d",
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#7b97cc" } },
        tooltip: {
          callbacks: { label: (ctx) => " " + fmt(ctx.parsed.y) + " EGP" },
        },
      },
      scales: {
        x: { ticks: { color: "#7b97cc" }, grid: { color: "#1a346022" } },
        y: {
          ticks: { color: "#7b97cc", callback: (v) => fmt(v) },
          grid: { color: "#1a346022" },
        },
      },
    },
    plugins: window.SharedCrosshairPlugin ? [window.SharedCrosshairPlugin] : [],
  });
}

// ════════════════════════════════════════════════════════════════════════════
// PDF GENERATION
// ════════════════════════════════════════════════════════════════════════════

function repKPI(label, value, icon, accent, bg) {
  const translatedLabel = t(label, label.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()));
  return `<div class="col-6 col-lg-3">
    <div class="kpi-card h-100" style="--kpi-accent:${accent};--kpi-bg:${bg}">
      <div class="kpi-icon"><i class="bi ${icon}"></i></div>
      <div class="kpi-label" data-i18n="${label}">${translatedLabel}</div>
      <div class="kpi-value">${value}</div>
    </div></div>`;
}