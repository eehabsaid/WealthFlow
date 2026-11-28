"use strict";
// Cash flow forecast tab — projected cash balance line chart (Chart.js).
// Data sources (existing payload fields only): timeline[].ending_cash and
// checkpoints.current (dashed reference line). No calculations beyond
// mapping those values into chart datasets.
// This file is part of the financial_advisor module.

function _cashFlowChartHexToRgba(hex, alpha) {
  const value = String(hex || "").trim();
  if (value.startsWith("#")) {
    const raw = value.slice(1);
    let r = null,
      g = null,
      b = null;
    if (raw.length === 6) {
      r = parseInt(raw.slice(0, 2), 16);
      g = parseInt(raw.slice(2, 4), 16);
      b = parseInt(raw.slice(4, 6), 16);
    } else if (raw.length === 3) {
      r = parseInt(raw[0] + raw[0], 16);
      g = parseInt(raw[1] + raw[1], 16);
      b = parseInt(raw[2] + raw[2], 16);
    }
    if (r !== null) return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return `rgba(79, 140, 255, ${alpha})`;
}

function _renderCashFlowChart(timeline, currentCash) {
  if (!window.Chart || !timeline.length) return;
  const canvas = document.getElementById("cash_flow_chart_canvas");
  if (!canvas) return;
  _destroyChart("cash_flow_chart_canvas");

  const langCode = currentLang ? currentLang() : document.documentElement.lang || "en";
  const monthFmt = new Intl.DateTimeFormat(langCode, { month: "short", timeZone: "UTC" });
  const compactFmt = new Intl.NumberFormat(langCode, {
    notation: "compact",
    maximumFractionDigits: 1,
  });
  const accent = _themeColor("--accent-primary", "#4f8cff");
  const muted = _themeColor("--text-muted", "#8a94a6");
  const grid = _themeColor("--border-color", "rgba(128, 128, 128, 0.2)");

  const labels = timeline.map((m) => (m.month ? monthFmt.format(new Date(`${m.month}-01`)) : ""));
  const series = timeline.map((m) => Number(m.ending_cash || 0));
  const reference = series.map(() => Number(currentCash || 0));

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: t("cash_flow_chart_forecast"),
          data: series,
          borderColor: accent,
          borderWidth: 2.5,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.45,
          fill: true,
          backgroundColor: (ctx) => {
            const chart = ctx.chart;
            const area = chart.chartArea;
            if (!area) return _cashFlowChartHexToRgba(accent, 0.12);
            const gradient = chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
            gradient.addColorStop(0, _cashFlowChartHexToRgba(accent, 0.22));
            gradient.addColorStop(1, _cashFlowChartHexToRgba(accent, 0));
            return gradient;
          },
        },
        {
          label: t("cash_flow_chart_current"),
          data: reference,
          borderColor: muted,
          borderWidth: 1.5,
          borderDash: [6, 4],
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: muted, usePointStyle: true, pointStyle: "line" } },
        tooltip: {
          callbacks: {
            label: (item) => ` ${item.dataset.label}: ${_money(item.parsed.y)}`,
          },
        },
      },
      scales: {
        x: { ticks: { color: muted }, grid: { display: false } },
        y: {
          ticks: { color: muted, callback: (value) => compactFmt.format(value) },
          grid: { color: grid },
        },
      },
    },
  });
}
