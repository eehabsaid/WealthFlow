"use strict";
// Sale modal rendering.
// Part of the fixed_assets module (split from the former monolithic
// validation.js, 200-line rule). Do not edit directly.

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

                            <div class="d-grid gap-2">
                              <div class="d-flex justify-content-between"><span data-i18n="asset_type">Asset Type</span><span id="details_asset_type" class="fw-bold"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_date">Purchase Date</span><span id="details_purchase_date"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="valuation_source">Valuation Source</span><span id="details_valuation_source"></span></div>
                            </div>

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

                            <div class="d-grid gap-2">
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_price_egp">Purchase Price</span><span id="details_purchase_price" class="fw-bold"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_price_usd">Purchase USD</span><span id="details_purchase_usd"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="last_valuation_date">Last Valuation</span><span id="details_last_valuation"></span></div>
                            </div>

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

