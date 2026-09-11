"use strict";
// Fixed assets chart drawing utilities
// This file is part of the fixed_assets module. Do not edit directly.

function drawFixedAssetsDashboardCharts(metrics) {
  drawFixedAssetsDoughnutChart(
    "fixedAssetsAllocationChart",
    metrics.allocation.map((item) => item.label),
    metrics.allocation.map((item) => item.value)
  );
  drawFixedAssetsDoughnutChart(
    "fixedAssetsTypeChart",
    metrics.typeDistribution.map((item) => item.label),
    metrics.typeDistribution.map((item) => item.value)
  );
  drawFixedAssetsDoughnutChart(
    "fixedAssetsPortfolioChart",
    metrics.portfolioDistribution.map((item) => item.label),
    metrics.portfolioDistribution.map((item) => item.value)
  );
  drawFixedAssetsLineChart("fixedAssetsGrowthChart", metrics.growthSeries.labels, [
    {
      label: t("total_purchase_value"),
      data: metrics.growthSeries.purchaseValues,
      color: "#1a6ef5",
    },
    {
      label: t("current_market_value"),
      data: metrics.growthSeries.currentValues,
      color: "#10b981",
    },
  ]);
}

function getFixedAssetsChartTheme() {
  const styles = getComputedStyle(document.documentElement);
  return {
    textPrimary: styles.getPropertyValue("--text-primary").trim() || "#e2e8f0",
    textSecondary: styles.getPropertyValue("--text-secondary").trim() || "#94a3b8",
    borderColor: styles.getPropertyValue("--border-color").trim() || "#1e293b",
  };
}

function drawFixedAssetsDoughnutChart(canvasId, labels, data) {
  setTimeout(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;
    const chartTheme = getFixedAssetsChartTheme();
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: [
              "#1a6ef5",
              "#10b981",
              "#f59e0b",
              "#ef4444",
              "#8b5cf6",
              "#06b6d4",
              "#ec4899",
            ].slice(0, data.length),
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: {
              color: chartTheme.textSecondary,
              boxWidth: 12,
              padding: 12,
            },
          },
        },
      },
    });
  }, 50);
}

function drawFixedAssetsBarChart(canvasId, labels, datasets) {
  setTimeout(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;
    const chartTheme = getFixedAssetsChartTheme();
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: datasets.map((dataset) => ({
          label: dataset.label,
          data: dataset.data,
          backgroundColor: `${dataset.color}cc`,
          borderColor: dataset.color,
          borderWidth: 1,
          borderRadius: 4,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: chartTheme.textSecondary,
              boxWidth: 12,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: chartTheme.textSecondary },
            grid: { color: chartTheme.borderColor },
          },
          y: {
            ticks: { color: chartTheme.textSecondary },
            grid: { color: chartTheme.borderColor },
          },
        },
      },
    });
  }, 50);
}

function drawFixedAssetsLineChart(canvasId, labels, datasets) {
  setTimeout(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;
    const chartTheme = getFixedAssetsChartTheme();
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: datasets.map((dataset) => ({
          label: dataset.label,
          data: dataset.data,
          borderColor: dataset.color,
          backgroundColor: `${dataset.color}33`,
          borderWidth: 2,
          fill: false,
          tension: 0.25,
          pointRadius: 3,
          pointBackgroundColor: dataset.color,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: chartTheme.textSecondary,
              boxWidth: 12,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: chartTheme.textSecondary },
            grid: { color: chartTheme.borderColor },
          },
          y: {
            ticks: { color: chartTheme.textSecondary },
            grid: { color: chartTheme.borderColor },
          },
        },
      },
      plugins: window.SharedCrosshairPlugin ? [window.SharedCrosshairPlugin] : [],
    });
  }, 50);
}

