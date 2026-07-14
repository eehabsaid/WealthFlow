"use strict";
// showFixedAssetDetails — read-only asset detail modal
// This file is part of the fixed_assets module. Do not edit directly.

async function showFixedAssetDetails(assetId, options = {}) {
  if (options?.returnPurityKey) {
    setGoldPurityReturnContext(options.returnPurityKey);
  } else {
    clearGoldPurityReturnContext();
  }

  showLoading();

  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/`);

    if (!response.ok) throw new Error("Failed to load asset");

    const asset = await response.json();

    const photos = asset.photos || [];
    const renovations = asset.renovations || [];
    const furniture = asset.furniture || [];
    const valuationHistory = asset.valuation_history || [];
    const maintenance = asset.maintenance || [];
    const insurance = asset.insurance || [];
    const vehicleDetails = asset.vehicle_details || {};
    const goldDetails = asset.gold_details || {};
    const otherDetails = asset.other_asset_details || {};
    const sale = asset.sale || null;
    const mortgage = asset.mortgage || null;
    const rental = asset.rental || null;
    const realEstate = asset.real_estate || {};
    const utilitiesBadges = [
      realEstate.electricity
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-plug-fill me-1"></i><span data-i18n="electricity">Electricity</span></span>'
        : '',
      realEstate.water
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-droplet-fill me-1"></i><span data-i18n="water">Water</span></span>'
        : '',
      realEstate.gas
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-fire me-1"></i><span data-i18n="gas">Gas</span></span>'
        : '',
    ].filter(Boolean).join('');
    const featuresBadges = [
      realEstate.elevator
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-building me-1"></i><span data-i18n="elevator">Elevator</span></span>'
        : '',
      realEstate.garage
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-car-front-fill me-1"></i><span data-i18n="garage">Garage</span></span>'
        : '',
      realEstate.has_land_share
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-tree-fill me-1"></i><span data-i18n="has_land_share">Land Share</span></span>'
        : '',
      realEstate.licensed
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-shield-lock-fill me-1"></i><span data-i18n="licensed">Licensed</span></span>'
        : '',
    ].filter(Boolean).join('');
    const gainValue = asset.gain_loss !== undefined ? asset.gain_loss : ((asset.current_market_value || 0) - (asset.purchase_price || 0));
    const gainClass = gainValue >= 0 ? 'text-success' : 'text-danger';
    let assetViewMap = null;

    if (!isRealEstateAssetType(asset.asset_type)) {
      const coreTabLabel = isVehicleAssetType(asset.asset_type)
        ? t("vehicle", "Vehicle")
        : isGoldAssetType(asset.asset_type)
          ? t("gold_details", "Gold Details")
          : t("details", "Details");

      const coreTabPane = isVehicleAssetType(asset.asset_type)
        ? `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="brand">Brand</span><span class="value">${vehicleDetails.brand || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="model">Model</span><span class="value">${vehicleDetails.model || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="year">Year</span><span class="value">${vehicleDetails.year || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="vin">VIN</span><span class="value">${vehicleDetails.vin || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="engine">Engine</span><span class="value">${vehicleDetails.engine || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="transmission">Transmission</span><span class="value">${vehicleDetails.transmission || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="fuel_type">Fuel Type</span><span class="value">${vehicleDetails.fuel_type || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="mileage">Mileage</span><span class="value">${vehicleDetails.mileage || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="plate_number">Plate Number</span><span class="value">${vehicleDetails.plate_number || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="color">Color</span><span class="value">${vehicleDetails.color || '-'}</span></div></div>
              </div>
            </div>
          </div>
        `
        : isGoldAssetType(asset.asset_type)
          ? `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="gold_type">Gold Type</span><span class="value">${goldDetails.gold_type || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="purity">Purity</span><span class="value">${goldDetails.purity || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="weight">Weight</span><span class="value">${goldDetails.weight || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="unit">Unit</span><span class="value">${goldDetails.unit || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="market_price">Market Price</span><span class="value">${fmt(goldDetails.market_price)}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_weight">Purchase Weight</span><span class="value">${goldDetails.purchase_weight || '-'}</span></div></div>
              </div>
            </div>
          </div>
        `
          : `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="category">Category</span><span class="value">${otherDetails.category || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="manufacturer">Manufacturer</span><span class="value">${otherDetails.manufacturer || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="model">Model</span><span class="value">${otherDetails.model || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="serial_number">Serial Number</span><span class="value">${otherDetails.serial_number || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="warranty_expiry">Warranty Expiry</span><span class="value">${otherDetails.warranty_expiry || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${otherDetails.notes || '-'}</span></div></div>
                <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="description">Description</span><span class="value">${otherDetails.description || '-'}</span></div></div>
              </div>
            </div>
          </div>
        `;

      const extraVehicleTabs = isVehicleAssetType(asset.asset_type)
        ? `
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-maintenance-tab" data-bs-toggle="tab" data-bs-target="#asset-maintenance-pane" type="button" role="tab" data-i18n="maintenance">Maintenance</button>
          </li>
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-insurance-tab" data-bs-toggle="tab" data-bs-target="#asset-insurance-pane" type="button" role="tab" data-i18n="insurance">Insurance</button>
          </li>
        `
        : "";

      const extraVehiclePanes = isVehicleAssetType(asset.asset_type)
        ? `
          <div class="tab-pane fade" id="asset-maintenance-pane" role="tabpanel" aria-labelledby="asset-maintenance-tab">
            <div class="row g-3">
              ${(maintenance.length ? maintenance : [{ date: "-", type: "-", cost: 0, notes: "-" }]).map((item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="date">Date</div><div>${item.date || '-'}</div></div><div><div class="small" data-i18n="type">Type</div><div>${item.type || '-'}</div></div><div><div class="small" data-i18n="cost">Cost</div><div>${fmt(item.cost)}</div></div><div><div class="small" data-i18n="notes">Notes</div><div>${item.notes || '-'}</div></div></div></div></div>
              `).join("")}
            </div>
          </div>
          <div class="tab-pane fade" id="asset-insurance-pane" role="tabpanel" aria-labelledby="asset-insurance-tab">
            <div class="row g-3">
              ${(insurance.length ? insurance : [{ company: "-", policy_number: "-", expiry_date: "-", premium: 0 }]).map((item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="company">Company</div><div>${item.company || '-'}</div></div><div><div class="small" data-i18n="policy_number">Policy Number</div><div>${item.policy_number || '-'}</div></div><div><div class="small" data-i18n="expiry_date">Expiry Date</div><div>${item.expiry_date || '-'}</div></div><div><div class="small" data-i18n="premium">Premium</div><div>${fmt(item.premium)}</div></div></div></div></div>
              `).join("")}
            </div>
          </div>
        `
        : "";

      const extraValuationTab = !isGoldAssetType(asset.asset_type)
        ? `
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-valuation-tab" data-bs-toggle="tab" data-bs-target="#asset-valuation-pane" type="button" role="tab" data-i18n="valuation_history">Valuation History</button>
          </li>
        `
        : "";

      const extraValuationPane = !isGoldAssetType(asset.asset_type)
        ? `
          <div class="tab-pane fade" id="asset-valuation-pane" role="tabpanel" aria-labelledby="asset-valuation-tab">
            <div class="row g-3">
              ${(valuationHistory.length ? valuationHistory : [{ valuation_date: "-", market_value: 0, valuation_source: "-", notes: "-" }]).map((item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="date">Date</div><div>${item.valuation_date || '-'}</div></div><div><div class="small" data-i18n="current_market_value">Market Value</div><div>${fmt(item.market_value)}</div></div><div><div class="small" data-i18n="valuation_source">Valuation Source</div><div>${item.valuation_source || '-'}</div></div><div><div class="small" data-i18n="notes">Notes</div><div>${item.notes || '-'}</div></div></div></div></div>
              `).join("")}
            </div>
          </div>
        `
        : "";

      const html = `
      <div class="modal-header border-0 pb-0">
          <h5 class="modal-title fixed-assets-heading" data-i18n="asset_details">Asset Details</h5>
          <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
      </div>
      <div class="modal-body asset-modal-body p-0">
        <div class="p-4">
          <div class="asset-detail-header mb-4">
            <h3 class="asset-title mb-1 fixed-assets-heading">${asset.name || '-'}</h3>
            <span class="badge rounded-pill asset-type-badge" data-i18n="${fixedAssetTypeToI18nKey(asset.asset_type)}">${asset.asset_type || '-'}</span>
          </div>
          <ul class="nav nav-pills nav-fill mb-4 asset-detail-tabs" role="tablist">
            <li class="nav-item" role="presentation"><button class="nav-link active" id="asset-general-tab" data-bs-toggle="tab" data-bs-target="#asset-general-pane" type="button" role="tab" data-i18n="general">General</button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-core-tab" data-bs-toggle="tab" data-bs-target="#asset-core-pane" type="button" role="tab">${coreTabLabel}</button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-photos-tab" data-bs-toggle="tab" data-bs-target="#asset-photos-pane" type="button" role="tab" data-i18n="photos">Photos</button></li>
            ${extraVehicleTabs}
            ${extraValuationTab}
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-sale-tab" data-bs-toggle="tab" data-bs-target="#asset-sale-pane" type="button" role="tab" data-i18n="sale">Sale</button></li>
          </ul>
          <div class="tab-content" id="assetDetailsTabsContent">
            <div class="tab-pane fade show active" id="asset-general-pane" role="tabpanel" aria-labelledby="asset-general-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                <div class="row g-3">
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_price_egp">Purchase Price</span><span class="value">${fmt(asset.purchase_price)}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="current_market_value">Current Market Value</span><span class="value ${gainClass}">${fmt(asset.current_market_value)}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_date">Purchase Date</span><span class="value">${asset.purchase_date || '-'}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="gain_loss">Gain / Loss</span><span class="value ${gainClass}">${fmt(gainValue)}</span></div></div>
                  <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${asset.notes || '-'}</span></div></div>
                </div>
              </div></div>
            </div>
            <div class="tab-pane fade" id="asset-core-pane" role="tabpanel" aria-labelledby="asset-core-tab">${coreTabPane}</div>
            <div class="tab-pane fade" id="asset-photos-pane" role="tabpanel" aria-labelledby="asset-photos-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                <div id="assetMainPhotoContainer" class="asset-main-photo-container mb-3">
                  ${photos.length ? `<img id="assetMainPhoto" src="${photos[0].url}" alt="Asset photo" class="img-fluid" style="max-height:100%;max-width:100%;cursor:pointer;" />` : `<div class="text-center" data-i18n="no_property_photos">No photos available</div>`}
                </div>
                <div class="asset-photo-grid">${photos.length ? photos.slice(1).map((photo, index) => `<button type="button" class="btn btn-sm asset-photo-thumbnail p-0" data-url="${photo.url}" aria-label="Photo ${index + 2}"><img src="${photo.url}" alt="Thumbnail ${index + 2}" /></button>`).join("") : ""}</div>
              </div></div>
            </div>
            ${extraVehiclePanes}
            ${extraValuationPane}
            <div class="tab-pane fade" id="asset-sale-pane" role="tabpanel" aria-labelledby="asset-sale-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                ${sale ? `<div class="row g-3"><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="sale_date">Sale Date</span><span class="value">${sale.sale_date || '-'}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="sale_price_egp">Sale Price</span><span class="value">${fmt(sale.sale_price)}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="selling_expenses_egp">Selling Expenses</span><span class="value">${fmt(sale.selling_expenses)}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="net_sale_amount">Net Sale Amount</span><span class="value">${fmt(sale.net_sale_amount)}</span></div></div><div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${sale.notes || '-'}</span></div></div></div>` : `<div class="text-center" data-i18n="no_data">No data available</div>`}
              </div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer"><button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="close">Close</button></div>
      <div id="assetPhotoOverlay" class="position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-90 d-none" style="z-index:2000;"><div class="d-flex h-100 align-items-center justify-content-center"><img id="assetFullscreenImage" src="" alt="Fullscreen asset photo" class="img-fluid rounded" style="max-height:90%; max-width:90%;" /></div></div>
      `;

      showModal(html);
      applyTranslations();

      const mainPhoto = document.getElementById("assetMainPhoto");
      const photoOverlay = document.getElementById("assetPhotoOverlay");
      const fullscreenImage = document.getElementById("assetFullscreenImage");
      if (mainPhoto) {
        mainPhoto.addEventListener("click", () => {
          fullscreenImage.src = mainPhoto.src;
          photoOverlay?.classList.remove("d-none");
        });
      }
      photoOverlay?.addEventListener("click", () => {
        photoOverlay.classList.add("d-none");
        fullscreenImage.src = "";
      });

      const assetPhotoThumbnails = document.querySelectorAll(".asset-photo-thumbnail");
      assetPhotoThumbnails.forEach((thumb) => {
        thumb.addEventListener("click", (e) => {
          const url = e.currentTarget.dataset.url;
          const mainImg = document.getElementById("assetMainPhoto");
          if (mainImg) mainImg.src = url;
          assetPhotoThumbnails.forEach((item) => item.classList.remove("active"));
          e.currentTarget.classList.add("active");
        });
      });
      hideLoading();
      return;
    }

    const html = `
    <div class="modal-header border-0 pb-0">
        <h5 class="modal-title fixed-assets-heading" data-i18n="asset_details">Asset Details</h5>
        <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
    </div>

    <div class="modal-body asset-modal-body p-0">
        <div class="p-4">
            <div class="asset-detail-header mb-4">
                <div class="d-flex flex-column flex-lg-row gap-3 align-items-start">
                    <div class="asset-header-icon d-flex align-items-center justify-content-center">
                        <i class="bi bi-building"></i>
                    </div>
                    <div class="flex-fill">
                        <div class="d-flex flex-column flex-sm-row justify-content-between gap-3 align-items-start align-items-sm-center">
                            <div>
                                <h3 class="asset-title mb-1 fixed-assets-heading">${asset.name || '-'}</h3>
                                <span class="badge rounded-pill asset-type-badge" data-i18n="${fixedAssetTypeToI18nKey(asset.asset_type)}">${asset.asset_type || '-'}</span>
                            </div>
                            <div class="text-sm-end">
                                <div class="small asset-label" data-i18n="current_market_value">Current Market Value</div>
                                <div class="asset-value-large ${gainClass}">${fmt(asset.current_market_value)}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-4 g-3 mb-4">
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="purchase_price_egp">Purchase Price</div>
                        <div class="asset-summary-value">${fmt(asset.purchase_price)}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="purchase_date">Purchase Date</div>
                        <div class="asset-summary-value">${asset.purchase_date || '-'}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="gain_loss">Gain / Loss</div>
                        <div class="asset-summary-value ${gainClass}">${fmt(gainValue)}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="last_valuation_date">Last Valuation Date</div>
                        <div class="asset-summary-value">${asset.last_valuation_date || '-'}</div>
                    </div>
                </div>
                ${mortgage ? `
                <div class="col">
                  <div class="asset-summary-card h-100">
                    <div class="asset-summary-label" data-i18n="net_equity">Net Equity</div>
                    <div class="asset-summary-value">${fmt(mortgage.net_equity)}</div>
                  </div>
                </div>
                ` : ''}
                ${rental ? `
                <div class="col">
                  <div class="asset-summary-card h-100">
                    <div class="asset-summary-label" data-i18n="rental_yield">Rental Yield</div>
                    <div class="asset-summary-value">${fmtpresent(rental.rental_yield)}%</div>
                  </div>
                </div>
                ` : ''}
            </div>

            <ul class="nav nav-pills nav-fill mb-4 asset-detail-tabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="asset-general-tab" data-bs-toggle="tab" data-bs-target="#asset-general-pane" type="button" role="tab" aria-controls="asset-general-pane" aria-selected="true" data-i18n="general">General</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-property-tab" data-bs-toggle="tab" data-bs-target="#asset-property-pane" type="button" role="tab" aria-controls="asset-property-pane" aria-selected="false" data-i18n="property">Property</button>
                </li>
              <li class="nav-item" role="presentation">
                <button class="nav-link" id="asset-photos-tab" data-bs-toggle="tab" data-bs-target="#asset-photos-pane" type="button" role="tab" aria-controls="asset-photos-pane" aria-selected="false" data-i18n="photos">Photos</button>
              </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-renovation-tab" data-bs-toggle="tab" data-bs-target="#asset-renovation-pane" type="button" role="tab" aria-controls="asset-renovation-pane" aria-selected="false" data-i18n="renovations">Renovations</button>
                </li>
                ${isRealEstateAssetType(asset.asset_type) ? `
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-acquisition-tab" data-bs-toggle="tab" data-bs-target="#asset-acquisition-pane" type="button" role="tab" aria-controls="asset-acquisition-pane" aria-selected="false" data-i18n="acquisition_costs">Acquisition Costs</button>
                </li>
                ` : ''}
                ${furniture.length ? `
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-furniture-tab" data-bs-toggle="tab" data-bs-target="#asset-furniture-pane" type="button" role="tab" aria-controls="asset-furniture-pane" aria-selected="false" data-i18n="furniture">Furniture</button>
                </li>
                ` : ''}
                ${valuationHistory.length ? `
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-valuation-tab" data-bs-toggle="tab" data-bs-target="#asset-valuation-pane" type="button" role="tab" aria-controls="asset-valuation-pane" aria-selected="false" data-i18n="valuation_history">Valuation History</button>
                </li>
                ` : ''}
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-mortgage-tab" data-bs-toggle="tab" data-bs-target="#asset-mortgage-pane" type="button" role="tab" aria-controls="asset-mortgage-pane" aria-selected="false" data-i18n="mortgage">Mortgage</button>
                </li>
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-rental-tab" data-bs-toggle="tab" data-bs-target="#asset-rental-pane" type="button" role="tab" aria-controls="asset-rental-pane" aria-selected="false" data-i18n="rental">Rental</button>
                </li>
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-sale-tab" data-bs-toggle="tab" data-bs-target="#asset-sale-pane" type="button" role="tab" aria-controls="asset-sale-pane" aria-selected="false" data-i18n="sale">Sale</button>
                </li>
            </ul>

            <div class="tab-content" id="assetDetailsTabsContent">
                <div class="tab-pane fade show active" id="asset-general-pane" role="tabpanel" aria-labelledby="asset-general-tab">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="general_information">General Information</h6>
                                                          
                                    <div class="row mb-2"><div class="col-5 fixed-assets-section-title" data-i18n="asset_type">Asset Type</div><div class="col-7">${asset.asset_type || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5 fixed-assets-section-title" data-i18n="asset_name">Asset Name</div><div class="col-7">${asset.name || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_date">Purchase Date</div><div class="col-7">${asset.purchase_date || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="valuation_source">Valuation Source</div><div class="col-7">${asset.valuation_source || '-'}</div></div>
                                    <div class="row"><div class="col-5" data-i18n="notes">Notes</div><div class="col-7">${asset.notes || '-'}</div></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="valuation_summary">Valuation Summary</h6>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_price_egp">Purchase Price</div><div class="col-7 fw-bold">${fmt(asset.purchase_price)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_price_usd">Purchase Price (USD)</div><div class="col-7 fw-bold">${fmt(asset.purchase_price_usd)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="acquisition_costs_egp">Acquisition Costs</div><div class="col-7 fw-bold">${fmt(asset.total_acquisition_costs || 0)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="renovation_costs_egp">Renovation Costs</div><div class="col-7 fw-bold">${fmt(asset.total_renovation_costs || 0)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="total_investment_egp">Total Investment</div><div class="col-7 fw-bold">${fmt(asset.total_investment || asset.purchase_price)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="current_market_value">Current Market Value</div><div class="col-7 fw-bold">${fmt(asset.current_market_value)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="last_valuation_date">Last Valuation Date</div><div class="col-7">${asset.last_valuation_date || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="gain_loss">Gain / Loss</div><div class="col-7 fw-bold ${gainClass}">${fmt(gainValue)}</div></div>
                                    <div class="row"><div class="col-5" data-i18n="gain_percent">Gain (%)</div><div class="col-7 fw-bold ${gainClass}">${(asset.total_investment || asset.purchase_price) ? fmtpresent((gainValue / (asset.total_investment || asset.purchase_price)) * 100) + '%' : '-'}</div></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="asset-property-pane" role="tabpanel" aria-labelledby="asset-property-tab">
                    <div class="row g-3">
                        <div class="col-xl-7">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="property_details">Property Details</h6>
                                    <div class="row row-cols-1 row-cols-sm-2 row-cols-xl-3 g-3">
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="country">Country</span><span class="value">${asset.real_estate?.country || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="governorate">Governorate</span><span class="value">${asset.real_estate?.governorate || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="city">City</span><span class="value">${asset.real_estate?.city || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="district">District</span><span class="value">${asset.real_estate?.district || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="address">Address</span><span class="value">${asset.real_estate?.address || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="apt_area">Property Area</span><span class="value">${asset.real_estate?.apartment_area || '-'} m²</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="land_area">Land Area</span><span class="value">${asset.real_estate?.land_area || '-'} m²</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="rooms">Bedrooms</span><span class="value">${asset.real_estate?.rooms || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="bathrooms">Bathrooms</span><span class="value">${asset.real_estate?.bathrooms || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="floor">Floor Number</span><span class="value">${asset.real_estate?.floor || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="building_floors">Total Building Floors</span><span class="value">${asset.real_estate?.building_floors || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="building_year">Construction Year</span><span class="value">${asset.real_estate?.building_year || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="facades">Facade</span><span class="value">${asset.real_estate?.facades || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="furnished_status">Furnished Status</span><span class="value">${asset.real_estate?.furnished_status || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="finishing_level">Finishing Level</span><span class="value">${asset.real_estate?.finishing_level || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="land_share">Land Share</span><span class="value">${asset.real_estate?.land_share || '-'}</span></div></div>
                                    </div>
                                    <div class="asset-attribute-row mt-3"><span class="label" data-i18n="description">Description</span><span class="value">${asset.real_estate?.description || '-'}</span></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-xl-5">
                            <div class="row g-3">
                                <div class="col-12">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="location">Location</h6>
                                            <div id="assetPropertyMap" class="asset-main-photo-container" style="height:280px;"></div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="utilities">Utilities</h6>
                                            <div class="d-flex flex-wrap gap-2">
                                              ${utilitiesBadges || `<span class="small" style="color:var(--text-secondary);" data-i18n="no_data">No data available</span>`}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="features">Features</h6>
                                            <div class="d-flex flex-wrap gap-2">
                                              ${featuresBadges || `<span class="small" style="color:var(--text-secondary);" data-i18n="no_data">No data available</span>`}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="asset-photos-pane" role="tabpanel" aria-labelledby="asset-photos-tab">
                  <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                    <div class="card-body p-4">
                      <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="property_photos">Photo Gallery</h6>
                      <div id="assetMainPhotoContainer" class="asset-main-photo-container mb-3" style="justify-content:center;">
                        ${photos.length ? `<img id="assetMainPhoto" src="${photos[0].url}" alt="Asset photo" class="img-fluid" style="max-height:100%;max-width:100%;cursor:pointer;" />` : `<div class="text-center" data-i18n="no_property_photos">No photos available</div>`}
                      </div>
                      <div class="asset-photo-grid">
                        ${photos.length ? photos.slice(1).map((photo, index) => `
                          <button type="button" class="btn btn-sm asset-photo-thumbnail p-0" data-url="${photo.url}" aria-label="Photo ${index + 2}">
                            <img src="${photo.url}" alt="Thumbnail ${index + 2}" />
                          </button>
                        `).join('') : ''}
                      </div>
                    </div>
                  </div>
                </div>
                <div class="tab-pane fade" id="asset-renovation-pane" role="tabpanel" aria-labelledby="asset-renovation-tab">
                    <div class="row g-3">
                        ${renovations.length ? renovations.map((r) => `
                            <div class="col-md-6">
                                <div class="asset-renovation-card h-100">
                                    <div class="d-flex justify-content-between gap-3">
                                        <div>
                                            <div class="small mb-2" data-i18n="date">Date</div>
                                            <div class="fw-semibold">${r.date || '-'}</div>
                                            <div class="small mt-2" data-i18n="category">Category</div>
                                            <div data-i18n-prefix="renovation_" data-i18n-value="${(r.category || '').toLowerCase().replace(/ & /g, '_').replace(/ /g, '_')}">${r.category || '-'}</div>
                                        </div>
                                        <div class="text-end">
                                            <div class="small mb-2" data-i18n="amount_usd">Amount USD</div>
                                            <div class="fw-semibold">${fmt(r.amount_usd)}</div>
                                            <div class="small mt-3" data-i18n="amount_egp">Amount</div>
                                            <div class="fw-semibold">${fmt(r.amount_egp)}</div>
                                        </div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="description">Description</div>
                                        <div>${r.description || '-'}</div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="notes">Notes</div>
                                        <div>${r.notes || '-'}</div>
                                    </div>
                                </div>
                            </div>
                        `).join('') : `
                            <div class="col-12">
                                <div class="text-center py-5" data-i18n="no_renovations">No renovations registered.</div>
                            </div>
                        `}
                        ${renovations.length ? `
                        <div class="col-12">
                            <div class="asset-renovation-card asset-renovation-summary" style="padding: 16px;">
                                <div class="d-flex flex-column gap-2" style="width: 100%;">
                                    
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="total_renovation_cost_usd">Total Renovation Cost USD</div>
                                        <div class="text-end fw-semibold">
                                            $${fmt(renovations.reduce((sum, r) => sum + (parseFloat(r.amount_usd) || 0), 0))}
                                        </div>
                                    </div>

                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="amount_egp">Amount</div>
                                        <div class="text-end fw-semibold">
                                            ${fmt(renovations.reduce((sum, r) => sum + (parseFloat(r.amount_egp) || 0), 0))} <span data-i18n="EGP">EGP</span>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                ${isRealEstateAssetType(asset.asset_type) ? `
                <div class="tab-pane fade" id="asset-acquisition-pane" role="tabpanel" aria-labelledby="asset-acquisition-tab">
                    <div class="row g-3">
                        ${(asset.acquisition_costs || []).length ? asset.acquisition_costs.map((c) => `
                            <div class="col-md-6">
                                <div class="asset-renovation-card h-100">
                                    <div class="d-flex justify-content-between gap-3">
                                        <div>
                                            <div class="small mb-2" data-i18n="date">Date</div>
                                            <div class="fw-semibold">${c.date || '-'}</div>
                                            <div class="small mt-2" data-i18n="category">Category</div>
                                            <div data-i18n-prefix="acquisition_" data-i18n-value="${(c.category || '').toLowerCase().replace(/ & /g, '_').replace(/ /g, '_')}">${c.category || '-'}</div>
                                        </div>
                                        <div class="text-end">
                                            <div class="small mb-2" data-i18n="amount_usd">Amount USD</div>
                                            <div class="fw-semibold">${fmt(c.amount_usd)}</div>
                                            <div class="small mt-3" data-i18n="amount_egp">Amount</div>
                                            <div class="fw-semibold">${fmt(c.amount_egp)}</div>
                                        </div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="description">Description</div>
                                        <div>${c.description || '-'}</div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="notes">Notes</div>
                                        <div>${c.notes || '-'}</div>
                                    </div>
                                </div>
                            </div>
                        `).join('') : `
                            <div class="col-12">
                                <div class="text-center py-5" data-i18n="no_acquisition_costs">No acquisition costs registered.</div>
                            </div>
                        `}
                        ${(asset.acquisition_costs || []).length ? `
                        <div class="col-12">
                            <div class="asset-renovation-card asset-renovation-summary" style="padding: 16px;">
                                <div class="d-flex flex-column gap-2" style="width: 100%;">
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="total_acquisition_cost_usd">Total Acquisition Cost USD</div>
                                        <div class="text-end fw-semibold">
                                            $${fmt(asset.acquisition_costs.reduce((sum, c) => sum + (parseFloat(c.amount_usd) || 0), 0))}
                                        </div>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="amount_egp">Amount</div>
                                        <div class="text-end fw-semibold">
                                            ${fmt(asset.acquisition_costs.reduce((sum, c) => sum + (parseFloat(c.amount_egp) || 0), 0))} <span data-i18n="EGP">EGP</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                ` : ''}
                  ${furniture.length ? `
                  <div class="tab-pane fade" id="asset-furniture-pane" role="tabpanel" aria-labelledby="asset-furniture-tab">
                    <div class="row g-3">
                      ${furniture.map((item) => `
                        <div class="col-md-6">
                          <div class="asset-renovation-card h-100">
                            <div class="d-flex justify-content-between gap-3">
                              <div>
                                <div class="small mb-1" data-i18n="item_name">Item Name</div>
                                <div class="fw-semibold">${item.name || '-'}</div>
                              </div>
                              <div class="text-end">
                                <div class="small mb-1" data-i18n="amount_egp">Amount</div>
                                <div class="fw-semibold">${fmt(item.amount_egp * parseInt(item.quantity) || 1)}</div>
                              </div>
                            </div>
                            <div class="mt-3 d-flex justify-content-between gap-3">
                               <div><span class="small" data-i18n="category">Category</span><div data-i18n-prefix="furniture_" data-i18n-value="${(item.category || '').toLowerCase().replace(/ & /g, '_').replace(/ /g, '_')}">${item.category || '-'}</div></div>
                               <div><span class="small" data-i18n="quantity">Quantity</span><div>${item.quantity || '-'}</div></div>
                              <div><span class="small" data-i18n="purchase_date">Purchase Date</span><div>${item.purchase_date || '-'}</div></div>
                            </div>
                            <div class="mt-3"><div class="small mb-1" data-i18n="notes">Notes</div><div>${item.notes || '-'}</div></div>
                          </div>
                        </div>
                      `).join('')}
                      <div class="col-12">
                            <div class="asset-renovation-card asset-renovation-summary" style="padding: 16px;">
                                <div class="d-flex flex-column gap-2" style="width: 100%;">
                                    
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="total_furniture_cost_usd">Total Furniture Cost USD</div>
                                        <div class="text-end fw-semibold">
                                            $${fmt(furniture.reduce((sum, item) => {
                                                const qty = parseInt(item.quantity) || 1;
                                                const rate = parseFloat(item.usd_rate) || parseFloat(asset.purchase_usd_rate) || 0;
                                                if (rate > 0) {
                                                    return sum + (((parseFloat(item.amount_egp) || 0) * qty) / rate);
                                                } else {
                                                    return sum + (parseFloat(item.amount_usd) || 0);
                                                }
                                            }, 0))}
                                        </div>
                                    </div>

                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="amount_egp">Amount</div>
                                        <div class="text-end fw-semibold">
                                            ${fmt(furniture.reduce((sum, item) => sum + ((parseFloat(item.amount_egp) || 0) * (parseInt(item.quantity) || 1)), 0))} <span data-i18n="EGP">EGP</span>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </div>
                    </div>
                  </div>
                  ` : ''}
                  ${valuationHistory.length ? `
                  <div class="tab-pane fade" id="asset-valuation-pane" role="tabpanel" aria-labelledby="asset-valuation-tab">
                    <div class="row g-3">
                      ${valuationHistory.map((item) => `
                        <div class="col-12">
                          <div class="asset-renovation-card">
                            <div class="d-flex flex-column flex-md-row justify-content-between gap-3">
                              <div>
                                <div class="small mb-1" data-i18n="date">Date</div>
                                <div class="fw-semibold">${item.valuation_date || '-'}</div>
                              </div>
                              <div>
                                <div class="small mb-1" data-i18n="valuation_source">Valuation Source</div>
                                <div>${item.valuation_source || '-'}</div>
                              </div>
                              <div class="text-md-end">
                                <div class="small mb-1" data-i18n="current_market_value">Current Market Value</div>
                                <div class="fw-semibold">${fmt(item.market_value)}</div>
                              </div>
                            </div>
                            <div class="mt-3"><div class="small mb-1" data-i18n="notes">Notes</div><div>${item.notes || '-'}</div></div>
                          </div>
                        </div>
                      `).join('')}
                    </div>
                  </div>
                  ` : ''}
                  <div class="tab-pane fade" id="asset-mortgage-pane" role="tabpanel" aria-labelledby="asset-mortgage-tab">
                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                      <div class="card-body p-4">
                        ${mortgage ? `
                          <div class="row g-3">
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="loan_amount">Loan Amount</span><span class="value">${fmt(mortgage.loan_amount)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="remaining_balance">Remaining Balance</span><span class="value">${fmt(mortgage.remaining_balance)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="monthly_installment">Monthly Installment</span><span class="value">${fmt(mortgage.monthly_installment)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="interest_rate">Interest Rate</span><span class="value">${fmtpresent(mortgage.interest_rate)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="start_date">Start Date</span><span class="value">${mortgage.start_date || '-'}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="end_date">End Date</span><span class="value">${mortgage.end_date || '-'}</span></div></div>
                            <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="net_equity">Net Equity</span><span class="value">${fmt(mortgage.net_equity)}</span></div></div>
                          </div>
                        ` : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`}
                      </div>
                    </div>
                  </div>

                  <div class="tab-pane fade" id="asset-rental-pane" role="tabpanel" aria-labelledby="asset-rental-tab">
                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                      <div class="card-body p-4">
                        ${rental ? `
                          <div class="row g-3">
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="monthly_rent">Monthly Rent</span><span class="value">${fmt(rental.monthly_rent)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="annual_rent">Annual Rent</span><span class="value">${fmt(rental.annual_rent)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="occupancy_rate">Occupancy Rate</span><span class="value">${fmtpresent(rental.occupancy_rate)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="rental_yield">Rental Yield</span><span class="value">${fmtpresent(rental.rental_yield)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="tenant_name_optional">Tenant Name</span><span class="value">${rental.tenant_name || '-'}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="contract_start">Contract Start</span><span class="value">${rental.contract_start || '-'}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="contract_end">Contract End</span><span class="value">${rental.contract_end || '-'}</span></div></div>
                            <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${rental.notes || '-'}</span></div></div>
                          </div>
                        ` : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`}
                      </div>
                    </div>
                  </div>

                  <div class="tab-pane fade" id="asset-sale-pane" role="tabpanel" aria-labelledby="asset-sale-tab">
                    <div class="row g-3">
                      <div class="col-md-6">
                        <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                          <div class="card-body p-4">
                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="sale_information">Sale Information</h6>
                            ${sale ? `
                              <div class="row mb-2"><div class="col-5" data-i18n="sale_date">Sale Date</div><div class="col-7">${sale.sale_date || '-'}</div></div>
                              <div class="row mb-2"><div class="col-5" data-i18n="sale_price_egp">Sale Price</div><div class="col-7 fw-bold">${fmt(sale.sale_price)}</div></div>
                              <div class="row mb-2"><div class="col-5" data-i18n="selling_expenses_egp">Selling Expenses</div><div class="col-7">${fmt(sale.selling_expenses)}</div></div>
                              <div class="row"><div class="col-5" data-i18n="net_sale_amount">Net Sale Amount</div><div class="col-7 fw-bold">${fmt(sale.net_sale_amount)}</div></div>
                            ` : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`}
                          </div>
                        </div>
                      </div>
                      <div class="col-md-6">
                        <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                          <div class="card-body p-4">
                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="notes">Notes</h6>
                            <div>${sale?.notes || '-'}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
            </div>
            <div id="assetPhotoOverlay" class="position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-90 d-none" style="z-index:2000;">
                <div class="d-flex h-100 align-items-center justify-content-center">
                    <img id="assetFullscreenImage" src="" alt="Fullscreen asset photo" class="img-fluid rounded" style="max-height:90%; max-width:90%;" />
                </div>
            </div>
        </div>
    </div>

    <div class="modal-footer">
        <button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="close">Close</button>
    </div>
`;

    showModal(html);

    applyTranslations();

    const mainPhoto = document.getElementById('assetMainPhoto');
    const photoOverlay = document.getElementById('assetPhotoOverlay');
    const fullscreenImage = document.getElementById('assetFullscreenImage');

    if (mainPhoto) {
      mainPhoto.addEventListener('click', () => {
        fullscreenImage.src = mainPhoto.src;
        photoOverlay.classList.remove('d-none');
      });
    }

    photoOverlay?.addEventListener('click', () => {
      photoOverlay.classList.add('d-none');
      fullscreenImage.src = '';
    });

    const assetPhotoThumbnails = document.querySelectorAll('.asset-photo-thumbnail');
    assetPhotoThumbnails.forEach((thumb, index) => {
      thumb.addEventListener('click', (e) => {
        const url = e.currentTarget.dataset.url;
        const mainImg = document.getElementById('assetMainPhoto');
        if (mainImg) mainImg.src = url;
        assetPhotoThumbnails.forEach((item) => item.classList.remove('active'));
        e.currentTarget.classList.add('active');
      });
    });

    const propertyLatitude = parseFloat(asset.real_estate?.latitude);
    const propertyLongitude = parseFloat(asset.real_estate?.longitude);

    if (!Number.isNaN(propertyLatitude) && !Number.isNaN(propertyLongitude)) {
      assetViewMap = L.map('assetPropertyMap', {
        dragging: false,
        touchZoom: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        zoomControl: false,
        tap: false,
      }).setView([propertyLatitude, propertyLongitude], 14);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(assetViewMap);

      L.marker([propertyLatitude, propertyLongitude], { interactive: false }).addTo(assetViewMap);
      setTimeout(() => assetViewMap.invalidateSize(), 200);
    }

    const assetPropertyTab = document.getElementById('asset-property-tab');
    if (assetPropertyTab && assetViewMap) {
      assetPropertyTab.addEventListener('shown.bs.tab', () => {
        setTimeout(() => assetViewMap.invalidateSize(), 50);
      });
    }

    document.querySelectorAll('#assetDetailsTabsContent .card').forEach((card) => {
      card.style.background = 'var(--bg-secondary)';
      card.style.color = 'var(--text-primary)';
    });

    document.querySelectorAll('#assetDetailsTabsContent').forEach((el) => {
      el.style.color = 'var(--text-secondary)';
    });
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

