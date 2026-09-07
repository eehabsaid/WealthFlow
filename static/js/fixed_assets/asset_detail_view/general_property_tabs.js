"use strict";
// Real-estate asset detail modal: General + Property tab panes.

function buildGeneralPropertyTabsHtml(ctx) {
  const { asset, gainValue, gainClass, utilitiesBadges, featuresBadges } = ctx;
  return `
                <div class="tab-pane fade show active" id="asset-general-pane" role="tabpanel" aria-labelledby="asset-general-tab">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="general_information">General Information</h6>
                                                          
                                    <div class="row mb-2"><div class="col-5 fixed-assets-section-title" data-i18n="asset_type">Asset Type</div><div class="col-7">${asset.asset_type || "-"}</div></div>
                                    <div class="row mb-2"><div class="col-5 fixed-assets-section-title" data-i18n="asset_name">Asset Name</div><div class="col-7">${asset.name || "-"}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_date">Purchase Date</div><div class="col-7">${formatDate(asset.purchase_date) || "-"}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="valuation_source">Valuation Source</div><div class="col-7">${asset.valuation_source || "-"}</div></div>
                                    <div class="row"><div class="col-5" data-i18n="notes">Notes</div><div class="col-7">${asset.notes || "-"}</div></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="valuation_summary">Valuation Summary</h6>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_price_egp">Purchase Price</div><div class="col-7 fw-bold">${fmt(asset.purchase_price)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_price_usd">Purchase Price (USD)</div><div class="col-7 fw-bold">${fmt(asset.purchase_price_usd)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="acquisition_costs_egp">Acquisition Costs</div><div class="col-7 fw-bold">${fmt(asset.total_acquisition_costs || 0)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="renovation_costs_egp">Renovation Costs</div><div class="col-7 fw-bold">${fmt(asset.total_renovation_costs || 0)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="total_investment_egp">Total Investment</div><div class="col-7 fw-bold">${fmt(asset.total_investment || asset.purchase_price)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="current_market_value">Current Market Value</div><div class="col-7 fw-bold">${fmt(asset.current_market_value)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="last_valuation_date">Last Valuation Date</div><div class="col-7">${formatDate(asset.last_valuation_date) || "-"}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="gain_loss">Gain / Loss</div><div class="col-7 fw-bold ${gainClass}">${fmt(gainValue)}</div></div>
                                    <div class="row"><div class="col-5" data-i18n="gain_percent">Gain (%)</div><div class="col-7 fw-bold ${gainClass}">${asset.total_investment || asset.purchase_price ? fmtpresent((gainValue / (asset.total_investment || asset.purchase_price)) * 100) + "%" : "-"}</div></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="asset-property-pane" role="tabpanel" aria-labelledby="asset-property-tab">
                    <div class="row g-3">
                        <div class="col-xl-7">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="property_details">Property Details</h6>
                                    <div class="row row-cols-1 row-cols-sm-2 row-cols-xl-3 g-3">
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="country">Country</span><span class="value">${asset.real_estate?.country || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="governorate">Governorate</span><span class="value">${asset.real_estate?.governorate || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="city">City</span><span class="value">${asset.real_estate?.city || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="district">District</span><span class="value">${asset.real_estate?.district || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="address">Address</span><span class="value">${asset.real_estate?.address || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="apt_area">Property Area</span><span class="value">${asset.real_estate?.apartment_area || "-"} m²</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="land_area">Land Area</span><span class="value">${asset.real_estate?.land_area || "-"} m²</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="rooms">Bedrooms</span><span class="value">${asset.real_estate?.rooms || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="bathrooms">Bathrooms</span><span class="value">${asset.real_estate?.bathrooms || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="floor">Floor Number</span><span class="value">${asset.real_estate?.floor || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="building_floors">Total Building Floors</span><span class="value">${asset.real_estate?.building_floors || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="building_year">Construction Year</span><span class="value">${asset.real_estate?.building_year || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="facades">Facade</span><span class="value">${asset.real_estate?.facades || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="furnished_status">Furnished Status</span><span class="value">${asset.real_estate?.furnished_status || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="finishing_level">Finishing Level</span><span class="value">${asset.real_estate?.finishing_level || "-"}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="land_share">Land Share</span><span class="value">${asset.real_estate?.land_share || "-"}</span></div></div>
                                    </div>
                                    <div class="asset-attribute-row mt-3"><span class="label" data-i18n="description">Description</span><span class="value">${asset.real_estate?.description || "-"}</span></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-xl-5">
                            <div class="row g-3">
                                <div class="col-12">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="location">Location</h6>
                                            <div id="assetPropertyMap" class="asset-main-photo-container" style="height:280px;"></div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="utilities">Utilities</h6>
                                            <div class="d-flex flex-wrap gap-2">
                                              ${utilitiesBadges || `<span class="small" style="color:var(--text-secondary);" data-i18n="no_data">No data available</span>`}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="features">Features</h6>
                                            <div class="d-flex flex-wrap gap-2">
                                              ${featuresBadges || `<span class="small" style="color:var(--text-secondary);" data-i18n="no_data">No data available</span>`}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                            </div>
                        </div>
                    </div>
                </div>
`;
}
