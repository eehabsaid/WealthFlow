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
            "rgba(16, 185, 129, 0.8)",
            "rgba(244, 63, 94, 0.8)",
            "rgba(99, 102, 241, 0.8)",
          ],
          borderColor: ["#10b981", "#f43f5e", "#6366f1"],
          borderWidth: 1.5,
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
          padding: 10,
          cornerRadius: 8,
        },
      },
      scales: {
        x: { ticks: { color: "#94a3b8", font: { family: "Inter, sans-serif" } }, grid: { display: false } },
        y: {
          ticks: { color: "#94a3b8", font: { family: "Inter, sans-serif" }, callback: (v) => fmt(v) },
          grid: { color: "rgba(148, 163, 184, 0.12)" },
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
          borderColor: "#f43f5e",
          backgroundColor: "rgba(244, 63, 94, 0.08)",
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: "#f43f5e",
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#94a3b8", font: { family: "Inter, sans-serif" } } },
        tooltip: {
          callbacks: { label: (ctx) => " " + fmt(ctx.parsed.y) + " EGP" },
          padding: 10,
          cornerRadius: 8,
        },
      },
      scales: {
        x: { ticks: { color: "#94a3b8", font: { family: "Inter, sans-serif" } }, grid: { display: false } },
        y: {
          ticks: { color: "#94a3b8", font: { family: "Inter, sans-serif" }, callback: (v) => fmt(v) },
          grid: { color: "rgba(148, 163, 184, 0.12)" },
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