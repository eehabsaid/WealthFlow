"use strict";
// Fixed assets analytics — per-asset metrics computation (ROI, appreciation,
// annual return, diversification score) and holding-period formatter. Split
// out of analytics.js (200-line backlog). Bare globals.
// ════════════════════════════════════════════════════════════════════════════

function getFixedAssetsAnalyticsMetrics(assets) {
  const now = new Date();
  const assetRows = assets.map((asset) => {
    const purchasePrice = parseFloat(asset.purchase_price) || 0;
    const currentValue = parseFloat(asset.current_market_value) || 0;
    const renovationCost =
      asset.total_renovation_costs !== undefined
        ? asset.total_renovation_costs
        : (asset.renovations || []).reduce(
            (sum, item) => sum + (parseFloat(item.amount_egp) || 0),
            0
          );
    const acquisitionCost =
      asset.total_acquisition_costs !== undefined ? asset.total_acquisition_costs : 0;
    const investmentBase =
      asset.total_investment !== undefined
        ? asset.total_investment
        : purchasePrice + renovationCost + acquisitionCost;

    const gainAmount =
      asset.gain_loss !== undefined ? asset.gain_loss : currentValue - investmentBase;

    const roi =
      asset.roi !== undefined ? asset.roi : investmentBase > 0 ? gainAmount / investmentBase : 0;

    const appreciation =
      asset.appreciation !== undefined
        ? asset.appreciation
        : purchasePrice > 0
          ? (currentValue - purchasePrice) / purchasePrice
          : 0;

    const purchaseDate = asset.purchase_date ? new Date(asset.purchase_date) : null;
    const holdingYearsRaw = purchaseDate
      ? (now - purchaseDate) / (1000 * 60 * 60 * 24 * 365.25)
      : 0;
    const holdingYears = holdingYearsRaw > 0 ? holdingYearsRaw : 0;
    const annualReturn =
      asset.annual_return !== undefined
        ? asset.annual_return
        : investmentBase > 0 && holdingYears > 0
          ? Math.pow(currentValue / investmentBase, 1 / holdingYears) - 1
          : 0;
    const holdingMonths = purchaseDate
      ? Math.max(0, Math.round((now - purchaseDate) / (1000 * 60 * 60 * 24 * 30.4375)))
      : 0;
    const renovationCostPercent = purchasePrice > 0 ? renovationCost / purchasePrice : 0;

    return {
      name: asset.name || "—",
      type: asset.asset_type || t("type_other", "Other"),
      roi,
      appreciation,
      annualReturn: Number.isFinite(annualReturn) ? annualReturn : 0,
      holdingPeriodMonths: holdingMonths,
      holdingPeriodLabel: formatHoldingPeriod(holdingMonths),
      renovationCostPercent,
      gainAmount,
      currentValue,
    };
  });

  const totalFixedAssetsValue = assetRows.reduce((sum, row) => sum + row.currentValue, 0);
  const shares = assetRows
    .map((row) => (totalFixedAssetsValue > 0 ? row.currentValue / totalFixedAssetsValue : 0))
    .filter((share) => share > 0);
  const concentration = shares.reduce((sum, share) => sum + share * share, 0);
  const diversificationScore =
    shares.length > 1
      ? Math.max(0, ((1 - concentration) / (1 - 1 / shares.length)) * 100)
      : shares.length === 1
        ? 0
        : 100;

  return {
    totalFixedAssetsValue,
    diversificationScore,
    assetRows,
  };
}

function formatHoldingPeriod(months) {
  if (!months) {
    return `0 ${t("months", "Months")}`;
  }

  if (months < 12) {
    return `${months} ${t("months", "Months")}`;
  }

  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;

  if (!remainingMonths) {
    return `${years} ${t("years", "Years")}`;
  }

  return `${years} ${t("years", "Years")} ${remainingMonths} ${t("months", "Months")}`;
}
