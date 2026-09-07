"use strict";
// Risk radar chart drawing.

window.RA = window.RA || {};

window.RA.drawRiskRadarChart = function(payload) {
  if (typeof _destroyChart === "function") _destroyChart("riskRadarChart");
  const radarData = payload?.radar || {};
  if (!radarData.labels || !radarData.values) return;

  const canvas = document.getElementById("riskRadarChart");
  if (!canvas || !window.Chart) return;
  const labels = radarData.labels.map((k) => (typeof t === "function" ? t(k, k) : k));

  document.addEventListener("languageChanged", () => {
    if (window._riskRadarChart) {
      window._riskRadarChart.data.labels = radarData.labels.map((k) =>
        typeof t === "function" ? t(k, k) : k
      );
      window._riskRadarChart.update();
    }
  });
  const textPrimary =
    typeof _themeColor === "function" ? _themeColor("--text-primary", "#333") : "#333";
  const gridColor =
    typeof _themeColor === "function" ? _themeColor("--border-color", "#e2e8f0") : "#e2e8f0";
  const isRtl = typeof _pageDirection === "function" ? _pageDirection() === "rtl" : false;

  // Ensure chart updates on language change
  const updateChartLabels = () => {
    if (!window._riskRadarChart) return;
    const translatedLabels = radarData.labels.map((k) => (typeof t === "function" ? t(k, k) : k));
    window._riskRadarChart.data.labels = translatedLabels;
    window._riskRadarChart.data.datasets[0].label =
      typeof t === "function" ? t("risk_analysis_risk_score", "Risk Score") : "Risk Score";
    window._riskRadarChart.update();
  };

  if (window._riskRadarChart) {
    window._riskRadarChart.destroy();
  }

  window._riskRadarChart = new Chart(canvas, {
    type: "radar",
    data: {
      labels: labels,
      datasets: [
        {
          label:
            typeof t === "function" ? t("risk_analysis_risk_score", "Risk Score") : "Risk Score",
          data: radarData.values,
          backgroundColor: "rgba(255, 149, 0, 0.2)",
          borderColor: "rgba(255, 149, 0, 1)",
          pointBackgroundColor: "rgba(255, 149, 0, 1)",
          pointBorderColor: "#fff",
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: "rgba(255, 149, 0, 1)",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      rtl: isRtl,
      scales: {
        r: {
          angleLines: { color: gridColor },
          grid: { color: gridColor },
          pointLabels: {
            color: "#888",
            font: { size: 11, family: "system-ui, -apple-system, sans-serif" },
          },
          ticks: {
            backdropColor: "transparent",
            color:
              typeof _themeColor === "function" ? _themeColor("--text-secondary", "#666") : "#666",
            stepSize: 20,
            min: 0,
            max: 100,
            display: true,
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor:
            typeof _themeColor === "function" ? _themeColor("--bg-secondary", "#fff") : "#fff",
          titleColor: textPrimary,
          bodyColor: textPrimary,
          borderColor: gridColor,
          borderWidth: 1,
          displayColors: false,
          callbacks: {
            label: function (context) {
              return context.formattedValue + " / 100";
            },
          },
        },
      },
    },
  });
}

