"use strict";

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

                        <div class="col-md-12">
                            <label class="form-label text-light" data-i18n="notes">Internal Notes</label>
                            <textarea class="form-control" id="fa_notes" rows="2"></textarea>
                        </div>

                  </div> <!-- End General Tab -->`;
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
