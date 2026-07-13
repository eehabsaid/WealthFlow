"use strict";
// showFixedAssetModal — full asset form modal builder
// This file is part of the fixed_assets module. Do not edit directly.

async function showFixedAssetModal(assetId = null, options = {}) {
  if (options?.returnPurityKey) {
    setGoldPurityReturnContext(options.returnPurityKey);
  } else {
    clearGoldPurityReturnContext();
  }

  const isEdit = assetId !== null;
  currentEditingAssetId = isEdit ? assetId : null;
  currentAssetHasPurchaseSync = false;
  const modalTitleKey = isEdit ? "edit_fixed_asset" : "add_fixed_asset";
  const modalTitleDefault = isEdit
    ? "Edit Asset Details"
    : "Register New Fixed Asset";

  const html = `
        <div class="modal-header">
            <h5 class="modal-title fixed-assets-heading" data-i18n="${modalTitleKey}">${modalTitleDefault}</h5>
            <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
        </div>
        <div class="modal-body" style="max-height: 75vh; overflow-y: auto; overflow-x: hidden; padding: 1.5rem;">
          <form id="fixedAssetForm">

              <ul class="nav nav-tabs mb-4" id="fixedAssetTabs" role="tablist">
                  <li class="nav-item" role="presentation">
                      <button class="nav-link active"
                              id="general-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#general-pane"
                              type="button"
                              role="tab"
                              aria-controls="general-pane"
                              aria-selected="true"
                              data-i18n="general">
                          General
                      </button>
                  </li>

                  <li class="nav-item" role="presentation">
                      <button class="nav-link"
                              id="property-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#property-pane"
                              type="button"
                              role="tab"
                              aria-controls="property-pane"
                              aria-selected="false"
                              data-i18n="property">
                          Property
                      </button>
                  </li>

                    <li class="nav-item d-none" role="presentation" id="vehicle-tab-item">
                      <button class="nav-link"
                          id="vehicle-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#vehicle-pane"
                          type="button"
                          role="tab"
                          aria-controls="vehicle-pane"
                          aria-selected="false"
                          data-i18n="vehicle">
                        Vehicle
                      </button>
                    </li>

                    <li class="nav-item d-none" role="presentation" id="gold-tab-item">
                      <button class="nav-link"
                          id="gold-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#gold-pane"
                          type="button"
                          role="tab"
                          aria-controls="gold-pane"
                          aria-selected="false"
                          data-i18n="gold_details">
                        Gold Details
                      </button>
                    </li>

                    <li class="nav-item d-none" role="presentation" id="other-details-tab-item">
                      <button class="nav-link"
                          id="other-details-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#other-details-pane"
                          type="button"
                          role="tab"
                          aria-controls="other-details-pane"
                          aria-selected="false"
                          data-i18n="details">
                        Details
                      </button>
                    </li>

                    <li class="nav-item" role="presentation">
                      <button class="nav-link"
                          id="photos-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#photos-pane"
                          type="button"
                          role="tab"
                          aria-controls="photos-pane"
                          aria-selected="false"
                          data-i18n="photos">
                        Photos
                      </button>
                    </li>

                  <li class="nav-item" role="presentation">
                      <button class="nav-link"
                              id="renovation-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#renovation-pane"
                              type="button"
                              role="tab"
                              aria-controls="renovation-pane"
                              aria-selected="false"
                              data-i18n="renovations">
                          Renovations
                      </button>
                  </li>

                        <li class="nav-item d-none" role="presentation" id="maintenance-tab-item">
                          <button class="nav-link"
                              id="maintenance-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#maintenance-pane"
                              type="button"
                              role="tab"
                              aria-controls="maintenance-pane"
                              aria-selected="false"
                              data-i18n="maintenance">
                            Maintenance
                          </button>
                        </li>

                        <li class="nav-item d-none" role="presentation" id="insurance-tab-item">
                          <button class="nav-link"
                              id="insurance-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#insurance-pane"
                              type="button"
                              role="tab"
                              aria-controls="insurance-pane"
                              aria-selected="false"
                              data-i18n="insurance">
                            Insurance
                          </button>
                        </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="furniture-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#furniture-pane"
                                type="button"
                                role="tab"
                                aria-controls="furniture-pane"
                                aria-selected="false"
                                data-i18n="furniture">
                              Furniture
                            </button>
                          </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="valuation-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#valuation-pane"
                                type="button"
                                role="tab"
                                aria-controls="valuation-pane"
                                aria-selected="false"
                                data-i18n="valuation_history">
                              Valuation History
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="mortgage-tab-item">
                            <button class="nav-link"
                                id="mortgage-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#mortgage-pane"
                                type="button"
                                role="tab"
                                aria-controls="mortgage-pane"
                                aria-selected="false"
                                data-i18n="mortgage">
                              Mortgage
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="rental-tab-item">
                            <button class="nav-link"
                                id="rental-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#rental-pane"
                                type="button"
                                role="tab"
                                aria-controls="rental-pane"
                                aria-selected="false"
                                data-i18n="rental">
                              Rental
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="sale-tab-item">
                            <button class="nav-link"
                                id="sale-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#sale-pane"
                                type="button"
                                role="tab"
                                aria-controls="sale-pane"
                                aria-selected="false"
                                data-i18n="sale">
                              Sale
                            </button>
                          </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="documents-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#documents-pane"
                                type="button"
                                role="tab"
                                aria-controls="documents-pane"
                                aria-selected="false"
                                data-i18n="documents_title">
                              Documents
                            </button>
                          </li>
              </ul>

              <div class="tab-content" id="fixedAssetTabsContent">

                  ${renderGeneralTab()}

                  ${renderPropertyTab()}

                  ${renderVehicleTab()}

                  ${renderGoldTab()}

                  ${renderOtherDetailsTab()}

                  ${renderPhotosTab()}

                  ${renderRenovationTab()}

                    ${renderFurnitureTab()}

                    ${renderValuationTab()}

                    ${renderMaintenanceTab()}

                    ${renderInsuranceTab()}

                    ${renderMortgageTab()}

                    ${renderRentalTab()}

                    ${renderSaleTab()}

                    ${renderDocumentsTab()}

              </div> <!-- End Tab Content -->

          </form>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="saveFixedAsset(${assetId})" data-i18n="save">Save</button>
        </div>
    `;

  showModal(html);
  applyTranslations();
  await populateGoldSettingsDropdowns();
  const propertyTab = document.getElementById("property-tab");
  const statusField = document.getElementById("fa_status");
  const salePriceField = document.getElementById("fa_sale_price");
  const sellingExpensesField = document.getElementById("fa_selling_expenses");
  const currentValueField = document.getElementById("fa_current_value");
  const monthlyRentField = document.getElementById("fa_monthly_rent");
  const remainingBalanceField = document.getElementById("fa_remaining_balance");
  const assetTypeField = document.getElementById("fa_type");
  const goldPurityField = document.getElementById("gd_purity");
  const goldUnitField = document.getElementById("gd_unit");

  if (statusField) {
    statusField.addEventListener("change", toggleSaleTabVisibility);
  }

  if (salePriceField) {
    salePriceField.addEventListener("input", updateNetSaleAmount);
  }

  if (sellingExpensesField) {
    sellingExpensesField.addEventListener("input", updateNetSaleAmount);
  }

  if (currentValueField) {
    currentValueField.addEventListener("input", () => {
      updateMortgageSummary();
      updateRentalSummary();
    });
  }

  if (monthlyRentField) {
    monthlyRentField.addEventListener("input", updateRentalSummary);
  }

  if (remainingBalanceField) {
    remainingBalanceField.addEventListener("input", updateMortgageSummary);
  }

  if (assetTypeField) {
    assetTypeField.addEventListener("change", toggleRealEstateDependentTabs);
  }

  if (goldPurityField) {
    goldPurityField.addEventListener("change", updateGoldValuation);
  }

  if (goldUnitField) {
    goldUnitField.addEventListener("input", updateGoldValuation);
  }

  if (window.DocumentManager) {
    window.DocumentManager.init({
      containerId: "fixedAssetDocumentManagerContainer",
      parentType: "fixed_asset",
      parentId: assetId,
      disabledMessage: t("documents_save_first", "Save this record first to manage documents."),
    });
  }

  await loadFixedAssetSyncDropdownData();
  resetPurchasePaymentsForm();
  addPurchasePaymentRow();
  propertyPhotos = [];
  renderPropertyPhotoGallery();
  ["acquisitionContainer", "renovationContainer", "furnitureContainer", "valuationContainer", "maintenanceContainer", "insuranceContainer"].forEach((id) => {
    const container = document.getElementById(id);
    if (container) container.innerHTML = "";
  });
  updateAcquisitionSummary();
  if (typeof updateRenovationSummary === "function") updateRenovationSummary();
  if (typeof updateFurnitureSummary === "function") updateFurnitureSummary();
  if (typeof updateValuationSummary === "function") updateValuationSummary();
  resetSaleForm();
  toggleSaleDepositBankField();
  resetMortgageForm();
  resetRentalForm();
  toggleSaleTabVisibility();
  toggleRealEstateDependentTabs();

  propertyTab.addEventListener("shown.bs.tab", function () {
    if (propertyMap) {
      setTimeout(() => {
        propertyMap.invalidateSize();
      }, 50);
    }
  });

  document
    .getElementById("btnLocateProperty")
    .addEventListener("click", locatePropertyOnMap);
  const refreshValuationButton = document.getElementById("btnRefreshPropertyValuation");
  if (refreshValuationButton) {
    refreshValuationButton.addEventListener("click", refreshPropertyValuation);
  }
  initializePropertyMap();
  if (isEdit) {
    await loadFixedAsset(assetId);
  } else {
    maybeRefreshPurchaseUsdRateOnLoad();
  }
}


function renderGeneralTab() {
  return `<!-- 1. GENERAL TAB PANE -->
                  <div class="tab-pane fade show active"
                      id="general-pane"
                      role="tabpanel"
                      aria-labelledby="general-tab">

                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                              <label class="form-label fixed-assets-section-title" data-i18n="asset_type">Asset Type</label>
                              <select class="form-select" id="fa_type" onchange="toggleRealEstateFields()" required>
                                  <option value="Real Estate" data-i18n="type_real_estate">Real Estate</option>
                                  <option value="Vehicles" data-i18n="type_vehicles">Vehicles</option>
                                  <option value="Gold" data-i18n="type_gold">Gold</option>
                                  <option value="Other Assets" data-i18n="type_other_assets">Other Assets</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                              <label class="form-label fixed-assets-section-title" data-i18n="asset_name">Asset Name</label>
                              <input type="text" class="form-control" id="fa_name" required>
                            </div>
                        </div>

                            <div class="row g-3 mb-3">
                              <div class="col-md-6">
                                <label class="form-label text-light" data-i18n="asset_status">Asset Status</label>
                                <select class="form-select" id="fa_status" required>
                                  <option value="Owned" data-i18n="owned">Owned</option>
                                  <option value="Sold" data-i18n="sold">Sold</option>
                                </select>
                              </div>
                            </div>

                        <div class="row g-3 mb-3">
                          <div class="col-md-3">
                            <label class="form-label text-light" data-i18n="purchase_currency">Purchase Currency</label>
                            <select class="form-select" id="fa_purchase_currency" onchange="handlePurchaseCurrencyChange()" required></select>
                          </div>
                          <div class="col-md-3">
                            <label class="form-label text-light" data-i18n="purchase_price_egp">Purchase Price</label>
                                <input type="number" step="0.01" class="form-control" oninput="updatePurchasePriceUSD()" id="fa_purchase_price" required>
                            </div>
                          <div class="col-md-3">
                                <label class="form-label text-light" data-i18n="purchase_usd_rate">USD Exchange Rate</label>
                            <div class="input-group">
                              <input type="number" step="0.00001" class="form-control" oninput="updatePurchasePriceUSD()" id="fa_purchase_usd_rate" required>
                              <button type="button" class="btn btn-outline-secondary" onclick="fillCurrentUsdRate()" data-i18n="current_rate_btn">Now</button>
                            </div>
                            </div>
                          <div class="col-md-3">
                                <label class="form-label text-light" data-i18n="purchase_price_usd">Purchase Price (USD)</label>
                                <input type="number" step="0.01" class="form-control" id="fa_purchase_price_usd" readonly>
                            </div>
                        </div>

                        <div class="row g-3 mb-3">
                            <div class="col-md-4">
                                <label class="form-label text-light" data-i18n="purchase_date">Purchase Date</label>
                                <input type="date" class="form-control" id="fa_purchase_date" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-light" data-i18n="current_market_value">Current Market Value</label>
                                <input type="number" step="0.01" class="form-control" id="fa_current_value" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-light" data-i18n="last_valuation_date">Last Valuation Date</label>
                                <input type="date" class="form-control" id="fa_last_valuation_date" required>
                            </div>
                        </div>

                        <div class="card border-0 shadow-sm bg-transparent mb-3">
                          <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                            <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="payment_information">Payment Information</h6>
                            <button type="button" class="btn btn-outline-primary btn-sm" onclick="addPurchasePaymentRow()" data-i18n="add_payment_source">+ Add Payment Source</button>
                          </div>
                          <div class="card-body px-0 pt-2">
                            <div id="purchasePaymentsContainer" class="w-100"></div>
                            <div class="small text-light mt-2" style="opacity:0.8;" data-i18n="purchase_payment_total_hint">Total payment sources must equal Purchase Price.</div>
                          </div>
                        </div>

                        <div class="row g-3 mb-3" id="valuation-source-row">
                            <div class="col-md-12">
                                <label class="form-label text-light" data-i18n="valuation_source">Valuation Source</label>
                                <select class="form-select" id="fa_val_source">
                                    <option value="Manual" data-i18n="val_manual">Manual Input</option>
                                    <option value="Automatic" data-i18n="val_automatic">System Synced</option>
                                </select>
                            </div>
                        </div>

                        <!-- FIXED: Notes is now nested exclusively here at the bottom of the General Tab -->
                        <div class="col-md-12">
                            <label class="form-label text-light" data-i18n="notes">Internal Notes</label>
                            <textarea class="form-control" id="fa_notes" rows="2"></textarea>
                        </div>

                  </div> <!-- End General Tab -->`;
}

function renderPropertyTab() {
  return `<!-- 2. PROPERTY TAB PANE -->
                  <div class="tab-pane fade"
                      id="property-pane"
                      role="tabpanel"
                      aria-labelledby="property-tab">

                        <div id="realEstateSection">
                            <h6 class="mb-3 font-weight-bold fixed-assets-section-title" style="font-size: 0.95rem;" data-i18n="real_estate_details">Real Estate Technical Specifications</h6>
                            
                            <div class="row g-3 mb-3">
                                <div class="col-sm-6 col-md-3"><input type="text" class="form-control" id="re_country" placeholder="Egypt" data-i18n-placeholder="country"></div>
                                <div class="col-sm-6 col-md-3"><input type="text" class="form-control" id="re_governorate" placeholder="Governorate" data-i18n-placeholder="governorate"></div>
                                <div class="col-sm-6 col-md-3"><input type="text" class="form-control" id="re_city" placeholder="City" data-i18n-placeholder="city"></div>
                                <div class="col-sm-6 col-md-3"><input type="text" class="form-control" id="re_district" placeholder="District" data-i18n-placeholder="district"></div>
                            </div>

                            <div class="row g-3 mb-3 align-items-end">
                                <div class="col-md-9">
                                    <input type="text" class="form-control" id="re_address" placeholder="Address Details" data-i18n-placeholder="address">
                                </div>
                                <div class="col-md-3">
                                    <button type="button" class="btn btn-primary w-100" id="btnLocateProperty" data-i18n="locate_on_map">Locate on Map</button>
                                </div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label small text-light" data-i18n="latitude">Latitude</label>
                                    <input type="number" step="0.000001" class="form-control" id="re_latitude" readonly>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small text-light" data-i18n="longitude">Longitude</label>
                                    <input type="number" step="0.000001" class="form-control" id="re_longitude" readonly>
                                </div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-12">
                                    <label class="form-label small text-light" data-i18n="property_location">Property Location</label>
                                    <div id="propertyMap" class="w-100" style="height:300px; border:1px solid var(--border-color); border-radius:8px;"></div>
                                    <small class="form-text text-light" style="opacity: 0.65;" data-i18n="map_click_instruction">Click anywhere on the map to select the property location.</small>
                                </div>
                            </div>

                            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
                              <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                                <div>
                                  <div style="font-weight:600;color:var(--text-secondary);" data-i18n="property_valuation">Property Valuation</div>
                                  <div style="font-size:12px;color:var(--text-muted);" data-i18n="property_valuation_desc">Automatic estimate is applied only when a configured provider can value this property.</div>
                                </div>
                                <button type="button" class="btn-primary-custom" id="btnRefreshPropertyValuation" data-i18n="refresh_property_valuation">Refresh Valuation</button>
                              </div>
                              <div class="row g-3">
                                <div class="col-md-4">
                                  <label class="form-label small text-light" data-i18n="last_estimated_market_price">Last Estimated Market Price</label>
                                  <input type="number" step="0.01" class="form-control" id="re_last_estimated_market_price" readonly>
                                </div>
                                <div class="col-md-4">
                                  <label class="form-label small text-light" data-i18n="last_valuation_date">Last Valuation Date</label>
                                  <input type="date" class="form-control" id="re_last_valuation_date" readonly>
                                </div>
                                <div class="col-md-4">
                                  <label class="form-label small text-light" data-i18n="valuation_provider">Valuation Provider</label>
                                  <input type="text" class="form-control" id="re_valuation_provider" readonly>
                                </div>
                              </div>
                            </div>

                            <hr class="my-4">
                            <div class="row g-3 mb-3">
                                <div class="col-sm-6 col-md-4"><label class="form-label small text-light" data-i18n="apt_area">Property Area (Sqm)</label><input type="number" class="form-control" id="re_area"></div>
                                <div class="col-sm-6 col-md-4"><label class="form-label small text-light" data-i18n="land_area">Land Plot Footprint (Sqm)</label><input type="number" class="form-control" id="re_land_area"></div>
                                <div class="col-6 col-md-2"><label class="form-label small text-light" data-i18n="rooms">Bedrooms</label><input type="number" class="form-control" id="re_rooms"></div>
                                <div class="col-6 col-md-2"><label class="form-label small text-light" data-i18n="bathrooms">Bathrooms</label><input type="number" class="form-control" id="re_bathrooms"></div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-6 col-md-3"><label class="form-label small text-light" data-i18n="floor">Floor Number</label><input type="number" class="form-control" id="re_floor"></div>
                                <div class="col-6 col-md-3"><label class="form-label small text-light" data-i18n="building_floors">Total Building Stories</label><input type="number" class="form-control" id="re_b_floors"></div>
                                <div class="col-6 col-md-3"><label class="form-label small text-light" data-i18n="building_year">Construction Year</label><input type="number" class="form-control" id="re_year"></div>
                                <div class="col-6 col-md-3"><label class="form-label small text-light" data-i18n="facades">Facade Orientation</label><input type="text" class="form-control" id="re_facades"></div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label small text-light" data-i18n="furnished_status">Furnished Status</label>
                                    <select class="form-select" id="re_furnished">
                                        <option value="Unfurnished" data-i18n="unfurnished">Unfurnished</option>
                                        <option value="Semi Furnished" data-i18n="semi_furnished">Semi Furnished</option>
                                        <option value="Fully Furnished" data-i18n="fully_furnished">Fully Furnished</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small text-light" data-i18n="finishing_level">Finishing Level Type</label>
                                    <select class="form-select" id="re_finishing">
                                        <option value="Shell & Core" data-i18n="shell_core">Shell & Core</option>
                                        <option value="Semi Finished" data-i18n="semi_finished">Semi Finished</option>
                                        <option value="Fully Finished" data-i18n="fully_finished">Fully Finished</option>
                                        <option value="Luxury Finished" data-i18n="luxury_finished">Luxury Finished</option>
                                    </select>
                                </div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label small d-block mb-2 text-light" data-i18n="utilities">Available Utilities</label>
                                <div class="fa-chip-check-list">
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_util_elec">
                                        <label class="form-check-label small text-light" for="re_util_elec" data-i18n="electricity">Electricity Grid</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_util_water">
                                        <label class="form-check-label small text-light" for="re_util_water" data-i18n="water">Water Line</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_util_gas">
                                        <label class="form-check-label small text-light" for="re_util_gas" data-i18n="gas">Natural Gas</label>
                                    </div>
                                </div>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small d-block mb-2 text-light" data-i18n="features">Structural Amenities</label>
                                <div class="fa-chip-check-list">
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_feat_elevator">
                                        <label class="form-check-label small text-light" for="re_feat_elevator" data-i18n="elevator">Elevator</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_feat_garage">
                                        <label class="form-check-label small text-light" for="re_feat_garage" data-i18n="garage">Garage</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_has_land_share">
                                        <label class="form-check-label small text-light" for="re_has_land_share" data-i18n="has_land_share">Land Share</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_feat_licensed">
                                        <label class="form-check-label small text-light" for="re_feat_licensed" data-i18n="licensed">Licensed</label>
                                    </div>
                                </div>
                                </div>
                            </div>

                            <div class="row g-3">
                                <div class="col-md-4">
                                    <label class="form-label small text-light" data-i18n="land_share">Undivided Land Share (Carat)</label>
                                    <input type="text" class="form-control" id="re_land_share">
                                </div>
                                <div class="col-md-8">
                                    <label class="form-label small text-light" data-i18n="description">Property Structural Description</label>
                                    <input type="text" class="form-control" id="re_description">
                                </div>
                            </div>

                            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-top:16px;">
                              <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                                <div>
                                  <span style="font-weight:600;color:var(--text-secondary);" data-i18n="acquisition_costs">Acquisition Costs</span>
                                  <span id="acquisition-count-badge" class="text-secondary font-weight-normal small ms-1"></span>
                                </div>
                                <button type="button" class="btn btn-outline-primary btn-sm" onclick="addAcquisitionRow({}, true)" data-i18n="add_acquisition">
                                  + Add Acquisition Cost
                                </button>
                              </div>
                              <div id="acquisitionSummaryStrip" class="furniture-summary-strip mb-3"></div>
                              <div id="acquisitionContainer" class="w-100"></div>
                            </div>
                        </div>
                        
                  </div> <!-- End Property Tab -->`;
}

function renderVehicleTab() {
  return `<div class="tab-pane fade"
                      id="vehicle-pane"
                      role="tabpanel"
                      aria-labelledby="vehicle-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                          <div class="card-body px-0 pt-2">
                            <div class="row g-3">
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="brand">Brand</label><input type="text" class="form-control" id="vd_brand"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="model">Model</label><input type="text" class="form-control" id="vd_model"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="year">Year</label><input type="number" class="form-control" id="vd_year"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="vin">VIN</label><input type="text" class="form-control" id="vd_vin"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="engine">Engine</label><input type="text" class="form-control" id="vd_engine"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="transmission">Transmission</label><input type="text" class="form-control" id="vd_transmission"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="fuel_type">Fuel Type</label><input type="text" class="form-control" id="vd_fuel_type"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="mileage">Mileage</label><input type="number" step="0.01" class="form-control" id="vd_mileage"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="plate_number">Plate Number</label><input type="text" class="form-control" id="vd_plate_number"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="vehicle_license_expiry">Vehicle License Expiry</label><input type="date" class="form-control" id="vd_license_expiry_date"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="color">Color</label><input type="text" class="form-control" id="vd_color"></div>
                            </div>
                          </div>
                        </div>

                  </div> <!-- End Vehicle Tab -->`;
}

function renderGoldTab() {
  return `<div class="tab-pane fade"
                      id="gold-pane"
                      role="tabpanel"
                      aria-labelledby="gold-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                          <div class="card-body px-0 pt-2">
                            <div class="row g-3">
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="gold_type">Gold Type</label><select class="form-select" id="gd_gold_type"></select></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="purity">Purity</label><select class="form-select" id="gd_purity"></select></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="weight">Weight</label><input type="number" step="0.0001" class="form-control" id="gd_weight" oninput="updateGoldValuation()"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="unit">Unit</label><input type="text" class="form-control" id="gd_unit" value="gram"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="market_price">Market Price</label><input type="number" step="0.0001" class="form-control" id="gd_market_price" readonly></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="cashback_per_gram">Cashback per Gram</label><input type="number" step="0.0001" class="form-control" id="gd_cashback_per_gram" value="0" readonly></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="purchase_weight">Purchase Weight</label><input type="number" step="0.0001" class="form-control" id="gd_purchase_weight"></div>
                              <div class="col-12"><small class="text-light" style="opacity:.75;" data-i18n="auto_calculated_from_gold_prices">Auto-calculated from Gold Prices module (SELL + USD/EGP).</small></div>
                            </div>
                          </div>
                        </div>

                  </div> <!-- End Gold Tab -->`;
}

function renderOtherDetailsTab() {
  return `<div class="tab-pane fade"
                      id="other-details-pane"
                      role="tabpanel"
                      aria-labelledby="other-details-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                          <div class="card-body px-0 pt-2">
                            <div class="row g-3">
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="category">Category</label><input type="text" class="form-control" id="od_category"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="manufacturer">Manufacturer</label><input type="text" class="form-control" id="od_manufacturer"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="model">Model</label><input type="text" class="form-control" id="od_model"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="serial_number">Serial Number</label><input type="text" class="form-control" id="od_serial_number"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="warranty_expiry">Warranty Expiry</label><input type="date" class="form-control" id="od_warranty_expiry"></div>
                              <div class="col-md-12"><label class="form-label text-light" data-i18n="description">Description</label><textarea class="form-control" id="od_description" rows="2"></textarea></div>
                              <div class="col-md-12"><label class="form-label text-light" data-i18n="notes">Notes</label><textarea class="form-control" id="od_notes" rows="2"></textarea></div>
                            </div>
                          </div>
                        </div>

                  </div> <!-- End Other Details Tab -->`;
}

function renderPhotosTab() {
  return `<div class="tab-pane fade"
                      id="photos-pane"
                      role="tabpanel"
                      aria-labelledby="photos-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                          <div class="card-body px-0 pt-2">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                              <h5 class="mb-0 fixed-assets-section-title" data-i18n="property_photos">Photo Gallery</h5>
                              <button type="button" id="btnUploadPropertyPhoto" class="btn btn-primary btn-sm">
                                <i class="bi bi-upload me-1"></i><span data-i18n="upload_photo">Upload Photo</span>
                              </button>
                            </div>
                            <input type="file" id="propertyPhotoInput" accept="image/*" multiple style="display:none;">
                            <div id="propertyPhotoGallery" class="row g-3"></div>
                          </div>
                        </div>

                  </div> <!-- End Photos Tab -->`;
}

function renderRenovationTab() {
  return `<div class="tab-pane fade"
                      id="renovation-pane"
                      role="tabpanel"
                      aria-labelledby="renovation-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title">
                            <span data-i18n="renovations">Renovations</span>
                            <span id="renovation-count-badge" class="text-secondary font-weight-normal small ms-1"></span>
                          </h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addRenovationRow({}, true)" data-i18n="add_renovation">
                            + Add Renovation
                          </button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="renovationSummaryStrip" class="furniture-summary-strip"></div>
                          <div id="renovationContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Renovation Tab -->`;
}

function renderFurnitureTab() {
  return `<div class="tab-pane fade"
                      id="furniture-pane"
                      role="tabpanel"
                      aria-labelledby="furniture-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title">
                            <span data-i18n="furniture">Furniture</span>
                            <span id="furniture-count-badge" class="text-secondary font-weight-normal small ms-1"></span>
                          </h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addFurnitureRow({}, true)" data-i18n="add_furniture">
                            + Add Furniture
                          </button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="furnitureSummaryStrip" class="furniture-summary-strip"></div>
                          <div id="furnitureContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Furniture Tab -->`;
}

function renderValuationTab() {
  return `<div class="tab-pane fade"
                      id="valuation-pane"
                      role="tabpanel"
                      aria-labelledby="valuation-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title">
                            <span data-i18n="valuation_history">Valuation History</span>
                            <span id="valuation-count-badge" class="text-secondary font-weight-normal small ms-1"></span>
                          </h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addValuationRow({}, true)" data-i18n="add_valuation">
                            + Add Valuation
                          </button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="valuationSummaryStrip" class="furniture-summary-strip"></div>
                          <div id="valuationContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Valuation Tab -->`;
}

function renderMaintenanceTab() {
  return `<div class="tab-pane fade"
                      id="maintenance-pane"
                      role="tabpanel"
                      aria-labelledby="maintenance-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="maintenance">Maintenance</h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addMaintenanceRow()" data-i18n="add_maintenance">+ Add Maintenance</button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="maintenanceContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Maintenance Tab -->`;
}

function renderInsuranceTab() {
  return `<div class="tab-pane fade"
                      id="insurance-pane"
                      role="tabpanel"
                      aria-labelledby="insurance-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="insurance">Insurance</h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addInsuranceRow()" data-i18n="add_insurance">+ Add Insurance</button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="insuranceContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Insurance Tab -->`;
}

function renderMortgageTab() {
  return `<div class="tab-pane fade"
                      id="mortgage-pane"
                      role="tabpanel"
                      aria-labelledby="mortgage-tab">

                      <div class="card border-0 shadow-sm bg-transparent item-card open">
                        <div class="card-header d-flex justify-content-between align-items-center px-3 bg-transparent border-0" style="border-bottom: 1px solid var(--border-color) !important;">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="mortgage">Mortgage</h6>
                          <button type="button" class="btn btn-danger btn-sm" onclick="deleteMortgageDetails()" data-i18n="delete">Delete</button>
                        </div>
                        <div class="card-body px-3 pt-3 pb-3">
                          <div class="field-grid">
                            <div class="field span-2">
                              <label class="form-label" data-i18n="loan_amount">Loan Amount</label>
                              <input type="number" step="0.01" class="form-control" id="fa_loan_amount">
                            </div>
                            <div class="field span-2">
                              <label class="form-label" data-i18n="remaining_balance">Remaining Balance</label>
                              <input type="number" step="0.01" class="form-control" id="fa_remaining_balance" oninput="updateMortgageSummary()">
                            </div>
                            <div class="field">
                              <label class="form-label" data-i18n="monthly_installment">Monthly Installment</label>
                              <input type="number" step="0.01" class="form-control" id="fa_monthly_installment">
                            </div>
                            <div class="field">
                              <label class="form-label" data-i18n="interest_rate">Interest Rate</label>
                              <input type="number" step="0.0001" class="form-control" id="fa_interest_rate">
                            </div>
                            <div class="field span-2">
                              <label class="form-label" data-i18n="net_equity">Net Equity</label>
                              <input type="number" step="0.01" class="form-control" id="fa_net_equity" readonly>
                            </div>
                            <div class="field span-2">
                              <label class="form-label" data-i18n="start_date">Start Date</label>
                              <input type="date" class="form-control" id="fa_mortgage_start_date">
                            </div>
                            <div class="field span-2">
                              <label class="form-label" data-i18n="end_date">End Date</label>
                              <input type="date" class="form-control" id="fa_mortgage_end_date">
                            </div>
                          </div>
                        </div>
                      </div>

                    </div> <!-- End Mortgage Tab -->`;
}

function renderRentalTab() {
  return `<div class="tab-pane fade"
                      id="rental-pane"
                      role="tabpanel"
                      aria-labelledby="rental-tab">

                      <div class="card border-0 shadow-sm bg-transparent item-card open">
                        <div class="card-header d-flex justify-content-between align-items-center px-3 bg-transparent border-0" style="border-bottom: 1px solid var(--border-color) !important;">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="rental">Rental</h6>
                          <button type="button" class="btn btn-danger btn-sm" onclick="deleteRentalDetails()" data-i18n="delete">Delete</button>
                        </div>
                        <div class="card-body px-3 pt-3 pb-3">
                          <div class="field-grid">
                            <div class="field">
                              <label class="form-label" data-i18n="monthly_rent">Monthly Rent</label>
                              <input type="number" step="0.01" class="form-control" id="fa_monthly_rent" oninput="updateRentalSummary()">
                            </div>
                            <div class="field">
                              <label class="form-label" data-i18n="annual_rent">Annual Rent</label>
                              <input type="number" step="0.01" class="form-control" id="fa_annual_rent" readonly>
                            </div>
                            <div class="field span-2">
                              <label class="form-label" data-i18n="rental_yield">Rental Yield</label>
                              <input type="number" step="0.01" class="form-control" id="fa_rental_yield" readonly>
                            </div>
                            <div class="field">
                              <label class="form-label" data-i18n="occupancy_rate">Occupancy Rate</label>
                              <input type="number" step="0.01" class="form-control" id="fa_occupancy_rate">
                            </div>
                            <div class="field span-3">
                              <label class="form-label" data-i18n="tenant_name_optional">Tenant Name (Optional)</label>
                              <input type="text" class="form-control" id="fa_tenant_name">
                            </div>
                            <div class="field span-2">
                              <label class="form-label" data-i18n="contract_start">Contract Start</label>
                              <input type="date" class="form-control" id="fa_contract_start">
                            </div>
                            <div class="field span-2">
                              <label class="form-label" data-i18n="contract_end">Contract End</label>
                              <input type="date" class="form-control" id="fa_contract_end">
                            </div>
                            <div class="field span-4">
                              <label class="form-label" data-i18n="rental_notes">Rental Notes</label>
                              <textarea class="form-control" id="fa_rental_notes" rows="3"></textarea>
                            </div>
                          </div>
                        </div>
                      </div>

                    </div> <!-- End Rental Tab -->`;
}

function renderSaleTab() {
  return `<div class="tab-pane fade"
                      id="sale-pane"
                      role="tabpanel"
                      aria-labelledby="sale-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-body px-0 pt-2">
                          <div class="row g-3 mb-3">
                            <div class="col-md-6">
                              <label class="form-label text-light" data-i18n="sale_date">Sale Date</label>
                              <input type="date" class="form-control" id="fa_sale_date">
                            </div>
                            <div class="col-md-6">
                              <label class="form-label text-light" data-i18n="sale_price_egp">Sale Price (EGP)</label>
                              <input type="number" step="0.01" class="form-control" id="fa_sale_price">
                            </div>
                          </div>

                          <div class="row g-3 mb-3">
                            <div class="col-md-6">
                              <label class="form-label text-light" data-i18n="selling_expenses_egp">Selling Expenses (EGP)</label>
                              <input type="number" step="0.01" class="form-control" id="fa_selling_expenses">
                            </div>
                            <div class="col-md-6">
                              <label class="form-label text-light" data-i18n="net_sale_amount">Net Sale Amount</label>
                              <input type="number" step="0.01" class="form-control" id="fa_net_sale_amount" readonly>
                            </div>
                          </div>

                          <div class="row g-3 mb-3">
                            <div class="col-md-4">
                              <label class="form-label text-light" data-i18n="currency">Currency</label>
                              <select class="form-select" id="fa_deposit_currency"></select>
                            </div>
                            <div class="col-md-4">
                              <label class="form-label text-light" data-i18n="deposit_method">Deposit Method</label>
                              <select class="form-select" id="fa_deposit_method" onchange="toggleSaleDepositBankField()"></select>
                            </div>
                            <div class="col-md-4" id="faDepositBankWrap">
                              <label class="form-label text-light" data-i18n="bank">Bank</label>
                              <select class="form-select" id="fa_deposit_bank"></select>
                            </div>
                          </div>

                          <div class="row g-3">
                            <div class="col-md-12">
                              <label class="form-label text-light" data-i18n="sale_notes">Sale Notes</label>
                              <textarea class="form-control" id="fa_sale_notes" rows="3"></textarea>
                            </div>
                          </div>
                        </div>
                      </div>

                    </div> <!-- End Sale Tab -->`;
}

function renderDocumentsTab() {
  return `<div class="tab-pane fade"
                      id="documents-pane"
                      role="tabpanel"
                      aria-labelledby="documents-tab">

                      <div id="fixedAssetDocumentManagerContainer"></div>

                    </div> <!-- End Documents Tab -->`;
}
