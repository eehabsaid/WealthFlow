"use strict";
// Gold purity group details modal.
// Part of the fixed_assets module (split from the former monolithic list.js,
// 200-line rule). Do not edit directly.

function showGoldPurityGroupDetails(purityKey) {
  const normalizedPurity = normalizeGoldPurity(purityKey || "24k");
  setGoldPurityReturnContext(normalizedPurity);
  const purchases = normalizeFixedAssetsData(fixedAssetsState.assets).filter((asset) => {
    if (!isGoldAssetType(asset.asset_type || asset.type)) return false;
    const assetPurity = normalizeGoldPurity(asset?.gold_details?.purity || asset?.purity || "24k");
    return assetPurity === normalizedPurity;
  });

  if (!purchases.length) {
    showToast(
      t("no_gold_purchases_for_purity", "No gold purchases found for this purity."),
      "warning"
    );
    return;
  }

  const rows = purchases
    .sort((a, b) => String(b.purchase_date || "").localeCompare(String(a.purchase_date || "")))
    .map((asset) => {
      const weight = parseFloat(asset?.gold_details?.weight) || 0;
      const unit = asset?.gold_details?.unit || "gram";
      return `
        <tr>
          <td>${asset.name || "—"}</td>
          <td>${asset.purchase_date || "—"}</td>
          <td>${fmt(weight)} ${unit}</td>
          <td class="text-end">${fmt(asset.purchase_price)}</td>
          <td class="text-end">${fmt(asset.current_market_value)}</td>
          <td class="d-flex gap-2">
            <button class="btn-icon" title="${t("view", "View")}" onclick="openGoldPurchaseDetails(${asset.id}, '${normalizedPurity}')"><i class="bi bi-eye"></i></button>
            <button class="btn-icon" title="${t("edit", "Edit")}" onclick="openGoldPurchaseEditor(${asset.id}, '${normalizedPurity}')"><i class="bi bi-pencil"></i></button>
            <button class="btn-icon del" title="${t("delete", "Delete")}" onclick="deleteFixedAssetFromGoldGroup(${asset.id}, '${normalizedPurity}')"><i class="bi bi-trash"></i></button>
          </td>
        </tr>
      `;
    })
    .join("");

  const html = `
    <div class="modal-header">
      <h5 class="modal-title" data-i18n="gold_purity_group_details">${t("gold_purity_group_details", "Gold Purity Details")}: ${normalizedPurity.toUpperCase()}</h5>
      <button type="button" class="btn-close btn-close-white" onclick="clearGoldPurityReturnContext(); closeModal()"></button>
    </div>
    <div class="modal-body">
      <div style="margin-bottom:12px;font-weight:600;color:var(--text-secondary);">
        <span data-i18n="number_of_purchases">${t("number_of_purchases", "Number of Purchases")}</span>: ${fmtInt(purchases.length)}
      </div>
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th data-i18n="asset_name">${t("asset_name", "Asset Name")}</th>
              <th data-i18n="purchase_date">${t("purchase_date", "Purchase Date")}</th>
              <th data-i18n="weight">${t("weight", "Weight")}</th>
              <th class="text-end" data-i18n="purchase_price_egp">${t("purchase_price_egp", "Purchase Price")}</th>
              <th class="text-end" data-i18n="current_market_value">${t("current_market_value", "Current Market Value")}</th>
              <th data-i18n="actions">${t("actions", "Actions")}</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    </div>
  `;

  showModal(html);
  applyTranslations();
}
