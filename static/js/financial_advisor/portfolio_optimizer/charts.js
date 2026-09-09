"use strict";
// Portfolio Optimizer chart rendering
// This file is part of the financial_advisor module. Do not edit directly.

function _drawPortfolioAllocationChart(payload) {
  const canvasId = "portfolioAllocationChart";
  const canvas = document.getElementById(canvasId);
  if (!canvas || !window.Chart) return;

  _destroyChart(canvasId);

  const direction = _pageDirection();
  const isRTL = direction === "rtl";
  const primaryText = _themeColor("--text-primary", "#e8f0fe");
  const gridColor = "rgba(123, 147, 201, 0.16)";

  const labels = (payload?.allocation_chart?.labels || []).map((labelKey) => t(labelKey, labelKey));
  const values = payload?.allocation_chart?.values || [];

  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          borderColor: "rgba(13, 21, 48, 0.9)",
          borderWidth: 2,
          backgroundColor: [
            "#50d890",
            "#4f8ff7",
            "#8c7cf0",
            "#f3c846",
            "#3ddc84",
            "#5da9ff",
            "#b178ff",
          ],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: {
          position: "right",
          rtl: isRTL,
          reverse: isRTL,
          labels: {
            color: primaryText,
            boxWidth: 12,
            usePointStyle: true,
            pointStyle: "circle",
            textDirection: direction,
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
              const total = values.reduce((sum, x) => sum + Number(x || 0), 0);
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
