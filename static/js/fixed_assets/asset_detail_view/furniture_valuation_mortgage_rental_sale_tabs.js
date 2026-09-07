"use strict";
// Real-estate asset detail modal: Furniture + Valuation History + Mortgage + Rental + Sale tab panes, plus the photo-overlay markup and modal footer (kept together since they close out the same template literal as the original monolithic function).

function buildFurnitureValuationMortgageRentalSaleTabsHtml(ctx) {
  const { asset, furniture, valuationHistory, sale, mortgage, rental } = ctx;
  return `
                  ${
                    furniture.length
                      ? `
                  <div class="tab-pane fade" id="asset-furniture-pane" role="tabpanel" aria-labelledby="asset-furniture-tab">
                    <div class="row g-3">
                      ${furniture
                        .map(
                          (item) => `
                        <div class="col-md-6">
                          <div class="asset-renovation-card h-100">
                            <div class="d-flex justify-content-between gap-3">
                              <div>
                                <div class="small mb-1" data-i18n="item_name">Item Name</div>
                                <div class="fw-semibold">${item.name || "-"}</div>
                              </div>
                              <div class="text-end">
                                <div class="small mb-1" data-i18n="amount_egp">Amount</div>
                                <div class="fw-semibold">${fmt(item.amount_egp * parseInt(item.quantity) || 1)}</div>
                              </div>
                            </div>
                            <div class="mt-3 d-flex justify-content-between gap-3">
                               <div><span class="small" data-i18n="category">Category</span><div data-i18n-prefix="furniture_" data-i18n-value="${(item.category || "").toLowerCase().replace(/ & /g, "_").replace(/ /g, "_")}">${item.category || "-"}</div></div>
                               <div><span class="small" data-i18n="quantity">Quantity</span><div>${item.quantity || "-"}</div></div>
                              <div><span class="small" data-i18n="purchase_date">Purchase Date</span><div>${formatDate(item.purchase_date) || "-"}</div></div>
                            </div>
                            <div class="mt-3"><div class="small mb-1" data-i18n="notes">Notes</div><div>${item.notes || "-"}</div></div>
                          </div>
                        </div>
                      `
                        )
                        .join("")}
                      <div class="col-12">
                            <div class="asset-renovation-card asset-renovation-summary" style="padding: 16px;">
                                <div class="d-flex flex-column gap-2" style="width: 100%;">
                                    
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="total_furniture_cost_usd">Total Furniture Cost USD</div>
                                        <div class="text-end fw-semibold">
                                            $${fmt(
                                              furniture.reduce((sum, item) => {
                                                const qty = parseInt(item.quantity) || 1;
                                                const rate =
                                                  parseFloat(item.usd_rate) ||
                                                  parseFloat(asset.purchase_usd_rate) ||
                                                  0;
                                                if (rate > 0) {
                                                  return (
                                                    sum +
                                                    ((parseFloat(item.amount_egp) || 0) * qty) /
                                                      rate
                                                  );
                                                } else {
                                                  return sum + (parseFloat(item.amount_usd) || 0);
                                                }
                                              }, 0)
                                            )}
                                        </div>
                                    </div>

                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="amount_egp">Amount</div>
                                        <div class="text-end fw-semibold">
                                            ${fmt(furniture.reduce((sum, item) => sum + (parseFloat(item.amount_egp) || 0) * (parseInt(item.quantity) || 1), 0))} <span data-i18n="EGP">EGP</span>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </div>
                    </div>
                  </div>
                  `
                      : ""
                  }
                  ${
                    valuationHistory.length
                      ? `
                  <div class="tab-pane fade" id="asset-valuation-pane" role="tabpanel" aria-labelledby="asset-valuation-tab">
                    <div class="row g-3">
                      ${valuationHistory
                        .map(
                          (item) => `
                        <div class="col-12">
                          <div class="asset-renovation-card">
                            <div class="d-flex flex-column flex-md-row justify-content-between gap-3">
                              <div>
                                <div class="small mb-1" data-i18n="date">Date</div>
                                <div class="fw-semibold">${formatDate(item.valuation_date) || "-"}</div>
                              </div>
                              <div>
                                <div class="small mb-1" data-i18n="valuation_source">Valuation Source</div>
                                <div>${item.valuation_source || "-"}</div>
                              </div>
                              <div class="text-md-end">
                                <div class="small mb-1" data-i18n="current_market_value">Current Market Value</div>
                                <div class="fw-semibold">${fmt(item.market_value)}</div>
                              </div>
                            </div>
                            <div class="mt-3"><div class="small mb-1" data-i18n="notes">Notes</div><div>${item.notes || "-"}</div></div>
                          </div>
                        </div>
                      `
                        )
                        .join("")}
                    </div>
                  </div>
                  `
                      : ""
                  }
                  <div class="tab-pane fade" id="asset-mortgage-pane" role="tabpanel" aria-labelledby="asset-mortgage-tab">
                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                      <div class="card-body p-4">
                        ${
                          mortgage
                            ? `
                          <div class="row g-3">
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="loan_amount">Loan Amount</span><span class="value">${fmt(mortgage.loan_amount)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="remaining_balance">Remaining Balance</span><span class="value">${fmt(mortgage.remaining_balance)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="monthly_installment">Monthly Installment</span><span class="value">${fmt(mortgage.monthly_installment)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="interest_rate">Interest Rate</span><span class="value">${fmtpresent(mortgage.interest_rate)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="start_date">Start Date</span><span class="value">${formatDate(mortgage.start_date) || "-"}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="end_date">End Date</span><span class="value">${formatDate(mortgage.end_date) || "-"}</span></div></div>
                            <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="net_equity">Net Equity</span><span class="value">${fmt(mortgage.net_equity)}</span></div></div>
                          </div>
                        `
                            : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`
                        }
                      </div>
                    </div>
                  </div>

                  <div class="tab-pane fade" id="asset-rental-pane" role="tabpanel" aria-labelledby="asset-rental-tab">
                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                      <div class="card-body p-4">
                        ${
                          rental
                            ? `
                          <div class="row g-3">
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="monthly_rent">Monthly Rent</span><span class="value">${fmt(rental.monthly_rent)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="annual_rent">Annual Rent</span><span class="value">${fmt(rental.annual_rent)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="occupancy_rate">Occupancy Rate</span><span class="value">${fmtpresent(rental.occupancy_rate)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="rental_yield">Rental Yield</span><span class="value">${fmtpresent(rental.rental_yield)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="tenant_name_optional">Tenant Name</span><span class="value">${rental.tenant_name || "-"}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="contract_start">Contract Start</span><span class="value">${formatDate(rental.contract_start) || "-"}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="contract_end">Contract End</span><span class="value">${formatDate(rental.contract_end) || "-"}</span></div></div>
                            <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${rental.notes || "-"}</span></div></div>
                          </div>
                        `
                            : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`
                        }
                      </div>
                    </div>
                  </div>

                  <div class="tab-pane fade" id="asset-sale-pane" role="tabpanel" aria-labelledby="asset-sale-tab">
                    <div class="row g-3">
                      <div class="col-md-6">
                        <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                          <div class="card-body p-4">
                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="sale_information">Sale Information</h6>
                            ${
                              sale
                                ? `
                              <div class="row mb-2"><div class="col-5" data-i18n="sale_date">Sale Date</div><div class="col-7">${formatDate(sale.sale_date) || "-"}</div></div>
                              <div class="row mb-2"><div class="col-5" data-i18n="sale_price_egp">Sale Price</div><div class="col-7 fw-bold">${fmt(sale.sale_price)}</div></div>
                              <div class="row mb-2"><div class="col-5" data-i18n="selling_expenses_egp">Selling Expenses</div><div class="col-7">${fmt(sale.selling_expenses)}</div></div>
                              <div class="row"><div class="col-5" data-i18n="net_sale_amount">Net Sale Amount</div><div class="col-7 fw-bold">${fmt(sale.net_sale_amount)}</div></div>
                            `
                                : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`
                            }
                          </div>
                        </div>
                      </div>
                      <div class="col-md-6">
                        <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                          <div class="card-body p-4">
                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="notes">Notes</h6>
                            <div>${sale?.notes || "-"}</div>
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
}
