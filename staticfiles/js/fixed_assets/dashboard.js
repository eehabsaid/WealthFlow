"use strict";
// Fixed assets dashboard tab rendering
// This file is part of the fixed_assets module. Do not edit directly.

function renderFixedAssetsDashboard(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = buildDashboardAnalyticsAssets(assets);

  if (!assetsArray.length) {
    container.innerHTML = `
      <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
          <div class="display-5 mb-3">📈</div>
          <h4 class="mt-2 fixed-assets-empty-title" data-i18n="fixed_assets_dashboard_empty">No Dashboard Data</h4>
          <p class="small mb-0 fixed-assets-muted" data-i18n="fixed_assets_dashboard_empty_desc">Add fixed assets to see your dashboard analytics.</p>
      </div>
    `;
    applyTranslations();
    return;
  }

  const metrics = getFixedAssetsDashboardMetrics(assetsArray);
  const gainColor = metrics.totalGain >= 0 ? "#17a34a" : "#ef4444";

  container.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px;">
      ${renderFixedAssetsKpi("bi bi-building", "total_assets", fmtInt(metrics.totalAssets))}
      ${renderFixedAssetsKpi("bi bi-cash-stack", "total_purchase_value", fmt(metrics.totalPurchaseValue))}
      ${renderFixedAssetsKpi("bi bi-graph-up-arrow", "current_market_value", fmt(metrics.currentMarketValue))}
      ${renderFixedAssetsKpi("bi bi-plus-slash-minus", "total_gain", `<span style="color:${gainColor}">${fmt(metrics.totalGain)}</span>`)}
      ${renderFixedAssetsKpi("bi bi-percent", "average_appreciation_percent", `${fmtpresent(metrics.averageAppreciation)}%`)}
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-weight:700;margin-bottom:14px;" data-i18n="asset_allocation"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsAllocationChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-weight:700;margin-bottom:14px;" data-i18n="asset_type_distribution"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsTypeChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-weight:700;margin-bottom:14px;" data-i18n="portfolio_distribution"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsPortfolioChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-weight:700;margin-bottom:14px;" data-i18n="value_growth_over_time"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsGrowthChart"></canvas></div>
      </div>
    </div>
  `;

  applyTranslations();
  drawFixedAssetsDashboardCharts(metrics);
}

