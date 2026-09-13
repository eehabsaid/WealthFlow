"use strict";
// Fixed assets detail tabs: insurance, sale, documents
// This file is part of the fixed_assets module. Do not edit directly.

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
