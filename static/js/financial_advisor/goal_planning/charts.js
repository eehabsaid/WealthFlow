"use strict";
// Goal Planning chart rendering
// This file is part of the financial_advisor module. Do not edit directly.

function _drawGoalTypeChart(payload) {
  const canvas = document.getElementById("goalPlanningTypeChart");
  if (!canvas || !window.Chart) return;

  _destroyChart("goalPlanningTypeChart");

  const direction = _pageDirection();
  const isRTL = direction === "rtl";
  const primaryText = _themeColor("--text-primary", "#e8f0fe");
  const gridColor = "rgba(123, 147, 201, 0.16)";

  const items = payload?.distribution?.by_type || [];
  const labels = items.map((item) => item.label || t("goal_planning_not_available"));
  const values = items.map((item) => Number(item.value_egp || 0));

  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          borderColor: "rgba(13, 21, 48, 0.9)",
          borderWidth: 2,
          backgroundColor: ["#4f8ff7", "#50d890", "#f3c846", "#8c7cf0", "#ff7c95", "#5da9ff"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: {
          position: "bottom",
          rtl: isRTL,
          reverse: isRTL,
          labels: {
            color: primaryText,
            boxWidth: 8,
            usePointStyle: true,
            pointStyle: "circle",
            textDirection: direction,
            padding: 14,
            font: { size: 12, weight: "600" },
          },
        },
        tooltip: {
          rtl: isRTL,
          textDirection: direction,
          titleColor: primaryText,
          bodyColor: primaryText,
          backgroundColor: "rgba(13, 21, 48, 0.96)",
          borderColor: gridColor,
          borderWidth: 1,
          callbacks: {
            label: (ctx) => {
              const total = values.reduce((sum, value) => sum + value, 0);
              const raw = Number(ctx.raw || 0);
              const pct = total > 0 ? (raw / total) * 100 : 0;
              return `${ctx.label}: ${fmt(raw)} (${fmtpresent(pct)}%)`;
            },
          },
        },
      },
    },
  });
}
