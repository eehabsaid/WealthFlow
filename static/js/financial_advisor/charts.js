"use strict";
// Chart configuration and drawing methods
// This file is part of the financial_advisor module. Do not edit directly.

function _drawGoalTypeChart(payload) {
  const canvas = document.getElementById("goalPlanningTypeChart");
  if (!canvas || !window.Chart) return;

  _destroyChart("goalPlanningTypeChart");

  const direction = _pageDirection();
  const isRTL = direction === "rtl";
  const primaryText = _themeColor("--text-primary", "#e8f0fe");
  const gridColor = "rgba(123, 147, 201, 0.16)";

  const items = payload?.distribution?.by_type || [];
  const labels = items.map((item) => item.label || t("goal_planning_not_available"));
  const values = items.map((item) => Number(item.value_egp || 0));

  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          borderColor: "rgba(13, 21, 48, 0.9)",
          borderWidth: 2,
          backgroundColor: ["#4f8ff7", "#50d890", "#f3c846", "#8c7cf0", "#ff7c95", "#5da9ff"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: {
          position: "bottom",
          rtl: isRTL,
          reverse: isRTL,
          labels: {
            color: primaryText,
            boxWidth: 8,
            usePointStyle: true,
            pointStyle: "circle",
            textDirection: direction,
            padding: 14,
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
          callbacks: {
            label: (ctx) => {
              const total = values.reduce((sum, value) => sum + value, 0);
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

  const labels = data.month_labels || [];
  const series = data.series || {};
  const conservative = (series.conservative?.points || []).map((p) => p.net_worth);
  const expected = (series.expected?.points || []).map((p) => p.net_worth);
  const optimistic = (series.optimistic?.points || []).map((p) => p.net_worth);

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: t("wealth_growth_scenario_conservative", "Conservative"), data: conservative, borderColor: "#6c757d", backgroundColor: "rgba(108,117,125,0.12)", tension: 0.3, pointRadius: 2, borderWidth: 2 },
        { label: t("wealth_growth_scenario_expected", "Expected"), data: expected, borderColor: "#1a6ef5", backgroundColor: "rgba(26,110,245,0.12)", tension: 0.3, pointRadius: 2, borderWidth: 2 },
        { label: t("wealth_growth_scenario_optimistic", "Optimistic"), data: optimistic, borderColor: "#20c997", backgroundColor: "rgba(32,201,151,0.12)", tension: 0.3, pointRadius: 2, borderWidth: 2 },
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
          callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.raw)}` },
        },
      },
      scales: {
        x: { reverse: isRTL, ticks: { color: secondaryText, textDirection: direction }, grid: { color: gridColor } },
        y: { position: isRTL ? "right" : "left", ticks: { color: secondaryText, align: isRTL ? "end" : "start" }, grid: { color: gridColor } },
      },
    },
    plugins: window.SharedCrosshairPlugin ? [window.SharedCrosshairPlugin] : [],
  });
}

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

