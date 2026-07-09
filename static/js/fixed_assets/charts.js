"use strict";
// Fixed assets chart drawing utilities
// This file is part of the fixed_assets module. Do not edit directly.

function renderFixedAssetsKpi(iconClass, labelKey, value) {
  return `
    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:18px 20px;">
      <div style="font-size:20px;margin-bottom:6px;color:var(--accent-primary);"><i class="${iconClass}"></i></div>
      <div style="font-size:11px;font-weight:700;letter-spacing:.05em;color:var(--text-secondary);text-transform:uppercase;margin-bottom:6px;" data-i18n="${labelKey}"></div>
      <div style="font-size:22px;font-weight:800;color:var(--text-primary);">${value}</div>
    </div>
  `;
}

function renderFixedAssetsPlaceholder(titleKey, descKey) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  container.innerHTML = `
    <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
        <div class="display-5 mb-3">🧭</div>
        <h4 class="mt-2 fixed-assets-empty-title" data-i18n="${titleKey}"></h4>
        <p class="small mb-0" style="color:var(--text-secondary);" data-i18n="${descKey}"></p>
    </div>
  `;
  applyTranslations();
}

function getFixedAssetsDashboardMetrics(assets) {
  const totalAssets = assets.length;
  const totalPurchaseValue = assets.reduce(
    (sum, asset) => sum + (parseFloat(asset.purchase_price) || 0),
    0,
  );
  const currentMarketValue = assets.reduce(
    (sum, asset) => sum + (parseFloat(asset.current_market_value) || 0),
    0,
  );
  const totalGain = currentMarketValue - totalPurchaseValue;

  const appreciationValues = assets
    .filter((asset) => (parseFloat(asset.purchase_price) || 0) > 0)
    .map((asset) => {
      const purchase = parseFloat(asset.purchase_price) || 0;
      const current = parseFloat(asset.current_market_value) || 0;
      return ((current - purchase) / purchase) * 100;
    });

  const averageAppreciation = appreciationValues.length
    ? appreciationValues.reduce((sum, value) => sum + value, 0) /
      appreciationValues.length
    : 0;

  const allocation = assets
    .map((asset) => ({
      label: asset.name || "—",
      value: parseFloat(asset.current_market_value) || 0,
    }))
    .filter((item) => item.value > 0);

  const typeMap = new Map();
  assets.forEach((asset) => {
    const key = asset.asset_type || t("type_other");
    typeMap.set(key, (typeMap.get(key) || 0) + 1);
  });

  const portfolioStatusMap = new Map();
  assets.forEach((asset) => {
    const isSold = asset.status === "Sold";
    const label = isSold ? t("sold_assets") : t("owned_assets");
    const value = isSold
      ? parseFloat(asset.sale?.net_sale_amount) || parseFloat(asset.sale?.sale_price) || 0
      : parseFloat(asset.current_market_value) || 0;
    portfolioStatusMap.set(label, (portfolioStatusMap.get(label) || 0) + value);
  });

  const growthSeries = buildFixedAssetsGrowthSeries(assets);

  return {
    totalAssets,
    totalPurchaseValue,
    currentMarketValue,
    totalGain,
    averageAppreciation,
    allocation,
    typeDistribution: Array.from(typeMap.entries()).map(([label, value]) => ({
      label,
      value,
    })),
    portfolioDistribution: Array.from(portfolioStatusMap.entries())
      .map(([label, value]) => ({ label, value }))
      .filter((item) => item.value > 0),
    growthSeries,
  };
}

function buildFixedAssetsGrowthSeries(assets) {
  const sortedAssets = [...assets].sort((a, b) => {
    const dateA = new Date(a.purchase_date || 0).getTime();
    const dateB = new Date(b.purchase_date || 0).getTime();
    return dateA - dateB;
  });

  let cumulativePurchase = 0;
  let cumulativeCurrent = 0;

  const labels = [];
  const purchaseValues = [];
  const currentValues = [];

  sortedAssets.forEach((asset) => {
    cumulativePurchase += parseFloat(asset.purchase_price) || 0;
    cumulativeCurrent += parseFloat(asset.current_market_value) || 0;

    labels.push(asset.purchase_date || asset.name || "—");
    purchaseValues.push(cumulativePurchase);
    currentValues.push(cumulativeCurrent);
  });

  return {
    labels,
    purchaseValues,
    currentValues,
  };
}

function drawFixedAssetsDashboardCharts(metrics) {
  drawFixedAssetsDoughnutChart(
    "fixedAssetsAllocationChart",
    metrics.allocation.map((item) => item.label),
    metrics.allocation.map((item) => item.value),
  );
  drawFixedAssetsDoughnutChart(
    "fixedAssetsTypeChart",
    metrics.typeDistribution.map((item) => item.label),
    metrics.typeDistribution.map((item) => item.value),
  );
  drawFixedAssetsDoughnutChart(
    "fixedAssetsPortfolioChart",
    metrics.portfolioDistribution.map((item) => item.label),
    metrics.portfolioDistribution.map((item) => item.value),
  );
  drawFixedAssetsLineChart(
    "fixedAssetsGrowthChart",
    metrics.growthSeries.labels,
    [
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
    ],
  );
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
        datasets: [{
          data,
          backgroundColor: ["#1a6ef5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"].slice(0, data.length),
          borderWidth: 0,
        }],
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
    });
  }, 50);
}

function _noDataFixedAssets(cols) {
  return `<tr><td colspan="${cols}" style="text-align:center;padding:28px;color:var(--text-secondary)" data-i18n="no_data">${t("no_data", "No data available")}</td></tr>`;
}

