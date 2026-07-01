"use strict";

let propertyMap = null;
let propertyMarker = null;
let propertyPhotos = [];
let currentEditingAssetId = null;

// ════════════════════════════════════════════════════════════════════════════
// DATA FETCHING & ROUTING
// ════════════════════════════════════════════════════════════════════════════

async function fetchAndRenderFixedAssets() {
  showLoading();
  try {
    const response = await fetch("/api/fixed-assets/");
    if (!response.ok) throw new Error("Failed to load fixed assets");
    const data = await response.json();
    renderFixedAssetsList(data);
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

function renderFixedAssets() {
  const target = document.getElementById("main-content");
  if (!target) return;

  target.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-4 pb-2" style="border-bottom: 1px solid var(--border-color);">
            <h3 class="m-0 font-weight-bold" data-i18n="fixed_assets">Fixed Assets</h3>
            <button class="btn-primary-custom" onclick="showFixedAssetModal()">
                <i class="bi bi-plus-lg"></i> <span data-i18n="add_new_asset">Add Asset</span>
            </button>
        </div>
        <div id="fixedAssetsContainer"></div>
    `;

  setTimeout(() => {
    fetchAndRenderFixedAssets();
  }, 0);
}

// ════════════════════════════════════════════════════════════════════════════
// LIST RENDERING (TABLE VIEW)
// ════════════════════════════════════════════════════════════════════════════

function renderFixedAssetsList(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  let assetsArray = [];
  if (Array.isArray(assets)) {
    assetsArray = assets;
  } else if (assets && typeof assets === "object") {
    if (Array.isArray(assets.data)) assetsArray = assets.data;
    else if (Array.isArray(assets.results)) assetsArray = assets.results;
    else if (Array.isArray(assets.assets)) assetsArray = assets.assets;
    else if (Array.isArray(assets.fixed_assets))
      assetsArray = assets.fixed_assets;
  }

  if (!assetsArray || assetsArray.length === 0) {
    container.innerHTML = `
            <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
                <div class="display-5 text-muted mb-3">🏢</div>
                <h4 class="mt-2" data-i18n="no_fixed_assets">No Fixed Assets Registered</h4>
                <p class="text-muted small mb-4" data-i18n="no_fixed_assets_desc">You haven't added any fixed assets or properties to your tracker portfolio yet.</p>
                <button class="btn btn-sm btn-primary-custom" onclick="showFixedAssetModal()">
                    <i class="bi bi-plus-lg"></i> <span data-i18n="add_first_asset">Register Your First Asset</span>
                </button>
            </div>
        `;
    if (typeof applyTranslations === "function") applyTranslations();
    return;
  }

  let html = `
  <div style="background:var(--bg-secondary);
              border:1px solid var(--border-color);
              border-radius:12px;
              overflow:visible">

      <div class="table-container">

          <table class="data-table">

              <thead>
                  <tr>
                      <th data-i18n="asset_name">Asset Name</th>
                      <th data-i18n="asset_type">Asset Type</th>
                      <th data-i18n="purchase_date">Purchase Date</th>
                      <th class="text-end" data-i18n="purchase_price_egp">Purchase Price (EGP)</th>
                      <th class="text-end" data-i18n="current_market_value">Current Market Value</th>
                      <th data-i18n="actions">Actions</th>
                  </tr>
              </thead>

              <tbody>
  `;

  assetsArray.forEach((asset) => {
    const assetType = asset.asset_type || asset.type || "Other";
    const typeKey = `type_${assetType.toLowerCase()}`;

    html += `
            <tr>
                <td>${asset.name || "—"}</td>
                <td>
                    <span
                        style="
                            background:rgba(26,110,245,.15);
                            color:var(--accent-primary);
                            padding:2px 8px;
                            border-radius:10px;
                            font-size:11px;
                            font-weight:700;
                        "
                        data-i18n="${typeKey}">
                        ${assetType}
                    </span>
                </td>
                <td>${asset.purchase_date || "—"}</td>
                <td class="text-end">
                    ${fmt(asset.purchase_price)}
                </td>
                <td class="text-end">
                    <span style="color:#17a34a;font-weight:700">
                        ${fmt(asset.current_market_value)}
                    </span>
                </td>
                <td class="d-flex gap-2">

                  <button class="btn-icon"
                      title="View"
                      onclick="showFixedAssetDetails(${asset.id})">
                      <i class="bi bi-eye"></i>
                  </button>

                  <button class="btn-icon"
                      title="Edit"
                      onclick="showFixedAssetModal(${asset.id})">
                      <i class="bi bi-pencil"></i>
                  </button>

                  <button class="btn-icon del"
                      title="Delete"
                      onclick="deleteFixedAsset(${asset.id})">
                      <i class="bi bi-trash"></i>
                  </button>

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

// ════════════════════════════════════════════════════════════════════════════
// MODALS & ACTIONS
// ════════════════════════════════════════════════════════════════════════════

async function showFixedAssetModal(assetId = null) {
  const isEdit = assetId !== null;
  const modalTitleKey = isEdit ? "edit_fixed_asset" : "add_fixed_asset";
  const modalTitleDefault = isEdit
    ? "Edit Asset Details"
    : "Register New Fixed Asset";

  const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${modalTitleKey}">${modalTitleDefault}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
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
              </ul>

              <div class="tab-content" id="fixedAssetTabsContent">

                  <!-- 1. GENERAL TAB PANE -->
                  <div class="tab-pane fade show active"
                      id="general-pane"
                      role="tabpanel"
                      aria-labelledby="general-tab">

                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <label class="form-label text-light" data-i18n="asset_name">Asset Name</label>
                                <input type="text" class="form-control" id="fa_name" required>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-light" data-i18n="asset_type">Asset Type</label>
                                <select class="form-select" id="fa_type" onchange="toggleRealEstateFields()" required>
                                    <option value="Apartment" data-i18n="type_apartment">Apartment</option>
                                    <option value="Villa" data-i18n="type_villa">Villa</option>
                                    <option value="Land" data-i18n="type_land">Land</option>
                                    <option value="Shop" data-i18n="type_shop">Shop</option>
                                    <option value="Office" data-i18n="type_office">Office</option>
                                    <option value="Car" data-i18n="type_car">Car</option>
                                    <option value="Other" data-i18n="type_other">Other</option>
                                </select>
                            </div>
                        </div>

                        <div class="row g-3 mb-3">
                            <div class="col-md-4">
                                <label class="form-label text-light" data-i18n="purchase_price_egp">Purchase Price (EGP)</label>
                                <input type="number" step="0.01" class="form-control" oninput="updatePurchasePriceUSD()" id="fa_purchase_price" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-light" data-i18n="purchase_usd_rate">USD Exchange Rate</label>
                                <input type="number" step="0.0001" class="form-control" oninput="updatePurchasePriceUSD()" id="fa_purchase_usd_rate" required>
                            </div>
                            <div class="col-md-4">
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

                        <div class="row g-3 mb-3">
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

                  </div> <!-- End General Tab -->

                  <!-- 2. PROPERTY TAB PANE -->
                  <div class="tab-pane fade"
                      id="property-pane"
                      role="tabpanel"
                      aria-labelledby="property-tab">

                        <div id="realEstateSection">
                            <h6 class="mb-3 font-weight-bold text-light" style="font-size: 0.95rem;" data-i18n="real_estate_details">Real Estate Technical Specifications</h6>
                            
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

                            <hr class="my-4">

                            <div class="mb-3">

                                <div class="d-flex justify-content-between align-items-center mb-3">

                                    <h5 class="mb-0"
                                        data-i18n="property_photos">
                                        Property Photos
                                    </h5>

                                    <button
                                        type="button"
                                        id="btnUploadPropertyPhoto"
                                        class="btn btn-primary btn-sm">

                                        <i class="bi bi-upload me-1"></i>

                                        <span data-i18n="upload_photo">
                                            Upload Photo
                                        </span>

                                    </button>

                                </div>

                                <input
                                    type="file"
                                    id="propertyPhotoInput"
                                    accept="image/*"
                                    multiple
                                    style="display:none;">

                                <div id="propertyPhotoGallery" class="row g-3">

                                    

                                </div>

                            </div>
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
                                    <div class="form-check form-check-inline">
                                        <input class="form-check-input" type="checkbox" id="re_util_elec">
                                        <label class="form-check-label small text-light" for="re_util_elec" data-i18n="electricity">Electricity Grid</label>
                                    </div>
                                    <div class="form-check form-check-inline">
                                        <input class="form-check-input" type="checkbox" id="re_util_water">
                                        <label class="form-check-label small text-light" for="re_util_water" data-i18n="water">Water Line</label>
                                    </div>
                                    <div class="form-check form-check-inline">
                                        <input class="form-check-input" type="checkbox" id="re_util_gas">
                                        <label class="form-check-label small text-light" for="re_util_gas" data-i18n="gas">Natural Gas</label>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small d-block mb-2 text-light" data-i18n="features">Structural Amenities</label>
                                    <div class="form-check form-check-inline">
                                        <input class="form-check-input" type="checkbox" id="re_feat_elevator">
                                        <label class="form-check-label small text-light" for="re_feat_elevator" data-i18n="elevator">Elevator</label>
                                    </div>
                                    <div class="form-check form-check-inline">
                                        <input class="form-check-input" type="checkbox" id="re_feat_garage">
                                        <label class="form-check-label small text-light" for="re_feat_garage" data-i18n="garage">Garage</label>
                                    </div>
                                    <div class="form-check form-check-inline">
                                        <input class="form-check-input" type="checkbox" id="re_has_land_share">
                                        <label class="form-check-label small text-light" for="re_has_land_share" data-i18n="has_land_share">Land Share</label>
                                    </div>
                                    <div class="form-check form-check-inline">
                                        <input class="form-check-input" type="checkbox" id="re_feat_licensed">
                                        <label class="form-check-label small text-light" for="re_feat_licensed" data-i18n="licensed">Licensed</label>
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
                        </div>
                        
                  </div> <!-- End Property Tab -->

                  <!-- 3. RENOVATION TAB PANE -->
                  <div class="tab-pane fade"
                      id="renovation-pane"
                      role="tabpanel"
                      aria-labelledby="renovation-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                            <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                                <h6 class="mb-0 font-weight-bold" style="color: var(--text-primary) !important;" data-i18n="renovation_history">Renovation History</h6>
                                <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#renovationCollapse">
                                    <i class="bi bi-chevron-down"></i>
                                </button>
                            </div>

                            <div class="collapse show" id="renovationCollapse">
                                <div class="card-body px-0 pt-2">
                                    <div id="renovationContainer" class="w-100"></div>
                                    <button type="button" class="btn btn-outline-primary btn-sm mt-2" onclick="addRenovationRow()" data-i18n="add_renovation">
                                        + Add Renovation
                                    </button>
                                </div>
                            </div>
                        </div>

                  </div> <!-- End Renovation Tab -->

              </div> <!-- End Tab Content -->

          </form>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="saveFixedAsset(${assetId})" data-i18n="save">Save</button>
        </div>
    `;

  showModal(html);
  applyTranslations();
  const propertyTab = document.getElementById("property-tab");

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
  initializePropertyMap();
  if (isEdit) {
    await loadFixedAsset(assetId);
  }
}

async function showFixedAssetDetails(assetId) {
  showLoading();

  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/`);

    if (!response.ok) throw new Error("Failed to load asset");

    const asset = await response.json();

    const photos = asset.photos || [];
    const renovations = asset.renovations || [];
    const gainValue = (asset.current_market_value || 0) - (asset.purchase_price || 0);
    const gainClass = gainValue >= 0 ? 'text-success' : 'text-danger';
    let assetViewMap = null;

    const html = `
    <div class="modal-header border-0 pb-0">
        <h5 class="modal-title" data-i18n="asset_details">Asset Details</h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
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
                                <h3 class="asset-title mb-1">${asset.name || '-'}</h3>
                                <span class="badge rounded-pill asset-type-badge" data-i18n="type_${(asset.asset_type || 'other').toLowerCase()}">${asset.asset_type || '-'}</span>
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
            </div>

            <ul class="nav nav-pills nav-fill mb-4 asset-detail-tabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="asset-general-tab" data-bs-toggle="tab" data-bs-target="#asset-general-pane" type="button" role="tab" aria-controls="asset-general-pane" aria-selected="true" data-i18n="general">General</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-property-tab" data-bs-toggle="tab" data-bs-target="#asset-property-pane" type="button" role="tab" aria-controls="asset-property-pane" aria-selected="false" data-i18n="property">Property</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-renovation-tab" data-bs-toggle="tab" data-bs-target="#asset-renovation-pane" type="button" role="tab" aria-controls="asset-renovation-pane" aria-selected="false" data-i18n="renovations">Renovations</button>
                </li>
            </ul>

            <div class="tab-content" id="assetDetailsTabsContent">
                <div class="tab-pane fade show active" id="asset-general-pane" role="tabpanel" aria-labelledby="asset-general-tab">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold" data-i18n="general_information">General Information</h6>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="asset_name">Asset Name</div><div class="col-7">${asset.name || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="asset_type">Asset Type</div><div class="col-7">${asset.asset_type || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="purchase_date">Purchase Date</div><div class="col-7">${asset.purchase_date || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="valuation_source">Valuation Source</div><div class="col-7">${asset.valuation_source || '-'}</div></div>
                                    <div class="row"><div class="col-5 text-muted" data-i18n="notes">Notes</div><div class="col-7">${asset.notes || '-'}</div></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold" data-i18n="valuation_summary">Valuation Summary</h6>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="purchase_price_egp">Purchase Price (EGP)</div><div class="col-7 fw-bold">${fmt(asset.purchase_price)}</div></div>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="purchase_price_usd">Purchase Price (USD)</div><div class="col-7 fw-bold">${fmt(asset.purchase_price_usd)}</div></div>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="current_market_value">Current Market Value</div><div class="col-7 fw-bold">${fmt(asset.current_market_value)}</div></div>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="last_valuation_date">Last Valuation Date</div><div class="col-7">${asset.last_valuation_date || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5 text-muted" data-i18n="gain_loss">Gain (EGP)</div><div class="col-7 fw-bold ${gainClass}">${fmt(gainValue)}</div></div>
                                    <div class="row"><div class="col-5 text-muted" data-i18n="gain_percent">Gain (%)</div><div class="col-7 fw-bold ${gainClass}">${asset.purchase_price ? fmtpresent((gainValue / asset.purchase_price) * 100) + '%' : '-'}</div></div>
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
                                    <h6 class="mb-3 fw-bold" data-i18n="property_details">Property Details</h6>
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
                                            <h6 class="mb-3 fw-bold" data-i18n="location">Location</h6>
                                            <div id="assetPropertyMap" class="asset-main-photo-container" style="height:280px;"></div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold" data-i18n="utilities">Utilities</h6>
                                            <div class="d-flex flex-wrap gap-2">
                                                <span class="badge rounded-pill bg-secondary-subtle text-light"><i class="bi bi-plug-fill me-1"></i><span data-i18n="electricity">Electricity</span></span>
                                                <span class="badge rounded-pill bg-secondary-subtle text-light"><i class="bi bi-droplet-fill me-1"></i><span data-i18n="water">Water</span></span>
                                                <span class="badge rounded-pill bg-secondary-subtle text-light"><i class="bi bi-fire me-1"></i><span data-i18n="gas">Gas</span></span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold" data-i18n="features">Features</h6>
                                            <div class="d-flex flex-wrap gap-2">
                                                <span class="badge rounded-pill bg-secondary-subtle text-light"><i class="bi bi-building me-1"></i><span data-i18n="elevator">Elevator</span></span>
                                                <span class="badge rounded-pill bg-secondary-subtle text-light"><i class="bi bi-car-front-fill me-1"></i><span data-i18n="garage">Garage</span></span>
                                                <span class="badge rounded-pill bg-secondary-subtle text-light"><i class="bi bi-tree-fill me-1"></i><span data-i18n="has_land_share">Land Share</span></span>
                                                <span class="badge rounded-pill bg-secondary-subtle text-light"><i class="bi bi-shield-lock-fill me-1"></i><span data-i18n="licensed">Licensed</span></span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-12">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold" data-i18n="property_photos">Photo Gallery</h6>
                                            <div id="assetMainPhotoContainer" class="asset-main-photo-container mb-3">
                                                ${photos.length ? `<img id="assetMainPhoto" src="${photos[0].url}" alt="Asset photo" class="img-fluid" style="max-height:100%;max-width:100%;cursor:pointer;" />` : `<div class="text-center text-muted" data-i18n="no_property_photos">No photos available</div>`}
                                            </div>
                                            <div class="asset-photo-grid">
                                                ${photos.length ? photos.map((photo, index) => `
                                                    <button type="button" class="btn btn-sm asset-photo-thumbnail p-0" data-url="${photo.url}" aria-label="Photo ${index + 1}">
                                                        <img src="${photo.url}" alt="Thumbnail ${index + 1}" />
                                                    </button>
                                                `).join('') : ''}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="asset-renovation-pane" role="tabpanel" aria-labelledby="asset-renovation-tab">
                    <div class="row g-3">
                        ${renovations.length ? renovations.map((r) => `
                            <div class="col-12">
                                <div class="asset-renovation-card">
                                    <div class="d-flex flex-column flex-md-row justify-content-between gap-3">
                                        <div>
                                            <div class="small text-muted mb-2" data-i18n="date">Date</div>
                                            <div class="fw-semibold">${r.date || '-'}</div>
                                            <div class="small text-muted mt-2" data-i18n="category">Category</div>
                                            <div>${r.category || '-'}</div>
                                        </div>
                                        <div class="text-md-end">
                                            <div class="small text-muted mb-2" data-i18n="amount_usd">Amount USD</div>
                                            <div class="fw-semibold">${fmt(r.amount_usd)}</div>
                                            <div class="small text-muted mt-3" data-i18n="amount_egp">Amount EGP</div>
                                            <div class="fw-semibold">${fmt(r.amount_egp)}</div>
                                        </div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small text-muted mb-1" data-i18n="description">Description</div>
                                        <div>${r.description || '-'}</div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small text-muted mb-1" data-i18n="notes">Notes</div>
                                        <div>${r.notes || '-'}</div>
                                    </div>
                                </div>
                            </div>
                        `).join('') : `
                            <div class="col-12">
                                <div class="text-center text-muted py-5" data-i18n="no_renovations">No renovations registered.</div>
                            </div>
                        `}
                        ${renovations.length ? `
                        <div class="col-12">
                            <div class="asset-renovation-card asset-renovation-summary">
                                <div class="d-flex flex-column flex-md-row justify-content-between gap-3 align-items-center">
                                    <div class="fw-semibold" data-i18n="total_renovation_cost_usd">Total Renovation Cost USD</div>
                                    <div class="text-end">
                                        <div>${fmt(renovations.reduce((sum, r) => sum + (parseFloat(r.amount_usd) || 0), 0))}</div>
                                        <div class="text-muted small" data-i18n="amount_egp">Total EGP</div>
                                        <div>${fmt(renovations.reduce((sum, r) => sum + (parseFloat(r.amount_egp) || 0), 0))}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        ` : ''}
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
        <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="close">Close</button>
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
      if (index === 0) thumb.classList.add('active');
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

    document.querySelectorAll('#assetDetailsTabsContent .text-muted').forEach((el) => {
      el.style.color = 'var(--text-secondary)';
    });
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

async function loadFixedAsset(assetId) {

    currentEditingAssetId = assetId;
  showLoading();
  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/`);
    if (!response.ok) throw new Error("Failed to load asset data");
    const asset = await response.json();

    document.getElementById("fa_name").value = asset.name || "";
    document.getElementById("fa_type").value = asset.asset_type || "Apartment";
    document.getElementById("fa_purchase_date").value =
      asset.purchase_date || "";
    document.getElementById("fa_purchase_price").value =
      asset.purchase_price || 0;
    document.getElementById("fa_purchase_usd_rate").value =
      asset.purchase_usd_rate || 1;
    document.getElementById("fa_purchase_price_usd").value =
      asset.purchase_price_usd || 0;
    updatePurchasePriceUSD();
    document.getElementById("fa_current_value").value =
      asset.current_market_value || 0;
    document.getElementById("fa_last_valuation_date").value =
      asset.last_valuation_date || "";
    document.getElementById("fa_val_source").value =
      asset.valuation_source || "Manual";
    document.getElementById("fa_last_valuation_date").value =
      asset.last_valuation_date || "";
    document.getElementById("fa_notes").value = asset.notes || "";
    // ---------------- Property Photos ----------------

    propertyPhotos = asset.photos || [];

    renderPropertyPhotoGallery();

    toggleRealEstateFields();

    if (asset.real_estate) {
      const re = asset.real_estate;
      document.getElementById("re_country").value = re.country || "";
      document.getElementById("re_governorate").value = re.governorate || "";
      document.getElementById("re_city").value = re.city || "";
      document.getElementById("re_district").value = re.district || "";
      document.getElementById("re_address").value = re.address || "";
      document.getElementById("re_latitude").value = re.latitude || "";
      document.getElementById("re_longitude").value = re.longitude || "";
      document.getElementById("re_area").value = re.apartment_area || 0;
      document.getElementById("re_land_area").value = re.land_area || 0;
      document.getElementById("re_rooms").value = re.rooms || 0;
      document.getElementById("re_bathrooms").value = re.bathrooms || 0;
      document.getElementById("re_floor").value = re.floor || 0;
      document.getElementById("re_b_floors").value = re.building_floors || 0;
      document.getElementById("re_year").value = re.building_year || 0;
      document.getElementById("re_facades").value = re.facades || "";
      document.getElementById("re_furnished").value =
        re.furnished_status || "Unfurnished";
      document.getElementById("re_finishing").value = re.finishing_level || "";
      document.getElementById("re_util_elec").checked = Boolean(re.electricity);
      document.getElementById("re_util_water").checked = Boolean(re.water);
      document.getElementById("re_util_gas").checked = Boolean(re.gas);
      document.getElementById("re_feat_elevator").checked = Boolean(
        re.elevator,
      );
      document.getElementById("re_feat_garage").checked = Boolean(re.garage);
      document.getElementById("re_feat_licensed").checked = Boolean(
        re.licensed,
      );
      document.getElementById("re_has_land_share").checked = Boolean(
        re.has_land_share,
      );
      document.getElementById("re_land_share").value = re.land_share || "";
      document.getElementById("re_description").value = re.description || "";
      const lat = parseFloat(re.latitude);
      const lng = parseFloat(re.longitude);

      if (!isNaN(lat) && !isNaN(lng)) {
        document.getElementById("re_latitude").value = lat;
        document.getElementById("re_longitude").value = lng;

        initializePropertyMap(lat, lng);
      }
    }

    // ---------- Renovations ----------
    const renovationContainer = document.getElementById("renovationContainer");

    if (renovationContainer) {
      renovationContainer.innerHTML = "";

      if (asset.renovations && asset.renovations.length) {
        asset.renovations.forEach((r) => {
          addRenovationRow({
            date: r.date,
            category: r.category,
            description: r.description,
            amount_egp: r.amount_egp,
            usd_rate: r.usd_rate,
            amount_usd: r.amount_usd,
            notes: r.notes,
          });
        });
      }
    }
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

function updatePurchasePriceUSD() {
  const egp =
    parseFloat(document.getElementById("fa_purchase_price").value) || 0;
  const rate =
    parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0;
  const usdField = document.getElementById("fa_purchase_price_usd");

  if (!usdField) return;

  if (rate > 0) {
    usdField.value = (egp / rate).toFixed(2);
  } else {
    usdField.value = "";
  }
}

async function saveFixedAsset(assetId = null) {
  const isEdit = assetId !== null;
  const url = isEdit ? `/api/fixed-assets/${assetId}/` : "/api/fixed-assets/";
  const method = isEdit ? "PUT" : "POST";

  const assetType = document.getElementById("fa_type").value;
  const isRealEstate = ["Apartment", "Villa", "Shop", "Office"].includes(
    assetType,
  );

  const payload = {
    name: document.getElementById("fa_name").value,
    asset_type: assetType,
    purchase_date: document.getElementById("fa_purchase_date").value,
    purchase_price:
      parseFloat(document.getElementById("fa_purchase_price").value) || 0,
    purchase_usd_rate:
      parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 1,
    current_market_value:
      parseFloat(document.getElementById("fa_current_value").value) || 0,
    valuation_source: document.getElementById("fa_val_source").value,
    last_valuation_date:
      document.getElementById("fa_last_valuation_date").value || null,
    notes: document.getElementById("fa_notes").value,
    status: "Owned",
  };

  if (isRealEstate) {
    payload.real_estate_details = {
      country: document.getElementById("re_country").value,
      governorate: document.getElementById("re_governorate").value,
      city: document.getElementById("re_city").value,
      district: document.getElementById("re_district").value,
      address: document.getElementById("re_address").value,
      latitude:
        parseFloat(document.getElementById("re_latitude").value) || null,
      longitude:
        parseFloat(document.getElementById("re_longitude").value) || null,
      apartment_area: parseFloat(document.getElementById("re_area").value) || 0,
      land_share_sqm:
        parseFloat(document.getElementById("re_land_area").value) || 0,
      rooms: parseInt(document.getElementById("re_rooms").value) || 0,
      bathrooms: parseInt(document.getElementById("re_bathrooms").value) || 0,
      floor: parseInt(document.getElementById("re_floor").value) || 0,
      building_floors:
        parseInt(document.getElementById("re_b_floors").value) || 0,
      building_year: parseInt(document.getElementById("re_year").value) || 0,
      facades: document.getElementById("re_facades").value,
      finishing_level: document.getElementById("re_finishing").value,
      furnished_status: document.getElementById("re_furnished").value,
      electricity: document.getElementById("re_util_elec").checked,
      water: document.getElementById("re_util_water").checked,
      gas: document.getElementById("re_util_gas").checked,
      elevator: document.getElementById("re_feat_elevator").checked,
      garage: document.getElementById("re_feat_garage").checked,
      licensed: document.getElementById("re_feat_licensed").checked,
      has_land_share: document.getElementById("re_has_land_share").checked,
      land_share: document.getElementById("re_land_share").value,
      description: document.getElementById("re_description").value,
    };
    payload.renovations = collectRenovations();
  }

  showLoading();
  try {
    const response = await fetch(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) throw new Error("Error saving fixed asset");

    const savedAsset = await response.json();

    const files = document.getElementById("propertyPhotoInput").files;

    if (files.length > 0) {
        for (const file of files) {
            const formData = new FormData();
            formData.append("photos", file);

            const uploadResponse = await fetch(
                `/api/fixed-assets/${savedAsset.id}/photos/`,
                {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: formData,
                }
            );

            if (!uploadResponse.ok)
                throw new Error("Failed to upload property photo.");

            const uploadedPhoto = await uploadResponse.json();
            propertyPhotos.push(uploadedPhoto);
        }

        renderPropertyPhotoGallery();
        document.getElementById("propertyPhotoInput").value = "";
    }

    showToast(
      isEdit ? "Asset updated successfully!" : "Asset added successfully!",
      "success",
    );

    closeModal(); // Call global dynamic closing match
    fetchAndRenderFixedAssets();
    document.getElementById("propertyPhotoInput").value = "";
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

async function deleteFixedAsset(assetId) {
  if (!confirm("Are you sure you want to delete this asset?")) return;
  showLoading();
  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/`, {
      method: "DELETE",
      headers: { "X-CSRFToken": getCsrfToken() },
    });
    if (!response.ok) throw new Error("Failed to delete fixed asset");
    showToast("Asset deleted successfully", "success");
    fetchAndRenderFixedAssets();
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

function showSaleModal(assetId, assetName, currentMarketValue) {
  const html = `
        <div class="modal-header">
            <h5 class="modal-title"><span data-i18n="sell_asset">Sell Asset</span>: ${assetName}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="assetSaleForm">
                <div class="mb-3">
                    <label class="form-label" data-i18n="sale_date">Sale Date</label>
                    <input type="date" class="form-control" id="sale_date" required>
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="sale_price">Sale Price</label>
                    <input type="number" step="0.01" class="form-control" id="sale_price" value="${currentMarketValue}" required>
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="selling_expenses">Selling Expenses</label>
                    <input type="number" step="0.01" class="form-control" id="selling_expenses" value="0">
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="notes">Notes</label>
                    <textarea class="form-control" id="sale_notes" rows="2"></textarea>
                </div>
            </form>
        </div>

        <!-- Information Cards -->
        <div class="container-fluid py-4">

            <div class="row g-4">

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="general_information">
                                General Information
                            </h6>

                            <table class="table table-borderless table-sm mb-0">

                                <tr>
                                    <td data-i18n="asset_type">Asset Type</td>
                                    <td id="details_asset_type" class="text-end fw-bold"></td>
                                </tr>

                                <tr>
                                    <td data-i18n="purchase_date">Purchase Date</td>
                                    <td id="details_purchase_date" class="text-end"></td>
                                </tr>

                                <tr>
                                    <td data-i18n="valuation_source">Valuation Source</td>
                                    <td id="details_valuation_source" class="text-end"></td>
                                </tr>

                            </table>

                        </div>

                    </div>

                </div>

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="financial_information">
                                Financial Information
                            </h6>

                            <table class="table table-borderless table-sm mb-0">

                                <tr>
                                    <td data-i18n="purchase_price_egp">Purchase Price</td>
                                    <td id="details_purchase_price" class="text-end fw-bold"></td>
                                </tr>

                                <tr>
                                    <td data-i18n="purchase_price_usd">Purchase USD</td>
                                    <td id="details_purchase_usd" class="text-end"></td>
                                </tr>

                                <tr>
                                    <td data-i18n="last_valuation_date">Last Valuation</td>
                                    <td id="details_last_valuation" class="text-end"></td>
                                </tr>

                            </table>

                        </div>

                    </div>

                </div>

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="notes">
                                Notes
                            </h6>

                            <div id="details_notes"
                                style="white-space:pre-wrap;"></div>

                        </div>

                    </div>

                </div>

            </div>

        </div>

        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="submitAssetSale(${assetId})" data-i18n="confirm_sale">Confirm Sale</button>
        </div>
    `;
  showModal(html);
  applyTranslations();
}

async function submitAssetSale(assetId) {
  const salePrice =
    parseFloat(document.getElementById("sale_price").value) || 0;
  const expenses =
    parseFloat(document.getElementById("selling_expenses").value) || 0;
  const netSaleAmount = salePrice - expenses;

  const payload = {
    sale_date: document.getElementById("sale_date").value,
    sale_price: salePrice,
    selling_expenses: expenses,
    net_sale_amount: netSaleAmount,
    notes: document.getElementById("sale_notes").value,
  };

  showLoading();
  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) throw new Error("Failed to process sale");

    showToast("Asset marked as Sold successfully!", "success");
    closeModal();
    fetchAndRenderFixedAssets();
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

function toggleRealEstateFields() {
  const assetType = document.getElementById("fa_type").value;
  const reSection = document.getElementById("realEstateSection");
  const isRealEstate = ["Apartment", "Villa", "Shop", "Office"].includes(
    assetType,
  );

  if (reSection) {
    reSection.style.display = isRealEstate ? "block" : "none";
  }
}

function getCsrfToken() {
  return (
    document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1] || ""
  );
}

function initializePropertyMap(lat = 30.0444, lng = 31.2357) {
  if (propertyMap) {
    propertyMap.remove();
    propertyMap = null;
  }

  propertyMap = L.map("propertyMap").setView([lat, lng], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(propertyMap);

  propertyMarker = L.marker([lat, lng], {
    draggable: true,
  }).addTo(propertyMap);

  propertyMarker.on("dragend", function () {
    const p = propertyMarker.getLatLng();

    document.getElementById("re_latitude").value = p.lat.toFixed(6);
    document.getElementById("re_longitude").value = p.lng.toFixed(6);

    reverseGeocode(p.lat, p.lng);
  });

  propertyMap.on("click", function (e) {
    propertyMarker.setLatLng(e.latlng);

    document.getElementById("re_latitude").value = e.latlng.lat.toFixed(6);
    document.getElementById("re_longitude").value = e.latlng.lng.toFixed(6);

    reverseGeocode(e.latlng.lat, e.latlng.lng);
  });

    setTimeout(() => propertyMap.invalidateSize(), 200);

    const uploadBtn = document.getElementById("btnUploadPropertyPhoto");
    const uploadInput = document.getElementById("propertyPhotoInput");

    if (uploadBtn && uploadInput) {

        uploadBtn.onclick = () => uploadInput.click();

        uploadInput.onchange = function () {

        const gallery = document.getElementById("propertyPhotoGallery");

        gallery.innerHTML = "";

        Array.from(this.files).forEach(file => {

            const reader = new FileReader();

            reader.onload = function (e) {

                gallery.insertAdjacentHTML(
                    "beforeend",
                    `
                    <div class="col-md-4">

                        <div class="card border-0 shadow-sm">

                            <div class="d-flex justify-content-center align-items-center"
                                style="height:220px; background:var(--bg-secondary);">

                                <img
                                    src="${e.target.result}"
                                    class="img-fluid rounded"
                                    style="
                                        max-width:100%;
                                        max-height:200px;
                                        object-fit:contain;">

                            </div>

                            <div class="card-body p-2 text-center">

                                <div class="small text-truncate">
                                    ${file.name}
                                </div>

                            </div>

                        </div>

                    </div>
                    `
                );

            };

            reader.readAsDataURL(file);

        });

    };

    }
    
}

function renderPropertyPhotoGallery() {

    const gallery = document.getElementById("propertyPhotoGallery");

    if (!gallery) return;

    gallery.innerHTML = "";

    if (!propertyPhotos || propertyPhotos.length === 0) {

        gallery.innerHTML = `
            <div class="col-12 text-center py-4">
                <i class="bi bi-images"
                   style="font-size:40px;color:var(--text-secondary);opacity:.45;"></i>

                <div class="mt-2"
                     style="color:var(--text-secondary);"
                     data-i18n="no_property_photos">
                    No property photos uploaded
                </div>
            </div>
        `;

        applyTranslations();
        return;
    }

    propertyPhotos.forEach((photo, index) => {

        gallery.innerHTML += `
            <div class="col-md-4 col-lg-3">

                <div class="card border-0 shadow-sm h-100">

                    <img
                        src="${photo.url}"
                        class="card-img-top"
                        style="height:180px;object-fit:cover;">

                        <button
                            type="button"
                            class="btn btn-danger w-100"
                            onclick="removePropertyPhoto(${index})">
                            <i class="bi bi-trash"></i>
                        </button>

                </div>
            </div>
        `;

    });

}

async function removePropertyPhoto(index) {

    const photo = propertyPhotos[index];

    if (!photo) return;

    if (!confirm("Delete this photo?")) return;

    try {

        const response = await fetch(
            `/api/fixed-assets/${currentEditingAssetId}/photos/${photo.id}/`,
            {
                method: "DELETE",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                },
            }
        );

        if (!response.ok)
            throw new Error("Failed to delete photo.");

        propertyPhotos.splice(index, 1);

        renderPropertyPhotoGallery();

        showToast("Photo deleted successfully.", "success");

    } catch (err) {

        showToast(err.message, "danger");

    }

}

async function locatePropertyOnMap() {
  const country = document.getElementById("re_country").value.trim();
  const governorate = document.getElementById("re_governorate").value.trim();
  const city = document.getElementById("re_city").value.trim();
  const district = document.getElementById("re_district").value.trim();
  const address = document.getElementById("re_address").value.trim();

  const query = [address, district, city, governorate, country]
    .filter(Boolean)
    .join(", ");

  if (!query) {
    showToast("Please enter an address first.", "warning");
    return;
  }

  showLoading();

  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`,
    );

    const results = await response.json();

    if (!results.length) {
      showToast("Address not found.", "warning");
      return;
    }

    const lat = parseFloat(results[0].lat);
    const lng = parseFloat(results[0].lon);

    document.getElementById("re_latitude").value = lat.toFixed(6);
    document.getElementById("re_longitude").value = lng.toFixed(6);

    propertyMap.setView([lat, lng], 17);

    propertyMarker.setLatLng([lat, lng]);
  } catch (err) {
    console.error(err);
    showToast("Unable to locate address.", "danger");
  } finally {
    hideLoading();
  }
}

async function reverseGeocode(lat, lng) {
  try {
    const currentLang = localStorage.getItem("lang") || "en";

    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=${currentLang},en`,
    );

    const result = await response.json();

    if (!result.address) return;

    const a = result.address;
    document.getElementById("re_country").value = a.country || "";

    document.getElementById("re_governorate").value = a.state || a.county || "";

    document.getElementById("re_city").value =
      a.city || a.town || a.village || "";

    document.getElementById("re_district").value =
      a.suburb ||
      a.neighbourhood ||
      a.city_district ||
      a.district ||
      a.municipality ||
      a.hamlet ||
      a.quarter ||
      a.borough ||
      a.village ||
      a.town ||
      a.city ||
      "";

    document.getElementById("re_address").value = result.display_name || "";
  } catch (err) {
    console.error(err);
  }
}

function addRenovationRow(data = {}) {
  const container = document.getElementById("renovationContainer");

  const row = document.createElement("div");

  row.className = "row g-2 mb-3 renovation-row";

  row.innerHTML = `

        <div class="col-md-2">
            <label class="form-label small"
                   data-i18n="renovation_date">
                Date
            </label>

            <input
                type="date"
                class="form-control renovation-date"
                value="${data.date || ""}">
        </div>

        <div class="col-md-2">

            <label class="form-label small"
                   data-i18n="renovation_type">
                Renovation Type
            </label>

            <select class="form-select renovation-category">

                <option value="Finishing"
                    data-i18n="renovation_finishing">
                    Finishing
                </option>

                <option value="Painting"
                    data-i18n="renovation_painting">
                    Painting
                </option>

                <option value="Flooring"
                    data-i18n="renovation_flooring">
                    Flooring
                </option>

                <option value="Kitchen"
                    data-i18n="renovation_kitchen">
                    Kitchen
                </option>

                <option value="Bathroom"
                    data-i18n="renovation_bathroom">
                    Bathroom
                </option>

                <option value="Electrical"
                    data-i18n="renovation_electrical">
                    Electrical
                </option>

                <option value="Plumbing"
                    data-i18n="renovation_plumbing">
                    Plumbing
                </option>

                <option value="Doors & Windows"
                    data-i18n="renovation_doors_windows">
                    Doors & Windows
                </option>

                <option value="Furniture"
                    data-i18n="renovation_furniture">
                    Furniture
                </option>

                <option value="Landscape"
                    data-i18n="renovation_landscape">
                    Landscape
                </option>

                <option value="Maintenance"
                    data-i18n="renovation_maintenance">
                    Maintenance
                </option>

                <option value="Other"
                    data-i18n="type_other">
                    Other
                </option>

            </select>

        </div>

        <div class="col-md-3">

            <label class="form-label small"
                   data-i18n="description">
                Description
            </label>

            <input
                type="text"
                class="form-control renovation-description"
                data-i18n-placeholder="description"
                placeholder="Description"
                value="${data.description || ""}">

        </div>

        <div class="col-md-2">

            <label class="form-label small"
                   data-i18n="amount">
                Amount (EGP)
            </label>

            <input
                type="number"
                step="0.01"
                class="form-control renovation-egp"
                value="${data.amount_egp || ""}"
                oninput="updateRenovationUSD(this)">

        </div>

        <div class="col-md-2">

            <label class="form-label small"
                   data-i18n="amount_usd">
                USD
            </label>

            <input
                type="number"
                step="0.01"
                class="form-control renovation-usd"
                value="${data.amount_usd || ""}"
                readonly>

        </div>



            <div class="col-md-1">

                <label class="form-label small">&nbsp;</label>

                <button
                    type="button"
                    class="btn btn-danger w-100"
                    onclick="this.closest('.renovation-row').remove()">

                    <i class="bi bi-trash"></i>

                </button>

            </div>

        <div class="col-md-12">

            <label class="form-label small"
                   data-i18n="notes">
                Notes
            </label>

            <textarea
                class="form-control renovation-notes"
                rows="2">${data.notes || ""}</textarea>

        </div>

    `;

  container.appendChild(row);

  row.querySelector(".renovation-category").value =
    data.category || "Finishing";

  applyTranslations();
  updateRenovationUSD(row.querySelector(".renovation-egp"));
}

function collectRenovations() {
  const renovations = [];

  document.querySelectorAll(".renovation-row").forEach((row) => {
    renovations.push({
      date: row.querySelector(".renovation-date").value,

      category: row.querySelector(".renovation-category").value,

      description: row.querySelector(".renovation-description").value,

      amount_egp: parseFloat(row.querySelector(".renovation-egp").value) || 0,

      usd_rate:
        parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0,

      amount_usd: parseFloat(row.querySelector(".renovation-usd").value) || 0,

      notes: row.querySelector(".renovation-notes").value,
    });
  });

  return renovations;
}

function updateRenovationUSD(input) {
  const row = input.closest(".renovation-row");

  const egp = parseFloat(row.querySelector(".renovation-egp").value) || 0;

  const rate =
    parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0;

  const usdInput = row.querySelector(".renovation-usd");

  if (rate > 0) {
    usdInput.value = (egp / rate).toFixed(2);
  } else {
    usdInput.value = "";
  }
}

// ════════════════════════════════════════════════════════════════════════════
// GLOBAL ROUTER EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.renderFixedAssets = renderFixedAssets;
window.showFixedAssetModal = showFixedAssetModal;
window.showSaleModal = showSaleModal;

if (window.location.hash === "#fixed-assets") {
  renderFixedAssets();
}
