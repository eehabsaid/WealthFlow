"use strict";
// Real-estate asset detail modal: Sale tab pane, photo-overlay markup, and
// modal footer (kept together since they close out the same template
// literal as the original monolithic function).
// Split out of furniture_valuation_mortgage_rental_sale_tabs.js
// (200-line rule). Do not edit directly.

function buildSalePaneAndFooterHtml(sale) {
  return `<div class="tab-pane fade" id="asset-sale-pane" role="tabpanel" aria-labelledby="asset-sale-tab">
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
