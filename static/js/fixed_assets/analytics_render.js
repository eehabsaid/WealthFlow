"use strict";
// Fixed assets analytics tab — main render function and portfolio KPI
// cards. Split out of analytics.js (200-line backlog). Bare globals —
// called by fixed_assets/tabs.js and fixed_assets/index.js.
// ════════════════════════════════════════════════════════════════════════════

function renderFixedAssetsAnalytics(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = buildDashboardAnalyticsAssets(assets);

  if (!assetsArray.length) {
    container.innerHTML = `
      <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
          <div class="display-5 mb-3">📊</div>
          <h4 class="mt-2 fixed-assets-empty-title" data-i18n="fixed_assets_analytics_empty">No Analytics Data</h4>
          <p class="small mb-0 fixed-assets-muted" data-i18n="fixed_assets_analytics_empty_desc">Add fixed assets to calculate analytics.</p>
      </div>
    `;
    applyTranslations();
    return;
  }

  const metrics = getFixedAssetsAnalyticsMetrics(assetsArray);

  const portfolioCards = renderFixedAssetsPortfolioCards(
    metrics,
    fixedAssetsState.portfolioSnapshot
  );
  const tableRows = metrics.assetRows.length
    ? metrics.assetRows
        .map(
          (row) => `
      <tr>
        <td class="fixed-assets-card-title">${row.name}</td>
        <td data-i18n="${fixedAssetTypeToI18nKey(row.type)}">${row.type}</td>
        <td class="text-end">${fmtpresent(row.roi)}%</td>
        <td class="text-end">${fmtpresent(row.appreciation)}%</td>
        <td class="text-end">${fmtpresent(row.annualReturn)}%</td>
        <td class="text-end">${row.holdingPeriodLabel}</td>
        <td class="text-end">${fmtpresent(row.renovationCostPercent)}%</td>
        <td class="text-end ${row.gainAmount >= 0 ? "text-success" : "text-danger"}">${fmt(row.gainAmount)}</td>
      </tr>
    `
        )
        .join("")
    : _noDataFixedAssets(8);

  container.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:20px;">
      ${portfolioCards}
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;margin-bottom:20px;">
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px;" data-i18n="liquid_vs_fixed_assets"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsLiquidVsFixedChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px;" data-i18n="asset_performance"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsPerformanceChart"></canvas></div>
      </div>
    </div>

    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden;">
      <div class="fixed-assets-section-title" style="padding:14px 20px;font-weight:700;border-bottom:1px solid var(--border-color);" data-i18n="per_asset_analytics"></div>
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th data-i18n="asset_name">Asset Name</th>
              <th data-i18n="asset_type">Asset Type</th>
              <th class="text-end" data-i18n="roi">ROI</th>
              <th class="text-end" data-i18n="appreciation_percent">Appreciation %</th>
              <th class="text-end" data-i18n="annual_return">Annual Return</th>
              <th class="text-end" data-i18n="holding_period">Holding Period</th>
              <th class="text-end" data-i18n="renovation_cost_percent">Renovation Cost %</th>
              <th class="text-end" data-i18n="gain_amount">Gain Amount</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    </div>
  `;

  applyTranslations();
  drawFixedAssetsAnalyticsCharts(metrics, fixedAssetsState.portfolioSnapshot);
}

function renderFixedAssetsPortfolioCards(metrics, snapshot) {
  const fixedValueCard = renderFixedAssetsKpi(
    "bi bi-bank2",
    "total_fixed_assets_value",
    fmt(metrics.totalFixedAssetsValue)
  );

  if (!snapshot) {
    return `
      ${fixedValueCard}
      ${renderFixedAssetsKpi("bi bi-pie-chart", "net_worth_contribution", "...")}
      ${renderFixedAssetsKpi("bi bi-arrows-collapse", "liquid_vs_fixed_assets", "...")}
      ${renderFixedAssetsKpi("bi bi-diagram-3", "diversification", `${fmtpresent(metrics.diversificationScore)}%`)}
    `;
  }

  const liquidVsFixedLabel = `${fmtpresent(snapshot.liquidAssetsRatio)}% / ${fmtpresent(snapshot.fixedAssetsRatio)}%`;

  return `
    ${fixedValueCard}
    ${renderFixedAssetsKpi("bi bi-pie-chart", "net_worth_contribution", `${fmtpresent(snapshot.netWorthContribution)}%`)}
    ${renderFixedAssetsKpi("bi bi-arrows-collapse", "liquid_vs_fixed_assets", liquidVsFixedLabel)}
    ${renderFixedAssetsKpi("bi bi-diagram-3", "diversification", `${fmtpresent(metrics.diversificationScore)}%`)}
  `;
}
