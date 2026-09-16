"use strict";
// Real-estate asset detail modal: Furniture tab pane HTML fragment.
// Split out of furniture_valuation_mortgage_rental_sale_tabs.js
// (200-line rule). Do not edit directly.

function buildFurniturePaneHtml(furniture, asset) {
  if (!furniture.length) return "";
  return `
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
                  `;
}
