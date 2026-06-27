"use strict";

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
        <div class="table-responsive rounded-3 mt-4" style="border: 1px solid var(--border-color); background: var(--bg-secondary);">
            <table class="table table-hover align-middle mb-0" style="color: var(--text-primary);">
                <thead style="background: rgba(0, 0, 0, 0.2); border-bottom: 2px solid var(--border-color);">
                    <tr>
                        <th class="px-4 py-3 small text-muted text-uppercase tracking-wider" data-i18n="asset_name">Asset Name</th>
                        <th class="px-3 py-3 small text-muted text-uppercase tracking-wider" data-i18n="asset_type">Asset Type</th>
                        <th class="px-3 py-3 small text-muted text-uppercase tracking-wider" data-i18n="purchase_date">Purchase Date</th>
                        <th class="px-3 py-3 small text-muted text-uppercase tracking-wider text-end" data-i18n="purchase_price_egp">Purchase Price (EGP)</th>
                        <th class="px-3 py-3 small text-muted text-uppercase tracking-wider text-end" data-i18n="current_market_value">Current Value</th>
                        <th class="px-4 py-3 small text-muted text-uppercase tracking-wider text-center" style="width: 120px;" data-i18n="actions">Actions</th>
                    </tr>
                </thead>
                <tbody style="border-top: none;">
    `;


  assetsArray.forEach((asset) => {

    const assetType = asset.asset_type || asset.type || "Other";
    const typeKey = `type_${assetType.toLowerCase()}`;

    html += `
            <tr style="border-bottom: 1px solid var(--border-color);">
                <td class="px-4 py-3 fw-bold asset-name-cell">${asset.name || ""}</td>
                <td class="px-3 py-3">
                    <span class="badge bg-dark text-light border" style="border-color: var(--border-color) !important;" data-i18n="${typeKey}">${assetType}</span>
                </td>
                <td class="px-3 py-3 text-muted small">${asset.purchase_date || ""}</td>
                <td class="px-3 py-3 text-end font-monospace">${Number(asset.purchase_price || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td class="px-3 py-3 text-end font-monospace text-success fw-bold">${Number(asset.current_market_value || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td class="px-4 py-3 text-center">
                    <div class="btn-group row-actions">
                        <button class="btn btn-sm btn-outline-secondary border-0 text-muted" onclick="showFixedAssetModal(${asset.id})" title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger border-0" onclick="deleteFixedAsset(${asset.id})" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
  });

  html += `
                </tbody>
            </table>
        </div>
    `;

  container.innerHTML = html;
  //if (typeof applyTranslations === 'function')
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
        <div class="modal fade" id="fixedAssetModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content" style="background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.37);">
                    <div class="modal-header px-4" style="border-bottom: 1px solid var(--border-color); background: rgba(0,0,0,0.1);">
                        <h5 class="modal-title font-weight-bold" data-i18n="${modalTitleKey}" style="font-size: 1.15rem; color: var(--text-primary);">${modalTitleDefault}</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body p-4" style="max-height:70vh; overflow-y:auto;">
                        <form id="fixedAssetForm">
                            <div class="row g-2 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="asset_name">Asset Name</label>
                                    <input type="text" class="form-control" id="fa_name" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="asset_type">Asset Type</label>
                                    <select class="form-select" id="fa_type" onchange="toggleRealEstateFields()" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);" required>
                                        <option value="Apartment" data-i18n="type_apartment" style="background: var(--bg-primary); color: var(--text-primary);">Apartment</option>
                                        <option value="Villa" data-i18n="type_villa" style="background: var(--bg-primary); color: var(--text-primary);">Villa</option>
                                        <option value="Land" data-i18n="type_land" style="background: var(--bg-primary); color: var(--text-primary);">Land</option>
                                        <option value="Shop" data-i18n="type_shop" style="background: var(--bg-primary); color: var(--text-primary);">Shop</option>
                                        <option value="Office" data-i18n="type_office" style="background: var(--bg-primary); color: var(--text-primary);">Office</option>
                                        <option value="Car" data-i18n="type_car" style="background: var(--bg-primary); color: var(--text-primary);">Car</option>
                                        <option value="Other" data-i18n="type_other" style="background: var(--bg-primary); color: var(--text-primary);">Other</option>
                                    </select>
                                </div>
                            </div>

                            <div class="row g-2 mb-3">
                                <div class="col-md-4">
                                    <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="purchase_date">Purchase Date</label>
                                    <input type="date" class="form-control" id="fa_purchase_date" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);" required>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="purchase_price_egp">Purchase Price (EGP)</label>
                                    <input type="number" step="0.01" class="form-control" id="fa_purchase_price" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);" required>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="purchase_usd_rate">USD Exchange Rate</label>
                                    <input type="number" step="0.0001" class="form-control" id="fa_purchase_usd_rate" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);" required>
                                </div>
                            </div>

                            <div class="row g-2 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="current_market_value">Current Market Value</label>
                                    <input type="number" step="0.01" class="form-control" id="fa_current_value" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="valuation_source">Valuation Source</label>
                                    <select class="form-select" id="fa_val_source" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);">
                                        <option value="Manual" data-i18n="val_manual" style="background: var(--bg-primary); color: var(--text-primary);">Manual Input</option>
                                        <option value="Automatic" data-i18n="val_automatic" style="background: var(--bg-primary); color: var(--text-primary);">System Synced</option>
                                    </select>
                                </div>
                            </div>

                            <div id="realEstateSection" style="display: none; border-top: 1px dashed var(--border-color); padding-top: 20px; margin-top: 15px;">
                                <h6 class="mb-3 font-weight-bold" style="font-size: 0.95rem; color: var(--text-primary);" data-i18n="real_estate_details">Real Estate Technical Specifications</h6>
                                <div class="row g-2 mb-2">
                                    <div class="col-md-3"><input type="text" class="form-control" id="re_country" placeholder="Egypt" data-i18n-placeholder="country" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-3"><input type="text" class="form-control" id="re_governorate" placeholder="Governorate" data-i18n-placeholder="governorate" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-3"><input type="text" class="form-control" id="re_city" placeholder="City" data-i18n-placeholder="city" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-3"><input type="text" class="form-control" id="re_district" placeholder="District" data-i18n-placeholder="district" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-12"><input type="text" class="form-control" id="re_address" placeholder="Address Details" data-i18n-placeholder="address" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                </div>

                                <div class="row g-2 mb-2">
                                    <div class="col-md-3"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="apt_area">Property Area (Sqm)</label><input type="number" class="form-control" id="re_area" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-3"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="land_area">Land Plot Footprint (Sqm)</label><input type="number" class="form-control" id="re_land_area" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-2"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="rooms">Bedrooms</label><input type="number" class="form-control" id="re_rooms" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-2"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="bathrooms">Bathrooms</label><input type="number" class="form-control" id="re_bathrooms" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-2"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="floor">Floor Number</label><input type="number" class="form-control" id="re_floor" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                </div>

                                <div class="row g-2 mb-2">
                                    <div class="col-md-3"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="building_floors">Total Building Stories</label><input type="number" class="form-control" id="re_b_floors" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-3"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="building_year">Construction Year</label><input type="number" class="form-control" id="re_year" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-3"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="facades">Facade Orientation</label><input type="text" class="form-control" id="re_facades" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                    <div class="col-md-3"><label class="form-label small mb-1" style="color: var(--text-primary);" data-i18n="finishing_level">Finishing Level Type</label><input type="text" class="form-control" id="re_finishing" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></div>
                                </div>

                                <div class="row g-2 mb-2">
                                    <div class="col-md-6">
                                        <label class="form-label small d-block mb-2" style="color: var(--text-primary);" data-i18n="utilities">Available Utilities</label>
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input" type="checkbox" id="re_util_elec">
                                            <label class="form-check-label small" for="re_util_elec" style="color: var(--text-primary);" data-i18n="electricity">Electricity Grid Connection</label>
                                        </div>
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input" type="checkbox" id="re_util_water">
                                            <label class="form-check-label small" for="re_util_water" style="color: var(--text-primary);" data-i18n="water">Water Line Connection</label>
                                        </div>
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input" type="checkbox" id="re_util_gas">
                                            <label class="form-check-label small" for="re_util_gas" style="color: var(--text-primary);" data-i18n="gas">Natural Gas Supply</label>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label small d-block mb-2" style="color: var(--text-primary);" data-i18n="features">Structural Amenities</label>
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input" type="checkbox" id="re_feat_elevator">
                                            <label class="form-check-label small" for="re_feat_elevator" style="color: var(--text-primary);" data-i18n="elevator">Elevator Access</label>
                                        </div>
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input" type="checkbox" id="re_feat_garage">
                                            <label class="form-check-label small" for="re_feat_garage" style="color: var(--text-primary);" data-i18n="garage">Dedicated Parking/Garage</label>
                                        </div>
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input" type="checkbox" id="re_feat_licensed">
                                            <label class="form-check-label small" for="re_feat_licensed" style="color: var(--text-primary);" data-i18n="licensed">Legally Licensed Building</label>
                                        </div>
                                    </div>
                                </div>

                                <div class="row g-2">
                                    <div class="col-md-4">
                                        <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="land_share">Undivided Land Share (Carat)</label>
                                        <input type="text" class="form-control" id="re_land_share" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);">
                                    </div>
                                    <div class="col-md-8">
                                        <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="description">Property Structural Description</label>
                                        <input type="text" class="form-control" id="re_description" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);">
                                    </div>
                                </div>
                            </div>

                            <div class="mb-2 mt-4">
                                <label class="form-label small mb-2" style="color: var(--text-primary);" data-i18n="notes">Internal Notes</label>
                                <textarea class="form-control" id="fa_notes" rows="2" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color); caret-color: var(--text-primary);"></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer px-4" style="border-top: 1px solid var(--border-color); background: rgba(0,0,0,0.1);">
                        <button type="button" class="btn btn-secondary px-4" data-bs-dismiss="modal" data-i18n="cancel" style="border-radius: 6px;">Cancel</button>
                        <button type="button" class="btn btn-primary px-4 btn-primary-custom" onclick="saveFixedAsset(${assetId})" data-i18n="save" style="border-radius: 6px;">Save</button>
                    </div>
                </div>
            </div>
        </div>
    `;

  document.getElementById("modal-container").innerHTML = html;
  const modalEl = document.getElementById("fixedAssetModal");
  const modalInstance = new bootstrap.Modal(modalEl);

  if (typeof applyTranslations === "function") applyTranslations();

  modalInstance.show();

  if (isEdit) {
      await loadFixedAsset(assetId);
  }
}

async function loadFixedAsset(assetId) {
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
    document.getElementById("fa_current_value").value =
      asset.current_market_value || 0;
    document.getElementById("fa_val_source").value =
      asset.valuation_source || "Manual";
    document.getElementById("fa_notes").value = asset.notes || "";

    toggleRealEstateFields();

    if (asset.real_estate) {
      const re = asset.real_estate;
      document.getElementById("re_country").value = re.country || "";
      document.getElementById("re_governorate").value = re.governorate || "";
      document.getElementById("re_city").value = re.city || "";
      document.getElementById("re_district").value = re.district || "";
      document.getElementById("re_address").value = re.address || "";
      document.getElementById("re_area").value = re.apartment_area || 0;
      document.getElementById("re_land_area").value = re.land_area || 0;
      document.getElementById("re_rooms").value = re.rooms || 0;
      document.getElementById("re_bathrooms").value = re.bathrooms || 0;
      document.getElementById("re_floor").value = re.floor || 0;
      document.getElementById("re_b_floors").value = re.building_floors || 0;
      document.getElementById("re_year").value = re.building_year || 0;
      document.getElementById("re_facades").value = re.facades || "";
      document.getElementById("re_finishing").value = re.finishing_level || "";
      document.getElementById("re_util_elec").checked = Boolean(re.electricity);
      document.getElementById("re_util_water").checked = Boolean(re.water);
      document.getElementById("re_util_gas").checked = Boolean(re.gas);
      document.getElementById("re_feat_elevator").checked = Boolean(re.elevator);
      document.getElementById("re_feat_garage").checked = Boolean(re.garage);
      document.getElementById("re_feat_licensed").checked = Boolean(re.licensed);
      document.getElementById("re_land_share").value = re.land_share || "";
      document.getElementById("re_description").value = re.description || "";
    }
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
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
      apartment_area: parseFloat(document.getElementById("re_area").value) || 0,
      land_share_sqm: parseFloat(document.getElementById("re_land_area").value) || 0,
      rooms: parseInt(document.getElementById("re_rooms").value) || 0,
      bathrooms: parseInt(document.getElementById("re_bathrooms").value) || 0,
      floor: parseInt(document.getElementById("re_floor").value) || 0,
      building_floors:
        parseInt(document.getElementById("re_b_floors").value) || 0,
      building_year: parseInt(document.getElementById("re_year").value) || 0,
      facades: document.getElementById("re_facades").value,
      finishing_level: document.getElementById("re_finishing").value,
      electricity: document.getElementById("re_util_elec").checked,
      water: document.getElementById("re_util_water").checked,
      gas: document.getElementById("re_util_gas").checked,
      elevator: document.getElementById("re_feat_elevator").checked,
      garage: document.getElementById("re_feat_garage").checked,
      licensed: document.getElementById("re_feat_licensed").checked,
      land_share: document.getElementById("re_land_share").value,
      description: document.getElementById("re_description").value,
    };
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

    showToast(
      isEdit ? "Asset updated successfully!" : "Asset added successfully!",
      "success",
    );

    const modalEl = document.getElementById("fixedAssetModal");
    const modalInstance = bootstrap.Modal.getInstance(modalEl);
    if (modalInstance) modalInstance.hide();

    fetchAndRenderFixedAssets();
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
        <div class="modal fade" id="assetSaleModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content" style="background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border-color);caret-color: var(--text-primary);">
                    <div class="modal-header">
                        <h5 class="modal-title"><span data-i18n="sell_asset">Sell Asset</span>: ${assetName}</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="assetSaleForm">
                            <div class="mb-3">
                                <label class="form-label" style="color: var(--text-primary);" data-i18n="sale_date">Sale Date</label>
                                <input type="date" class="form-control" id="sale_date" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label" style="color: var(--text-primary);" data-i18n="sale_price">Sale Price</label>
                                <input type="number" step="0.01" class="form-control" id="sale_price" value="${currentMarketValue}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label" style="color: var(--text-primary);" data-i18n="selling_expenses">Selling Expenses</label>
                                <input type="number" step="0.01" class="form-control" id="selling_expenses" value="0">
                            </div>
                            <div class="mb-3">
                                <label class="form-label" style="color: var(--text-primary);" data-i18n="notes">Notes</label>
                                <textarea class="form-control" id="sale_notes" rows="2"></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" data-i18n="cancel">Cancel</button>
                        <button type="button" class="btn btn-danger" onclick="submitAssetSale(${assetId})" data-i18n="confirm_sale">Confirm Sale</button>
                    </div>
                </div>
            </div>
        </div>
    `;
  document.getElementById("modal-container").innerHTML = html;
  if (typeof applyTranslations === "function") applyTranslations();
  new bootstrap.Modal(document.getElementById("assetSaleModal")).show();
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
    bootstrap.Modal.getInstance(
      document.getElementById("assetSaleModal"),
    ).hide();
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

// ════════════════════════════════════════════════════════════════════════════
// GLOBAL ROUTER EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.renderFixedAssets = renderFixedAssets;
window.showFixedAssetModal = showFixedAssetModal;
window.showSaleModal = showSaleModal;

if (window.location.hash === "#fixed-assets") {
  renderFixedAssets();
}