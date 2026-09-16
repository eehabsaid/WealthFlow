"use strict";
// Fixed assets list rendering (gold grouping + non-gold rows).
// Part of the fixed_assets module (split from the former monolithic list.js,
// 200-line rule). Do not edit directly.

function renderFixedAssetsList(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = normalizeFixedAssetsData(assets);
  const goldAssets = assetsArray.filter((asset) => isGoldAssetType(asset.asset_type || asset.type));
  const nonGoldAssets = assetsArray.filter(
    (asset) => !isGoldAssetType(asset.asset_type || asset.type)
  );

  if (!assetsArray || assetsArray.length === 0) {
    container.innerHTML = `
            <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
                <div class="display-5 mb-3">🏢</div>
                <h4 class="mt-2 fixed-assets-empty-title" data-i18n="no_fixed_assets">No Fixed Assets Registered</h4>
                <p class="small mb-4 fixed-assets-muted" data-i18n="no_fixed_assets_desc">You haven't added any fixed assets or properties to your tracker portfolio yet.</p>
                <button class="btn btn-sm btn-primary-custom" onclick="showFixedAssetModal()">
                    <i class="bi bi-plus-lg"></i> <span data-i18n="add_first_asset">Register Your First Asset</span>
                </button>
            </div>
        `;
    if (typeof applyTranslations === "function") applyTranslations();
    return;
  }

  const groupedGoldMap = {};
  goldAssets.forEach((asset) => {
    const purityKey = normalizeGoldPurity(asset?.gold_details?.purity || asset?.purity || "24k");
    const weight = parseFloat(asset?.gold_details?.weight) || 0;
    const unit = asset?.gold_details?.unit || "gram";
    const weightInGrams = weight * getGoldUnitFactor(unit);

    if (!groupedGoldMap[purityKey]) {
      groupedGoldMap[purityKey] = {
        purity_key: purityKey,
        purity_label: purityKey.toUpperCase(),
        total_weight_grams: 0,
        total_purchase_value: 0,
        total_current_market_value: 0,
        purchases_count: 0,
      };
    }

    groupedGoldMap[purityKey].total_weight_grams += weightInGrams;
    groupedGoldMap[purityKey].total_purchase_value += parseFloat(asset.purchase_price) || 0;
    groupedGoldMap[purityKey].total_current_market_value +=
      parseFloat(asset.current_market_value) || 0;
    groupedGoldMap[purityKey].purchases_count += 1;
  });

  const groupedGoldRows = Object.values(groupedGoldMap).sort((a, b) => {
    const rank = { "24k": 1, "22k": 2, "21k": 3, "18k": 4 };
    return (rank[a.purity_key] || 99) - (rank[b.purity_key] || 99);
  });

  let html = `
    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden;">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th data-i18n="asset_name">Asset Name</th>
              <th data-i18n="asset_type">Asset Type</th>
              <th data-i18n="purity">Purity</th>
              <th class="text-end" data-i18n="total_weight">Total Weight</th>
              <th class="text-end" data-i18n="total_purchase_value">Total Purchase Value</th>
              <th class="text-end" data-i18n="current_market_value">Current Market Value</th>
              <th class="text-end" data-i18n="number_of_purchases">Number of Purchases</th>
              <th data-i18n="actions">Actions</th>
            </tr>
          </thead>
          <tbody>
  `;

  groupedGoldRows.forEach((grouped) => {
    html += `
            <tr>
              <td class="fixed-assets-card-title">${t("type_gold", "Gold")}</td>
              <td>
                <span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;" data-i18n="type_gold">${t("type_gold", "Gold")}</span>
              </td>
              <td>${grouped.purity_label}</td>
              <td class="text-end">${fmt(grouped.total_weight_grams)}</td>
              <td class="text-end">${fmt(grouped.total_purchase_value)}</td>
              <td class="text-end">
                <span style="color:#17a34a;font-weight:700">${fmt(grouped.total_current_market_value)}</span>
              </td>
              <td class="text-end">${fmtInt(grouped.purchases_count)}</td>
              <td class="d-flex gap-2">
                <button class="btn-icon" title="${t("view", "View")}" onclick="showGoldPurityGroupDetails('${grouped.purity_key}')"><i class="bi bi-eye"></i></button>
              </td>
            </tr>
    `;
  });

  nonGoldAssets.forEach((asset) => {
    const assetType = asset.asset_type || asset.type || FIXED_ASSET_TYPES.OTHER;
    const typeKey = fixedAssetTypeToI18nKey(assetType);

    html += `
            <tr>
              <td class="fixed-assets-card-title">${asset.name || "—"}</td>
              <td>
                <span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;" data-i18n="${typeKey}">${assetType}</span>
              </td>
              <td>—</td>
              <td class="text-end">—</td>
              <td class="text-end">${fmt(asset.purchase_price)}</td>
              <td class="text-end">
                <span style="color:#17a34a;font-weight:700">${fmt(asset.current_market_value)}</span>
              </td>
              <td class="text-end">1</td>
              <td class="d-flex gap-2">
                <button class="btn-icon" title="View" onclick="showFixedAssetDetails(${asset.id})"><i class="bi bi-eye"></i></button>
                <button class="btn-icon" title="Edit" onclick="showFixedAssetModal(${asset.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" title="Delete" onclick="deleteFixedAsset(${asset.id})"><i class="bi bi-trash"></i></button>
              </td>
            </tr>
    `;
  });

  html += `
          </tbody>
        </table>
      </div>
    </div>
  `;

  container.innerHTML = html;
  applyTranslations();
}
