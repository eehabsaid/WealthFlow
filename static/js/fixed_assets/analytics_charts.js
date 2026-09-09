"use strict";
// Fixed assets analytics — portfolio snapshot loader and chart drawing.
// Split out of analytics.js (200-line backlog). Bare globals.
// ════════════════════════════════════════════════════════════════════════════

async function loadFixedAssetsPortfolioSnapshot() {
  fixedAssetsState.portfolioSnapshotLoading = true;

  try {
    const response = await fetch("/api/fixed-assets/");
    if (!response.ok) throw new Error("Failed to load analytics snapshot");

    const data = await response.json();
    fixedAssetsState.portfolioSnapshot = data?.portfolio_snapshot || null;
  } catch (err) {
    fixedAssetsState.portfolioSnapshot = null;
  } finally {
    fixedAssetsState.portfolioSnapshotLoading = false;
    if (fixedAssetsState.activeTab === "analytics") {
      renderActiveFixedAssetsTab();
    }
  }
}

function drawFixedAssetsAnalyticsCharts(metrics, snapshot) {
  const liquidValue = snapshot?.liquidAssetsValue || 0;
  const fixedValue = snapshot?.fixedAssetsValue || metrics.totalFixedAssetsValue;

  drawFixedAssetsDoughnutChart(
    "fixedAssetsLiquidVsFixedChart",
    [t("liquid_assets", "Liquid Assets"), t("fixed_assets", "Fixed Assets")],
    [liquidValue, fixedValue]
  );

  const performanceRows = [...metrics.assetRows].sort((a, b) => b.roi - a.roi).slice(0, 8);

  drawFixedAssetsBarChart(
    "fixedAssetsPerformanceChart",
    performanceRows.map((row) => row.name),
    [
      {
        label: t("roi", "ROI"),
        data: performanceRows.map((row) => row.roi),
        color: "#1a6ef5",
      },
      {
        label: t("annual_return", "Annual Return"),
        data: performanceRows.map((row) => row.annualReturn),
        color: "#10b981",
      },
    ]
  );
}
