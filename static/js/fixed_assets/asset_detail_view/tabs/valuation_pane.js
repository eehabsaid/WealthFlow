"use strict";
// Real-estate asset detail modal: Valuation History tab pane HTML fragment.
// Split out of furniture_valuation_mortgage_rental_sale_tabs.js
// (200-line rule). Do not edit directly.

function buildValuationHistoryPaneHtml(valuationHistory) {
  if (!valuationHistory.length) return "";
  return `
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
                  `;
}
