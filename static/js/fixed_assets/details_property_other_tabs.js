"use strict";
// Fixed asset modal — Renovation, Furniture, Mortgage, and Rental tab pane
// builders. Split out of details_property.js (200-line backlog). Bare
// globals.
// ════════════════════════════════════════════════════════════════════════════

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
                            <div class="field">
                              <label class="form-label" data-i18n="receive_method">Receive Into</label>
                              <select class="form-select rental-payment-method" id="fa_rental_receive_method" onchange="toggleMoneyMovementBankField(this, 'rental')">${renderPaymentMethodOptions("Cash")}</select>
                            </div>
                            <div class="field rental-bank-wrap" style="display:none;">
                              <label class="form-label" data-i18n="bank_account">Bank Account<span class="text-danger"> *</span></label>
                              <select class="form-select rental-bank" id="fa_rental_bank">${renderBankWithBalanceOptions("")}</select>
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
