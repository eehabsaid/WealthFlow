"use strict";
// Fixed assets chart drawing utilities
// This file is part of the fixed_assets module. Do not edit directly.

function renderFixedAssetsKpi(iconClass, labelKey, value) {
  return `
    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:18px 20px;">
      <div style="font-size:20px;margin-bottom:6px;color:var(--accent-primary);"><i class="${iconClass}"></i></div>
      <div style="font-size:11px;font-weight:700;letter-spacing:.05em;color:var(--text-secondary);text-transform:uppercase;margin-bottom:6px;" data-i18n="${labelKey}"></div>
      <div style="font-size:22px;font-weight:800;color:var(--text-primary);">${value}</div>
    </div>
  `;
}

function renderFixedAssetsPlaceholder(titleKey, descKey) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  container.innerHTML = `
    <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
        <div class="display-5 mb-3">🧭</div>
        <h4 class="mt-2 fixed-assets-empty-title" data-i18n="${titleKey}"></h4>
        <p class="small mb-0" style="color:var(--text-secondary);" data-i18n="${descKey}"></p>
    </div>
  `;
  applyTranslations();
}

function getFixedAssetsDashboardMetrics(assets) {
  const totalAssets = assets.length;
  const totalPurchaseValue = assets.reduce(
    (sum, asset) => sum + (parseFloat(asset.purchase_price) || 0),
    0
  );
  const currentMarketValue = assets.reduce(
    (sum, asset) => sum + (parseFloat(asset.current_market_value) || 0),
    0
  );
  const totalInvestment = assets.reduce(
    (sum, asset) =>
      sum + (parseFloat(asset.total_investment) || parseFloat(asset.purchase_price) || 0),
    0
  );
  const totalGain = currentMarketValue - totalInvestment;

  const appreciationValues = assets
    .filter(
      (asset) => (parseFloat(asset.total_investment) || parseFloat(asset.purchase_price) || 0) > 0
    )
    .map((asset) => {
      const investment =
        parseFloat(asset.total_investment) || parseFloat(asset.purchase_price) || 0;
      const current = parseFloat(asset.current_market_value) || 0;
      return ((current - investment) / investment) * 100;
    });

  const averageAppreciation = appreciationValues.length
    ? appreciationValues.reduce((sum, value) => sum + value, 0) / appreciationValues.length
    : 0;

  const allocation = assets
    .map((asset) => ({
      label: asset.name || "—",
      value: parseFloat(asset.current_market_value) || 0,
    }))
    .filter((item) => item.value > 0);

  const typeMap = new Map();
  assets.forEach((asset) => {
    const key = asset.asset_type || t("type_other");
    typeMap.set(key, (typeMap.get(key) || 0) + 1);
  });

  const portfolioStatusMap = new Map();
  assets.forEach((asset) => {
    const isSold = asset.status === "Sold";
    const label = isSold ? t("sold_assets") : t("owned_assets");
    const value = isSold
      ? parseFloat(asset.sale?.net_sale_amount) || parseFloat(asset.sale?.sale_price) || 0
      : parseFloat(asset.current_market_value) || 0;
    portfolioStatusMap.set(label, (portfolioStatusMap.get(label) || 0) + value);
  });

  const growthSeries = buildFixedAssetsGrowthSeries(assets);

  return {
    totalAssets,
    totalPurchaseValue,
    currentMarketValue,
    totalGain,
    averageAppreciation,
    allocation,
    typeDistribution: Array.from(typeMap.entries()).map(([label, value]) => ({
      label,
      value,
    })),
    portfolioDistribution: Array.from(portfolioStatusMap.entries())
      .map(([label, value]) => ({ label, value }))
      .filter((item) => item.value > 0),
    growthSeries,
  };
}

function buildFixedAssetsGrowthSeries(assets) {
  const sortedAssets = [...assets].sort((a, b) => {
    const dateA = new Date(a.purchase_date || 0).getTime();
    const dateB = new Date(b.purchase_date || 0).getTime();
    return dateA - dateB;
  });

  let cumulativePurchase = 0;
  let cumulativeCurrent = 0;

  const labels = [];
  const purchaseValues = [];
  const currentValues = [];

  sortedAssets.forEach((asset) => {
    cumulativePurchase += parseFloat(asset.purchase_price) || 0;
    cumulativeCurrent += parseFloat(asset.current_market_value) || 0;

    labels.push(asset.purchase_date || asset.name || "—");
    purchaseValues.push(cumulativePurchase);
    currentValues.push(cumulativeCurrent);
  });

  return {
    labels,
    purchaseValues,
    currentValues,
  };
}


function _noDataFixedAssets(cols) {
  return `<tr><td colspan="${cols}" style="text-align:center;padding:28px;color:var(--text-secondary)" data-i18n="no_data">${t("no_data", "No data available")}</td></tr>`;
}
