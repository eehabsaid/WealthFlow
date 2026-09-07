"use strict";
// Real-estate asset detail modal: Photos + Renovations + Acquisition Costs tab panes.

function buildPhotosRenovationAcquisitionTabsHtml(ctx) {
  const { asset, photos, renovations } = ctx;
  return `
                <div class="tab-pane fade" id="asset-photos-pane" role="tabpanel" aria-labelledby="asset-photos-tab">
                  <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                    <div class="card-body p-4">
                      <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="property_photos">Photo Gallery</h6>
                      <div id="assetMainPhotoContainer" class="asset-main-photo-container mb-3" style="justify-content:center;">
                        ${photos.length ? `<img id="assetMainPhoto" src="${photos[0].url}" alt="Asset photo" class="img-fluid" style="max-height:100%;max-width:100%;cursor:pointer;" />` : `<div class="text-center" data-i18n="no_property_photos">No photos available</div>`}
                      </div>
                      <div class="asset-photo-grid">
                        ${
                          photos.length
                            ? photos
                                .slice(1)
                                .map(
                                  (photo, index) => `
                          <button type="button" class="btn btn-sm asset-photo-thumbnail p-0" data-url="${photo.url}" aria-label="Photo ${index + 2}">
                            <img src="${photo.url}" alt="Thumbnail ${index + 2}" />
                          </button>
                        `
                                )
                                .join("")
                            : ""
                        }
                      </div>
                    </div>
                  </div>
                </div>
                <div class="tab-pane fade" id="asset-renovation-pane" role="tabpanel" aria-labelledby="asset-renovation-tab">
                    <div class="row g-3">
                        ${
                          renovations.length
                            ? renovations
                                .map(
                                  (r) => `
                            <div class="col-md-6">
                                <div class="asset-renovation-card h-100">
                                    <div class="d-flex justify-content-between gap-3">
                                        <div>
                                            <div class="small mb-2" data-i18n="date">Date</div>
                                            <div class="fw-semibold">${formatDate(r.date) || "-"}</div>
                                            <div class="small mt-2" data-i18n="category">Category</div>
                                            <div data-i18n-prefix="renovation_" data-i18n-value="${(r.category || "").toLowerCase().replace(/ & /g, "_").replace(/ /g, "_")}">${r.category || "-"}</div>
                                        </div>
                                        <div class="text-end">
                                            <div class="small mb-2" data-i18n="amount_usd">Amount USD</div>
                                            <div class="fw-semibold">${fmt(r.amount_usd)}</div>
                                            <div class="small mt-3" data-i18n="amount_egp">Amount</div>
                                            <div class="fw-semibold">${fmt(r.amount_egp)}</div>
                                        </div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="description">Description</div>
                                        <div>${r.description || "-"}</div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="notes">Notes</div>
                                        <div>${r.notes || "-"}</div>
                                    </div>
                                </div>
                            </div>
                        `
                                )
                                .join("")
                            : `
                            <div class="col-12">
                                <div class="text-center py-5" data-i18n="no_renovations">No renovations registered.</div>
                            </div>
                        `
                        }
                        ${
                          renovations.length
                            ? `
                        <div class="col-12">
                            <div class="asset-renovation-card asset-renovation-summary" style="padding: 16px;">
                                <div class="d-flex flex-column gap-2" style="width: 100%;">
                                    
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="total_renovation_cost_usd">Total Renovation Cost USD</div>
                                        <div class="text-end fw-semibold">
                                            $${fmt(renovations.reduce((sum, r) => sum + (parseFloat(r.amount_usd) || 0), 0))}
                                        </div>
                                    </div>

                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="amount_egp">Amount</div>
                                        <div class="text-end fw-semibold">
                                            ${fmt(renovations.reduce((sum, r) => sum + (parseFloat(r.amount_egp) || 0), 0))} <span data-i18n="EGP">EGP</span>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </div>
                        `
                            : ""
                        }
                    </div>
                </div>
                ${
                  isRealEstateAssetType(asset.asset_type)
                    ? `
                <div class="tab-pane fade" id="asset-acquisition-pane" role="tabpanel" aria-labelledby="asset-acquisition-tab">
                    <div class="row g-3">
                        ${
                          (asset.acquisition_costs || []).length
                            ? asset.acquisition_costs
                                .map(
                                  (c) => `
                            <div class="col-md-6">
                                <div class="asset-renovation-card h-100">
                                    <div class="d-flex justify-content-between gap-3">
                                        <div>
                                            <div class="small mb-2" data-i18n="date">Date</div>
                                            <div class="fw-semibold">${formatDate(c.date) || "-"}</div>
                                            <div class="small mt-2" data-i18n="category">Category</div>
                                            <div data-i18n-prefix="acquisition_" data-i18n-value="${(c.category || "").toLowerCase().replace(/ & /g, "_").replace(/ /g, "_")}">${c.category || "-"}</div>
                                        </div>
                                        <div class="text-end">
                                            <div class="small mb-2" data-i18n="amount_usd">Amount USD</div>
                                            <div class="fw-semibold">${fmt(c.amount_usd)}</div>
                                            <div class="small mt-3" data-i18n="amount_egp">Amount</div>
                                            <div class="fw-semibold">${fmt(c.amount_egp)}</div>
                                        </div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="description">Description</div>
                                        <div>${c.description || "-"}</div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="notes">Notes</div>
                                        <div>${c.notes || "-"}</div>
                                    </div>
                                </div>
                            </div>
                        `
                                )
                                .join("")
                            : `
                            <div class="col-12">
                                <div class="text-center py-5" data-i18n="no_acquisition_costs">No acquisition costs registered.</div>
                            </div>
                        `
                        }
                        ${
                          (asset.acquisition_costs || []).length
                            ? `
                        <div class="col-12">
                            <div class="asset-renovation-card asset-renovation-summary" style="padding: 16px;">
                                <div class="d-flex flex-column gap-2" style="width: 100%;">
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="total_acquisition_cost_usd">Total Acquisition Cost USD</div>
                                        <div class="text-end fw-semibold">
                                            $${fmt(asset.acquisition_costs.reduce((sum, c) => sum + (parseFloat(c.amount_usd) || 0), 0))}
                                        </div>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="amount_egp">Amount</div>
                                        <div class="text-end fw-semibold">
                                            ${fmt(asset.acquisition_costs.reduce((sum, c) => sum + (parseFloat(c.amount_egp) || 0), 0))} <span data-i18n="EGP">EGP</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        `
                            : ""
                        }
                    </div>
                </div>
                `
                    : ""
                }
`;
}
