"use strict";

function _renderWhatIfChart(payload) {
  const canvas = document.getElementById("whatIfChart");
  if (!canvas || !window.Chart) return;

  if (typeof _destroyChart === "function") {
    _destroyChart("whatIfChart");
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

  const baseSeries = (payload.baseline?.series || []).map((pt) => pt.net_worth);
  const adjSeries = (payload.adjusted?.series || []).map((pt) => pt.net_worth);

  const baselineLabel =
    typeof t === "function" ? t("whatif_baseline_label", "Baseline") : "Baseline";
  const adjustedLabel =
    typeof t === "function" ? t("whatif_adjusted_label", "Adjusted") : "Adjusted";

  new Chart(canvas, {
    type: "line",
    data: {
      labels: monthLabels,
      datasets: [
        {
          label: baselineLabel,
          data: baseSeries,
          borderColor: "rgba(108, 117, 125, 0.8)",
          backgroundColor: "rgba(108, 117, 125, 0.05)",
          borderDash: [5, 5],
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 6,
        },
        {
          label: adjustedLabel,
          data: adjSeries,
          borderColor: "rgba(32, 201, 151, 1)",
          backgroundColor: "rgba(32, 201, 151, 0.12)",
          borderWidth: 2.5,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 7,
          fill: true,
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
                return typeof t === "function" ? t("wealth_growth_current", "Current") : "Current";
              }
              return typeof formatDate === "function" ? formatDate(raw) : raw;
            },
            label: function (ctx) {
              const val = Number(ctx.raw || 0);
              return `${ctx.dataset.label}: ${typeof fmtpresent === "function" ? fmtpresent(val) : val.toLocaleString()}`;
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

window._showSliderTooltip = _showSliderTooltip;
window._hideSliderTooltip = _hideSliderTooltip;
window._buildComparisonRowsHtml = _buildComparisonRowsHtml;
window._renderWhatIfChart = _renderWhatIfChart;
