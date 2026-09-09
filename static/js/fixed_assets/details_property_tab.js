"use strict";
// Fixed asset modal — Property tab pane builder. Split out of
// details_property.js (200-line backlog). Bare global.
// ════════════════════════════════════════════════════════════════════════════

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

