"use strict";

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
