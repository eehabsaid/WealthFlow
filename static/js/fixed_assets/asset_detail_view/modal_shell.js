"use strict";
// Assembles the full real-estate asset detail modal HTML: header, summary
// cards, tab nav, and the tab-content wrapper. Delegates the actual tab
// panes to the sibling builder functions below (each returns a string that
// is concatenated in, preserving the exact original markup/ordering):
// - general_property_tabs.js
// - photos_renovation_acquisition_tabs.js
// - furniture_valuation_mortgage_rental_sale_tabs.js (also closes the
//   tab-content wrapper + renders the photo overlay + modal footer, since
//   that markup was part of the same original template literal)

function buildRealEstateModalHtml(ctx) {
  const {
    asset, gainValue, gainClass, photos, renovations, furniture,
    valuationHistory, sale, mortgage, rental, utilitiesBadges, featuresBadges,
  } = ctx;

  return `
    <div class="modal-header border-0 pb-0">
        <h5 class="modal-title fixed-assets-heading" data-i18n="asset_details">Asset Details</h5>
        <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
    </div>

    <div class="modal-body asset-modal-body p-0">
        <div class="p-4">
            <div class="asset-detail-header mb-4">
                <div class="d-flex flex-column flex-lg-row gap-3 align-items-start">
                    <div class="asset-header-icon d-flex align-items-center justify-content-center">
                        <i class="bi bi-building"></i>
                    </div>
                    <div class="flex-fill">
                        <div class="d-flex flex-column flex-sm-row justify-content-between gap-3 align-items-start align-items-sm-center">
                            <div>
                                <h3 class="asset-title mb-1 fixed-assets-heading">${asset.name || "-"}</h3>
                                <span class="badge rounded-pill asset-type-badge" data-i18n="${fixedAssetTypeToI18nKey(asset.asset_type)}">${asset.asset_type || "-"}</span>
                            </div>
                            <div class="text-sm-end">
                                <div class="small asset-label" data-i18n="current_market_value">Current Market Value</div>
                                <div class="asset-value-large ${gainClass}">${fmt(asset.current_market_value)}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-4 g-3 mb-4">
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="purchase_price_egp">Purchase Price</div>
                        <div class="asset-summary-value">${fmt(asset.purchase_price)}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="purchase_date">Purchase Date</div>
                        <div class="asset-summary-value">${formatDate(asset.purchase_date) || "-"}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="gain_loss">Gain / Loss</div>
                        <div class="asset-summary-value ${gainClass}">${fmt(gainValue)}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="last_valuation_date">Last Valuation Date</div>
                        <div class="asset-summary-value">${formatDate(asset.last_valuation_date) || "-"}</div>
                    </div>
                </div>
                ${
                  mortgage
                    ? `
                <div class="col">
                  <div class="asset-summary-card h-100">
                    <div class="asset-summary-label" data-i18n="net_equity">Net Equity</div>
                    <div class="asset-summary-value">${fmt(mortgage.net_equity)}</div>
                  </div>
                </div>
                `
                    : ""
                }
                ${
                  rental
                    ? `
                <div class="col">
                  <div class="asset-summary-card h-100">
                    <div class="asset-summary-label" data-i18n="rental_yield">Rental Yield</div>
                    <div class="asset-summary-value">${fmtpresent(rental.rental_yield)}%</div>
                  </div>
                </div>
                `
                    : ""
                }
            </div>

            <ul class="nav nav-pills nav-fill mb-4 asset-detail-tabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="asset-general-tab" data-bs-toggle="tab" data-bs-target="#asset-general-pane" type="button" role="tab" aria-controls="asset-general-pane" aria-selected="true" data-i18n="general">General</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-property-tab" data-bs-toggle="tab" data-bs-target="#asset-property-pane" type="button" role="tab" aria-controls="asset-property-pane" aria-selected="false" data-i18n="property">Property</button>
                </li>
              <li class="nav-item" role="presentation">
                <button class="nav-link" id="asset-photos-tab" data-bs-toggle="tab" data-bs-target="#asset-photos-pane" type="button" role="tab" aria-controls="asset-photos-pane" aria-selected="false" data-i18n="photos">Photos</button>
              </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-renovation-tab" data-bs-toggle="tab" data-bs-target="#asset-renovation-pane" type="button" role="tab" aria-controls="asset-renovation-pane" aria-selected="false" data-i18n="renovations">Renovations</button>
                </li>
                ${
                  isRealEstateAssetType(asset.asset_type)
                    ? `
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-acquisition-tab" data-bs-toggle="tab" data-bs-target="#asset-acquisition-pane" type="button" role="tab" aria-controls="asset-acquisition-pane" aria-selected="false" data-i18n="acquisition_costs">Acquisition Costs</button>
                </li>
                `
                    : ""
                }
                ${
                  furniture.length
                    ? `
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-furniture-tab" data-bs-toggle="tab" data-bs-target="#asset-furniture-pane" type="button" role="tab" aria-controls="asset-furniture-pane" aria-selected="false" data-i18n="furniture">Furniture</button>
                </li>
                `
                    : ""
                }
                ${
                  valuationHistory.length
                    ? `
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-valuation-tab" data-bs-toggle="tab" data-bs-target="#asset-valuation-pane" type="button" role="tab" aria-controls="asset-valuation-pane" aria-selected="false" data-i18n="valuation_history">Valuation History</button>
                </li>
                `
                    : ""
                }
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-mortgage-tab" data-bs-toggle="tab" data-bs-target="#asset-mortgage-pane" type="button" role="tab" aria-controls="asset-mortgage-pane" aria-selected="false" data-i18n="mortgage">Mortgage</button>
                </li>
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-rental-tab" data-bs-toggle="tab" data-bs-target="#asset-rental-pane" type="button" role="tab" aria-controls="asset-rental-pane" aria-selected="false" data-i18n="rental">Rental</button>
                </li>
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-sale-tab" data-bs-toggle="tab" data-bs-target="#asset-sale-pane" type="button" role="tab" aria-controls="asset-sale-pane" aria-selected="false" data-i18n="sale">Sale</button>
                </li>
            </ul>

            <div class="tab-content" id="assetDetailsTabsContent">
${buildGeneralPropertyTabsHtml(ctx)}
${buildPhotosRenovationAcquisitionTabsHtml(ctx)}
${buildFurnitureValuationMortgageRentalSaleTabsHtml(ctx)}
`;
}
