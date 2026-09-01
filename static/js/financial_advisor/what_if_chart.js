"use strict";

function _showSliderTooltip(slider, text) {
  let tooltip = document.getElementById("whatif-slider-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.id = "whatif-slider-tooltip";
    tooltip.className = "whatif-tooltip d-none";
    document.body.appendChild(tooltip);
  }

  tooltip.innerHTML = text;
  tooltip.classList.remove("d-none");

  const rect = slider.getBoundingClientRect();
  const min = Number(slider.min) || 0;
  const max = Number(slider.max) || 100;
  const val = Number(slider.value) || 0;
  const percent = max > min ? (val - min) / (max - min) : 0;

  const thumbWidth = 16;
  const trackWidth = Math.max(0, rect.width - thumbWidth);
  const thumbOffset = percent * trackWidth + thumbWidth / 2;

  const tooltipX = rect.left + window.scrollX + thumbOffset;
  const tooltipY = rect.top + window.scrollY - 8;

  tooltip.style.left = `${tooltipX}px`;
  tooltip.style.top = `${tooltipY}px`;
}

function _hideSliderTooltip() {
  const tooltip = document.getElementById("whatif-slider-tooltip");
  if (tooltip) {
    tooltip.classList.add("d-none");
  }
}

function _money(value) {
  const num = Number(value) || 0;
  if (typeof fmtpresent === "function") {
    return fmtpresent(num);
  }
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function _fmtDelta(val, isPct = false, digits = 1) {
  if (val === null || val === undefined) return "-";
  const num = Number(val) || 0;
  const sign = num > 0 ? "+" : "";
  if (isPct) return `${sign}${num.toFixed(digits)}%`;
  if (typeof fmtpresent === "function") {
    return `${sign}${fmtpresent(num)}`;
  }
  return `${sign}${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function _buildComparisonRowsHtml(data) {
  if (!data) return "";

  const base = data.baseline || {};
  const adj = data.adjusted || {};
  const delta = data.delta || {};

  const nwBase = base.net_worth_12m || 0;
  const nwAdj = adj.net_worth_12m || 0;
  const nwDeltaVal = delta.net_worth_12m || 0;
  const nwFav = delta.net_worth_12m_favorable;
  const nwBadgeBg = nwFav
    ? "rgba(34,197,94,0.15)"
    : nwDeltaVal === 0
      ? "rgba(108,117,125,0.15)"
      : "rgba(239,68,68,0.15)";
  const nwBadgeColor = nwFav
    ? "var(--accent-green, #22c55e)"
    : nwDeltaVal === 0
      ? "var(--text-muted, #9ca3af)"
      : "var(--accent-red, #ef4444)";

  const riskBase = base.risk_score || 0;
  const riskAdj = adj.risk_score || 0;
  const riskDeltaVal = delta.risk_score || 0;
  const riskFav = delta.risk_score_favorable;
  const riskBadgeBg = riskFav
    ? "rgba(34,197,94,0.15)"
    : riskDeltaVal === 0
      ? "rgba(108,117,125,0.15)"
      : "rgba(239,68,68,0.15)";
  const riskBadgeColor = riskFav
    ? "var(--accent-green, #22c55e)"
    : riskDeltaVal === 0
      ? "var(--text-muted, #9ca3af)"
      : "var(--accent-red, #ef4444)";

  const covBase = base.cash_coverage_months;
  const covAdj = adj.cash_coverage_months;
  const covDeltaVal = delta.cash_coverage_months;
  const covFav = delta.cash_coverage_favorable;
  const covBadgeBg = covFav
    ? "rgba(34,197,94,0.15)"
    : covDeltaVal === 0 || covDeltaVal === null
      ? "rgba(108,117,125,0.15)"
      : "rgba(239,68,68,0.15)";
  const covBadgeColor = covFav
    ? "var(--accent-green, #22c55e)"
    : covDeltaVal === 0 || covDeltaVal === null
      ? "var(--text-muted, #9ca3af)"
      : "var(--accent-red, #ef4444)";

  return `
    <div class="d-flex flex-column gap-3">
      <!-- Metric 1: Net Worth -->
      <div class="p-3 rounded d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
        <div class="fw-medium" style="color:var(--text-primary);" data-i18n="whatif_networth_12m">Net Worth (12 months)</div>
        <div class="d-flex align-items-center gap-3">
          <span class="small" style="color:var(--text-secondary);">${_money(nwBase)}</span>
          <i class="bi bi-arrow-right text-muted"></i>
          <span class="fw-bold" style="color:var(--text-primary);">${_money(nwAdj)}</span>
          <span class="badge px-2 py-1 fw-semibold" style="background:${nwBadgeBg}; color:${nwBadgeColor};">
            ${_fmtDelta(nwDeltaVal)}
          </span>
        </div>
      </div>

      <!-- Metric 2: Risk Score -->
      <div class="p-3 rounded d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
        <div class="fw-medium" style="color:var(--text-primary);" data-i18n="whatif_risk_score">Risk Score</div>
        <div class="d-flex align-items-center gap-3">
          <span class="small" style="color:var(--text-secondary);">${riskBase.toFixed(1)}</span>
          <i class="bi bi-arrow-right text-muted"></i>
          <span class="fw-bold" style="color:var(--text-primary);">${riskAdj.toFixed(1)}</span>
          <span class="badge px-2 py-1 fw-semibold" style="background:${riskBadgeBg}; color:${riskBadgeColor};">
            ${_fmtDelta(riskDeltaVal, false, 1)}
          </span>
        </div>
      </div>

      <!-- Metric 3: Cash Coverage -->
      <div class="p-3 rounded d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
        <div class="fw-medium" style="color:var(--text-primary);" data-i18n="whatif_cash_coverage">Cash Coverage (months)</div>
        <div class="d-flex align-items-center gap-3">
          <span class="small" style="color:var(--text-secondary);">${covBase !== null && covBase !== undefined ? covBase.toFixed(1) : "-"}</span>
          <i class="bi bi-arrow-right text-muted"></i>
          <span class="fw-bold" style="color:var(--text-primary);">${covAdj !== null && covAdj !== undefined ? covAdj.toFixed(1) : "-"}</span>
          <span class="badge px-2 py-1 fw-semibold" style="background:${covBadgeBg}; color:${covBadgeColor};">
            ${_fmtDelta(covDeltaVal, false, 1)}
          </span>
        </div>
      </div>
    </div>
  `;
}

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
