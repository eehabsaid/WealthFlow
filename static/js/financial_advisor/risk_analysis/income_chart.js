"use strict";
// Income stability chart drawing.

window.RA = window.RA || {};

window.RA.drawIncomeStabilityChart = function(payload) {
  if (typeof _destroyChart === "function") _destroyChart("incomeStabilityChart");
  const sources = payload?.income_stability?.sources || [];
  if (sources.length === 0) return;

  const canvas = document.getElementById("incomeStabilityChart");
  if (!canvas || !window.Chart) return;

  const labels = sources.map((s) => (typeof t === "function" ? t(s.label_key, s.id) : s.id));
  const data = sources.map((s) => s.percentage);
  const bgColors = sources.map((s) =>
    s.id === "salary" ? "rgba(52, 199, 89, 0.8)" : "rgba(0, 122, 255, 0.8)"
  );
  const borderColors = sources.map((s) =>
    s.id === "salary" ? "rgb(52, 199, 89)" : "rgb(0, 122, 255)"
  );
  const isRtl = typeof _pageDirection === "function" ? _pageDirection() === "rtl" : false;

  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: bgColors,
          borderColor: borderColors,
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      rtl: isRtl,
      cutout: "75%",
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor:
            typeof _themeColor === "function" ? _themeColor("--bg-secondary", "#fff") : "#fff",
          titleColor:
            typeof _themeColor === "function" ? _themeColor("--text-primary", "#333") : "#333",
          bodyColor:
            typeof _themeColor === "function" ? _themeColor("--text-primary", "#333") : "#333",
          borderColor:
            typeof _themeColor === "function"
              ? _themeColor("--border-color", "#e2e8f0")
              : "#e2e8f0",
          borderWidth: 1,
          callbacks: {
            label: function (context) {
              return context.formattedValue + "%";
            },
          },
        },
      },
    },
  });
}

