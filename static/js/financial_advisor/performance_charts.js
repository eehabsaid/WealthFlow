"use strict";

function filterTimeseries(list, timeframe) {
  if (!list || !list.length) return [];
  if (timeframe === "ALL") return list;
  const countMap = { "7D": 7, "30D": 30, "90D": 90 };
  const limit = countMap[timeframe] || 30;
  return list.slice(-limit);
}

function buildPerformanceChart({ canvasId, label, timeseries, valueKey, labelKey, mainColor }) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !window.Chart) return null;

  const existingChart = Chart.getChart(canvas);
  if (existingChart) existingChart.destroy();

  const labels = timeseries.map((item) => item[labelKey] || "");
  const values = timeseries.map((item) => item[valueKey] || 0);

  const maShortSeries = timeseries.map((item) => item.ma_short || 0);
  const maLongSeries = timeseries.map((item) => item.ma_long || 0);

  const textColor = getComputedStyle(document.documentElement).getPropertyValue("--text-secondary").trim() || "#a1a1aa";

  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, mainColor.replace("1)", "0.25)"));
  gradient.addColorStop(1, mainColor.replace("1)", "0.0)"));

  return new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: label,
          data: values,
          borderColor: mainColor,
          backgroundColor: gradient,
          borderWidth: 2,
          tension: 0.3,
          fill: true,
          pointRadius: values.length > 40 ? 0 : 2,
          pointHoverRadius: 5,
        },
        {
          label: "MA Short (7D)",
          data: maShortSeries,
          borderColor: "rgba(245, 158, 11, 0.9)",
          borderWidth: 1.5,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false,
        },
        {
          label: "MA Long (30D)",
          data: maLongSeries,
          borderColor: "rgba(6, 182, 212, 0.9)",
          borderWidth: 1.5,
          borderDash: [3, 3],
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          padding: 10,
          backgroundColor: "rgba(15, 23, 42, 0.9)",
          titleColor: "#f8fafc",
          bodyColor: "#f8fafc",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          callbacks: {
            label: function (context) {
              let val = context.parsed.y;
              return `${context.dataset.label}: ${typeof fmtpresent === 'function' ? fmtpresent(val) : val.toLocaleString()}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: {
            color: "rgba(255,255,255,0.05)",
          },
          ticks: {
            color: textColor,
            maxTicksLimit: 8,
            font: { size: 10 },
          },
        },
        y: {
          grid: {
            color: "rgba(255,255,255,0.05)",
          },
          ticks: {
            color: textColor,
            font: { size: 10 },
            callback: function (val) {
              return typeof fmtpresent === 'function' ? fmtpresent(val) : val.toLocaleString();
            },
          },
        },
      },
    },
  });
}

function renderGoldChart(goldObj, goldTimeframe) {
  const rawList = goldObj.timeseries || [];
  const filtered = filterTimeseries(rawList, goldTimeframe);
  return buildPerformanceChart({
    canvasId: "fa-gold-performance-chart",
    label: "24K Gold Price (EGP)",
    timeseries: filtered,
    valueKey: "carat_24k",
    labelKey: "date",
    mainColor: "rgba(139, 92, 246, 1)",
  });
}

function renderCurrencyChart(currObj, currencyTimeframe, selectedCurrency) {
  const rawList = currObj.timeseries || [];
  const filtered = filterTimeseries(rawList, currencyTimeframe);
  return buildPerformanceChart({
    canvasId: "fa-currency-performance-chart",
    label: `${selectedCurrency}/EGP`,
    timeseries: filtered,
    valueKey: "mid_rate",
    labelKey: "date",
    mainColor: "rgba(139, 92, 246, 1)",
  });
}

window.filterTimeseries = filterTimeseries;
window.buildPerformanceChart = buildPerformanceChart;
window.renderGoldChart = renderGoldChart;
window.renderCurrencyChart = renderCurrencyChart;
