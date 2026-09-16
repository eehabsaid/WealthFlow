"use strict";
// Real-estate asset detail modal: Mortgage + Rental tab panes HTML fragment.
// Split out of furniture_valuation_mortgage_rental_sale_tabs.js
// (200-line rule). Do not edit directly.

function buildMortgageRentalPanesHtml(mortgage, rental) {
  return `<div class="tab-pane fade" id="asset-mortgage-pane" role="tabpanel" aria-labelledby="asset-mortgage-tab">
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

                  `;
}
