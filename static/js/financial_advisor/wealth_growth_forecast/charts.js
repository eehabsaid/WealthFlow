"use strict";
// Wealth Growth Forecast chart rendering
// This file is part of the financial_advisor module. Do not edit directly.

function _drawWealthGrowthChart(data) {
  const canvas = document.getElementById("wealthGrowthChart");
  if (!canvas || !window.Chart) return;

  _destroyChart("wealthGrowthChart");

  const direction = _pageDirection();
  const isRTL = direction === "rtl";
  const primaryText = _themeColor("--text-primary", "#e8f0fe");
  const secondaryText = _themeColor("--text-secondary", "#7b93c9");
  const gridColor = "rgba(123, 147, 201, 0.16)";

  canvas.setAttribute("dir", direction);
  canvas.style.direction = direction;
  const chartWrapper = canvas.parentElement;
  if (chartWrapper) {
    chartWrapper.setAttribute("dir", direction);
  }

  const rawLabels = data.month_labels || [];
  const labels = rawLabels.map((lbl) => {
    if (!lbl || lbl === "Current" || lbl === "current") {
      return typeof t === "function" ? t("wealth_growth_current", "Current") : "Current";
    }
    return typeof formatDate === "function" ? formatDate(lbl) : lbl;
  });

  const series = data.series || {};
  const conservative = (series.conservative?.points || []).map((p) => p.net_worth);
  const expected = (series.expected?.points || []).map((p) => p.net_worth);
  const optimistic = (series.optimistic?.points || []).map((p) => p.net_worth);

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: t("wealth_growth_scenario_conservative", "Conservative"),
          data: conservative,
          borderColor: "#6c757d",
          backgroundColor: "rgba(108,117,125,0.12)",
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 2,
        },
        {
          label: t("wealth_growth_scenario_expected", "Expected"),
          data: expected,
          borderColor: "#1a6ef5",
          backgroundColor: "rgba(26,110,245,0.12)",
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 2,
        },
        {
          label: t("wealth_growth_scenario_optimistic", "Optimistic"),
          data: optimistic,
          borderColor: "#20c997",
          backgroundColor: "rgba(32,201,151,0.12)",
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          rtl: isRTL,
          reverse: isRTL,
          labels: {
            color: primaryText,
            textDirection: direction,
            usePointStyle: true,
            pointStyle: "rectRounded",
            boxWidth: 12,
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
            title: (items) => {
              if (!items || !items.length) return "";
              const raw = items[0].label || "";
              if (
                raw === "Current" ||
                raw === "current" ||
                raw ===
                  (typeof t === "function" ? t("wealth_growth_current", "Current") : "Current")
              ) {
                return typeof t === "function" ? t("wealth_growth_current", "Current") : "Current";
              }
              return typeof formatDate === "function" ? formatDate(raw) : raw;
            },
            label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.raw)}`,
          },
        },
      },
      scales: {
        x: {
          reverse: isRTL,
          ticks: { color: secondaryText, textDirection: direction },
          grid: { color: gridColor },
        },
        y: {
          position: isRTL ? "right" : "left",
          ticks: { color: secondaryText, align: isRTL ? "end" : "start" },
          grid: { color: gridColor },
        },
      },
    },
    plugins: window.SharedCrosshairPlugin ? [window.SharedCrosshairPlugin] : [],
  });
}
