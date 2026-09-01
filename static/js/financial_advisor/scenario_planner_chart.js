"use strict";
// Scenario Planner Multi-Series Chart Module
// This file is part of the financial_advisor module. Do not edit directly.

(function () {
  const COLOR_PALETTE = [
    { border: "rgba(26, 110, 245, 1)", bg: "rgba(26, 110, 245, 0.12)" }, // Blue / Primary
    { border: "rgba(255, 209, 102, 1)", bg: "rgba(255, 209, 102, 0.12)" }, // Yellow
    { border: "rgba(255, 77, 109, 1)", bg: "rgba(255, 77, 109, 0.12)" }, // Red
    { border: "rgba(0, 214, 143, 1)", bg: "rgba(0, 214, 143, 0.12)" }, // Green
    { border: "rgba(168, 85, 247, 1)", bg: "rgba(168, 85, 247, 0.12)" }, // Purple
  ];

  function _renderScenarioPlannerChart(payload) {
    const canvas = document.getElementById("scenarioPlannerChart");
    if (!canvas || !window.Chart) return;

    if (typeof _destroyChart === "function") {
      _destroyChart("scenarioPlannerChart");
    } else {
      const existing = Chart.getChart(canvas);
      if (existing) existing.destroy();
    }

    const direction = typeof _pageDirection === "function" ? _pageDirection() : "ltr";
    const isRTL = direction === "rtl";
    const primaryText =
      typeof _themeColor === "function" ? _themeColor("--text-primary", "#e8f0fe") : "#e8f0fe";
    const secondaryText =
      typeof _themeColor === "function" ? _themeColor("--text-secondary", "#7b93c9") : "#7b93c9";
    const gridColor = "rgba(123, 147, 201, 0.16)";

    canvas.setAttribute("dir", direction);
    canvas.style.direction = direction;

    const rawMonthLabels = payload.month_labels || [];
    const monthLabels = rawMonthLabels.map((lbl) => {
      if (!lbl || lbl === "Current" || lbl === "current") {
        return typeof t === "function" ? t("wealth_growth_current", "Current") : "Current";
      }
      return typeof formatDate === "function" ? formatDate(lbl) : lbl;
    });

    const datasets = [];

    // Baseline dataset (dashed line)
    const baseObj = payload.baseline || {};
    const basePoints = (baseObj.series || []).map((pt) => Number(pt.net_worth || 0));
    const baselineLabel =
      typeof t === "function" ? t("scenario_planner_baseline_label", "Baseline") : "Baseline";

    datasets.push({
      label: baselineLabel,
      data: basePoints,
      borderColor: "rgba(123, 147, 201, 0.8)",
      backgroundColor: "rgba(123, 147, 201, 0.05)",
      borderDash: [5, 5],
      borderWidth: 2,
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 6,
    });

    // N Scenario datasets
    const scenarios = payload.scenarios || [];
    scenarios.forEach((sc, idx) => {
      const palette = COLOR_PALETTE[idx % COLOR_PALETTE.length];
      const pts = (sc.series || []).map((pt) => Number(pt.net_worth || 0));

      datasets.push({
        label: sc.name || `Scenario ${sc.id}`,
        data: pts,
        borderColor: palette.border,
        backgroundColor: palette.bg,
        borderWidth: 2.5,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 7,
        fill: idx === 0,
      });
    });

    new Chart(canvas, {
      type: "line",
      data: {
        labels: monthLabels,
        datasets: datasets,
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
            position: "top",
            rtl: isRTL,
            reverse: isRTL,
            labels: {
              color: primaryText,
              usePointStyle: true,
              pointStyle: "circle",
              boxWidth: 10,
              padding: 16,
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
            padding: 12,
            callbacks: {
              title: function (items) {
                if (!items || !items.length) return "";
                const raw = items[0].label || "";
                if (
                  raw === "Current" ||
                  raw === "current" ||
                  raw ===
                    (typeof t === "function" ? t("wealth_growth_current", "Current") : "Current")
                ) {
                  return typeof t === "function"
                    ? t("wealth_growth_current", "Current")
                    : "Current";
                }
                return typeof formatDate === "function" ? formatDate(raw) : raw;
              },
              label: function (ctx) {
                const val = Number(ctx.raw || 0);
                const moneyStr =
                  typeof fmtpresent === "function" ? fmtpresent(val) : val.toLocaleString();
                return `${ctx.dataset.label}: ${moneyStr}`;
              },
            },
          },
        },
        scales: {
          x: {
            reverse: isRTL,
            ticks: { color: secondaryText, font: { size: 11 } },
            grid: { color: gridColor },
          },
          y: {
            position: isRTL ? "right" : "left",
            ticks: {
              color: secondaryText,
              font: { size: 11 },
              callback: function (val) {
                return typeof fmtpresent === "function" ? fmtpresent(val) : val.toLocaleString();
              },
            },
            grid: { color: gridColor },
          },
        },
      },
      plugins: window.SharedCrosshairPlugin ? [window.SharedCrosshairPlugin] : [],
    });
  }

  window._renderScenarioPlannerChart = _renderScenarioPlannerChart;
})();
