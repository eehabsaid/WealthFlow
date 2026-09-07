"use strict";
// Vehicle/gold/other-asset "core details" tab HTML for the non-real-estate
// asset detail modal branch. Returns the pieces needed by
// buildAndShowNonRealEstateModal (non_real_estate_modal.js).

function buildNonRealEstateCoreTabParts(ctx) {
      const coreTabLabel = isVehicleAssetType(ctx.asset.asset_type)
        ? t("vehicle", "Vehicle")
        : isGoldAssetType(ctx.asset.asset_type)
          ? t("gold_details", "Gold Details")
          : t("details", "Details");

      const coreTabPane = isVehicleAssetType(ctx.asset.asset_type)
        ? `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="brand">Brand</span><span class="value">${ctx.vehicleDetails.brand || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="model">Model</span><span class="value">${ctx.vehicleDetails.model || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="year">Year</span><span class="value">${ctx.vehicleDetails.year || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="vin">VIN</span><span class="value">${ctx.vehicleDetails.vin || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="engine">Engine</span><span class="value">${ctx.vehicleDetails.engine || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="transmission">Transmission</span><span class="value">${ctx.vehicleDetails.transmission || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="fuel_type">Fuel Type</span><span class="value">${ctx.vehicleDetails.fuel_type || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="mileage">Mileage</span><span class="value">${ctx.vehicleDetails.mileage || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="plate_number">Plate Number</span><span class="value">${ctx.vehicleDetails.plate_number || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="color">Color</span><span class="value">${ctx.vehicleDetails.color || "-"}</span></div></div>
              </div>
            </div>
          </div>
        `
        : isGoldAssetType(ctx.asset.asset_type)
          ? `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="gold_type">Gold Type</span><span class="value">${ctx.goldDetails.gold_type || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="purity">Purity</span><span class="value">${ctx.goldDetails.purity || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="weight">Weight</span><span class="value">${ctx.goldDetails.weight || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="unit">Unit</span><span class="value">${ctx.goldDetails.unit || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="market_price">Market Price</span><span class="value">${fmt(ctx.goldDetails.market_price)}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_weight">Purchase Weight</span><span class="value">${ctx.goldDetails.purchase_weight || "-"}</span></div></div>
              </div>
            </div>
          </div>
        `
          : `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="category">Category</span><span class="value">${ctx.otherDetails.category || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="manufacturer">Manufacturer</span><span class="value">${ctx.otherDetails.manufacturer || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="model">Model</span><span class="value">${ctx.otherDetails.model || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="serial_number">Serial Number</span><span class="value">${ctx.otherDetails.serial_number || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="warranty_expiry">Warranty Expiry</span><span class="value">${ctx.otherDetails.warranty_expiry || "-"}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${ctx.otherDetails.notes || "-"}</span></div></div>
                <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="description">Description</span><span class="value">${ctx.otherDetails.description || "-"}</span></div></div>
              </div>
            </div>
          </div>
        `;

      const extraVehicleTabs = isVehicleAssetType(ctx.asset.asset_type)
        ? `
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-maintenance-tab" data-bs-toggle="tab" data-bs-target="#asset-maintenance-pane" type="button" role="tab" data-i18n="maintenance">Maintenance</button>
          </li>
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-insurance-tab" data-bs-toggle="tab" data-bs-target="#asset-insurance-pane" type="button" role="tab" data-i18n="insurance">Insurance</button>
          </li>
        `
        : "";

      const extraVehiclePanes = isVehicleAssetType(ctx.asset.asset_type)
        ? `
          <div class="tab-pane fade" id="asset-maintenance-pane" role="tabpanel" aria-labelledby="asset-maintenance-tab">
            <div class="row g-3">
              ${(ctx.maintenance.length ? ctx.maintenance : [{ date: "-", type: "-", cost: 0, notes: "-" }])
                .map(
                  (item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="date">Date</div><div>${formatDate(item.date) || "-"}</div></div><div><div class="small" data-i18n="type">Type</div><div>${item.type || "-"}</div></div><div><div class="small" data-i18n="cost">Cost</div><div>${fmt(item.cost)}</div></div><div><div class="small" data-i18n="notes">Notes</div><div>${item.notes || "-"}</div></div></div></div></div>
              `
                )
                .join("")}
            </div>
          </div>
          <div class="tab-pane fade" id="asset-insurance-pane" role="tabpanel" aria-labelledby="asset-insurance-tab">
            <div class="row g-3">
              ${(ctx.insurance.length
                ? ctx.insurance
                : [{ company: "-", policy_number: "-", expiry_date: "-", premium: 0 }]
              )
                .map(
                  (item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="company">Company</div><div>${item.company || "-"}</div></div><div><div class="small" data-i18n="policy_number">Policy Number</div><div>${item.policy_number || "-"}</div></div><div><div class="small" data-i18n="expiry_date">Expiry Date</div><div>${formatDate(item.expiry_date) || "-"}</div></div><div><div class="small" data-i18n="premium">Premium</div><div>${fmt(item.premium)}</div></div></div></div></div>
              `
                )
                .join("")}
            </div>
          </div>
        `
        : "";

      const extraValuationTab = !isGoldAssetType(ctx.asset.asset_type)
        ? `
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-valuation-tab" data-bs-toggle="tab" data-bs-target="#asset-valuation-pane" type="button" role="tab" data-i18n="valuation_history">Valuation History</button>
          </li>
        `
        : "";

      const extraValuationPane = !isGoldAssetType(ctx.asset.asset_type)
        ? `
          <div class="tab-pane fade" id="asset-valuation-pane" role="tabpanel" aria-labelledby="asset-valuation-tab">
            <div class="row g-3">
              ${(ctx.valuationHistory.length
                ? ctx.valuationHistory
                : [{ valuation_date: "-", market_value: 0, valuation_source: "-", notes: "-" }]
              )
                .map(
                  (item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="date">Date</div><div>${formatDate(item.valuation_date) || "-"}</div></div><div><div class="small" data-i18n="current_market_value">Market Value</div><div>${fmt(item.market_value)}</div></div><div><div class="small" data-i18n="valuation_source">Valuation Source</div><div>${item.valuation_source || "-"}</div></div><div><div class="small" data-i18n="notes">Notes</div><div>${item.notes || "-"}</div></div></div></div></div>
              `
                )
                .join("")}
            </div>
          </div>
        `
        : "";

  return {
    coreTabLabel,
    coreTabPane,
    extraVehicleTabs,
    extraVehiclePanes,
    extraValuationTab,
    extraValuationPane,
  };
}
