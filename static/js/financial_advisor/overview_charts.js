"use strict";

function _drawOverviewCharts(payload) {
  if (!window.Chart) return;

  // 1. Cash Flow Sparkline
  const cfCanvasId = "overviewCashFlowChart";
  const cfCanvas = document.getElementById(cfCanvasId);
  if (cfCanvas) {
    _destroyChart(cfCanvasId);
    const cfTimeline = payload.cash_flow.sparkline || [];
    const labels = cfTimeline.map((p) => p.month);
    const values = cfTimeline.map((p) => p.balance);

    new Chart(cfCanvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            data: values,
            borderColor: "var(--accent-primary)",
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.45,
            fill: true,
            backgroundColor: "rgba(26, 110, 245, 0.06)",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: { x: { display: false }, y: { display: false } },
      },
    });
  }

  // 2. Wealth Growth Sparkline
  const wgCanvasId = "overviewWealthGrowthChart";
  const wgCanvas = document.getElementById(wgCanvasId);
  if (wgCanvas) {
    _destroyChart(wgCanvasId);
    const wgTimeline = payload.wealth_growth.sparkline || [];
    const labels = wgTimeline.map((p) => p.month);
    const values = wgTimeline.map((p) => p.balance);

    new Chart(wgCanvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            data: values,
            borderColor: "#8c7cf0",
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.45,
            fill: true,
            backgroundColor: "rgba(140, 124, 240, 0.06)",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: { x: { display: false }, y: { display: false } },
      },
    });
  }

  // 3. Portfolio Donut
  const pfCanvasId = "overviewPortfolioDonutChart";
  const pfCanvas = document.getElementById(pfCanvasId);
  if (pfCanvas) {
    _destroyChart(pfCanvasId);
    const chartData = payload.portfolio.allocation_chart || {};
    const labels = (chartData.labels || []).map((labelKey) => t(labelKey, labelKey));
    const values = chartData.values || [];

    new Chart(pfCanvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: values,
            borderColor: "var(--bg-secondary)",
            borderWidth: 2.5,
            backgroundColor: [
              "var(--accent-green)",
              "#8c7cf0",
              "var(--accent-yellow)",
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
        cutout: "75%",
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                const label = context.label || "";
                const val = context.parsed || 0;
                return ` ${label}: ${_money(val)}`;
              },
            },
          },
        },
      },
    });
  }
}

window._drawOverviewCharts = _drawOverviewCharts;
