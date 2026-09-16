"use strict";
// Dashboard analytics gold-grouping and sell-price lookup.
// Part of the fixed_assets module (split from the former monolithic gold.js,
// 200-line rule). Do not edit directly.

function buildDashboardAnalyticsAssets(assets) {
  const source = normalizeFixedAssetsData(assets);
  const groupedGoldMap = {};
  const nonGoldAssets = [];

  source.forEach((asset) => {
    const assetType = asset.asset_type || asset.type;
    if (!isGoldAssetType(assetType)) {
      nonGoldAssets.push(asset);
      return;
    }

    const purityKey = normalizeGoldPurity(asset?.gold_details?.purity || asset?.purity || "24k");
    if (!groupedGoldMap[purityKey]) {
      groupedGoldMap[purityKey] = {
        ...asset,
        id: `gold-group-${purityKey}`,
        name: `${t("type_gold", "Gold")} ${purityKey.toUpperCase()}`,
        asset_type: FIXED_ASSET_TYPES.GOLD,
        purchase_price: 0,
        current_market_value: 0,
        purchase_date: asset.purchase_date || null,
        renovations: [],

        // Aggregated Gold Analytics must recalculate these values
        // from the aggregated purchase/current values.
        total_acquisition_costs: 0,
        total_renovation_costs: 0,
      };

      delete groupedGoldMap[purityKey].total_investment;
      delete groupedGoldMap[purityKey].gain_loss;
      delete groupedGoldMap[purityKey].roi;
      delete groupedGoldMap[purityKey].appreciation;
      delete groupedGoldMap[purityKey].annual_return;
    }

    groupedGoldMap[purityKey].purchase_price += parseFloat(asset.purchase_price) || 0;
    groupedGoldMap[purityKey].current_market_value += parseFloat(asset.current_market_value) || 0;

    if (asset.purchase_date) {
      const currentDate = new Date(
        groupedGoldMap[purityKey].purchase_date || asset.purchase_date
      ).getTime();
      const candidateDate = new Date(asset.purchase_date).getTime();
      if (
        !Number.isNaN(candidateDate) &&
        (Number.isNaN(currentDate) || candidateDate < currentDate)
      ) {
        groupedGoldMap[purityKey].purchase_date = asset.purchase_date;
      }
    }
  });

  const groupedGoldAssets = Object.values(groupedGoldMap);
  return [...nonGoldAssets, ...groupedGoldAssets];
}

function getGoldSellPerGram(goldPayload, purityKey) {
  if (!goldPayload) return 0;
  const map = {
    "24k": parseFloat(goldPayload.carat_24k) || 0,
    "22k": parseFloat(goldPayload.carat_22k) || 0,
    "21k": parseFloat(goldPayload.carat_21k) || 0,
    "18k": parseFloat(goldPayload.carat_18k) || 0,
  };
  return map[purityKey] || map["24k"] || 0;
}
