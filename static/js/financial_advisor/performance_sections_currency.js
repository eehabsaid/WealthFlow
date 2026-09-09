"use strict";

// Performance tab — exchange rate chart + currency analysis row builder.
// Split out of performance.js (200-line backlog). Bare globals; takes a
// pre-computed context object built by renderPerformanceView.
// ════════════════════════════════════════════════════════════════════════════

function buildCurrencyChartAnalysisRow(ctx) {
  const { hasCurrHistory, selectedCurrency, currencyTimeframe, currRate,
    currTrend7, currTrend30, currTrend90 } = ctx;
  return `
        <!-- 4 & 5: Main Row 2 - Currency Chart & Analysis -->
        <div class="row g-4">
          <!-- 4. Exchange Rate Performance Chart (Single Unified Chart) -->
          <div class="col-12 col-lg-8">
            <div class="card border-0 p-3 h-100 d-flex flex-column" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                <div class="d-flex align-items-center gap-2">
                  <span class="badge rounded-circle bg-primary d-inline-flex justify-content-center align-items-center" style="width:24px; height:24px; font-size:12px;">4</span>
                  <h6 class="m-0 fw-bold" style="color:var(--text-primary);" data-i18n="performance_exchange_rate_chart_title">Exchange Rate Performance</h6>
                  <!-- Currency Selector Dropdown -->
                  <select class="form-select form-select-sm ms-2" id="fa-curr-select" style="width:auto; background:var(--bg-tertiary); color:var(--text-primary); border-color:var(--border-color);">
                    <option value="USD" ${selectedCurrency === "USD" ? "selected" : ""}>🇺🇸 USD</option>
                    <option value="EUR" ${selectedCurrency === "EUR" ? "selected" : ""}>🇪🇺 EUR</option>
                    <option value="SAR" ${selectedCurrency === "SAR" ? "selected" : ""}>🇸🇦 SAR</option>
                  </select>
                </div>
                <div class="btn-group btn-group-sm" role="group" id="fa-curr-tf-group">
                  <button type="button" class="btn btn-outline-secondary ${currencyTimeframe === "7D" ? "active" : ""}" data-tf="7D">7D</button>
                  <button type="button" class="btn btn-outline-secondary ${currencyTimeframe === "30D" ? "active" : ""}" data-tf="30D">30D</button>
                  <button type="button" class="btn btn-outline-secondary ${currencyTimeframe === "90D" ? "active" : ""}" data-tf="90D">90D</button>
                  <button type="button" class="btn btn-outline-secondary ${currencyTimeframe === "ALL" ? "active" : ""}" data-tf="ALL">All</button>
                </div>
              </div>
              <div class="flex-grow-1 position-relative" style="min-height:260px;">
                ${
                  hasCurrHistory
                    ? `
                  <canvas id="fa-currency-performance-chart"></canvas>
                `
                    : `
                  <div class="d-flex flex-column justify-content-center align-items-center h-100 py-5" style="color:var(--text-secondary);">
                    <i class="bi bi-graph-down fs-1 mb-2"></i>
                    <p class="m-0 small" data-i18n="performance_currency_disclaimer_snapshot">Historical rate data is unavailable yet. Showing current exchange rate snapshot.</p>
                  </div>
                `
                }
              </div>
              ${
                hasCurrHistory
                  ? `
                <div class="mt-2 extra-small d-flex gap-3 justify-content-center" style="color:var(--text-secondary);">
                  <span><i class="bi bi-dash-lg text-warning"></i> <span data-i18n="performance_ma_short_label">MA Short: 7-Day Moving Average</span></span>
                  <span><i class="bi bi-dash-lg text-info"></i> <span data-i18n="performance_ma_long_label">MA Long: 30-Day Moving Average</span></span>
                </div>
              `
                  : ""
              }
            </div>
          </div>

          <!-- 5. Currency Analysis (Right Col) -->
          <div class="col-12 col-lg-4">
            <div class="card border-0 p-3 h-100 d-flex flex-column justify-content-between" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div>
                <div class="d-flex justify-content-between align-items-center mb-3">
                  <div class="d-flex align-items-center">
                    <span class="badge rounded-circle bg-primary me-2 d-inline-flex justify-content-center align-items-center" style="width:24px; height:24px; font-size:12px;">5</span>
                    <h6 class="m-0 fw-bold" style="color:var(--text-primary);" data-i18n="performance_currency_analysis_title">Currency Analysis</h6>
                  </div>
                  <span class="badge ${hasCurrHistory ? "bg-success-subtle text-success" : "bg-warning-subtle text-warning"}" data-i18n="${hasCurrHistory ? "performance_history_available_badge" : "performance_snapshot_view_badge"}">
                    ${hasCurrHistory ? "Historical data available" : "Snapshot view"}
                  </span>
                </div>

                <!-- Currency Tab Switcher -->
                <ul class="nav nav-pills nav-fill mb-3" id="fa-curr-analysis-tabs" style="background:var(--bg-tertiary); padding:4px; border-radius:8px;">
                  <li class="nav-item">
                    <button class="nav-link btn-sm py-1 ${selectedCurrency === "USD" ? "active" : ""}" data-curr="USD">USD</button>
                  </li>
                  <li class="nav-item">
                    <button class="nav-link btn-sm py-1 ${selectedCurrency === "EUR" ? "active" : ""}" data-curr="EUR">EUR</button>
                  </li>
                  <li class="nav-item">
                    <button class="nav-link btn-sm py-1 ${selectedCurrency === "SAR" ? "active" : ""}" data-curr="SAR">SAR</button>
                  </li>
                </ul>

                <!-- Details Panel -->
                <div class="p-3 rounded mb-3" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
                  <div class="d-flex justify-content-between align-items-baseline mb-2">
                    <div class="small" style="color:var(--text-secondary);" data-i18n="performance_current_rate_label">Current Rate</div>
                    <div class="fs-4 fw-bold text-primary">${formatRateEgp(currRate)}</div>
                  </div>

                  ${
                    hasCurrHistory
                      ? `
                    <hr style="border-color:var(--border-color); margin:8px 0;">
                    <div class="d-flex justify-content-between align-items-center py-1">
                      <span class="extra-small" style="color:var(--text-secondary);" data-i18n="performance_trend_7d">7-Day Change</span>
                      <span class="fw-bold extra-small ${currTrend7 >= 0 ? "text-success" : "text-danger"}">
                        ${currTrend7 >= 0 ? "+" : ""}${currTrend7.toFixed(2)}%
                      </span>
                    </div>
                    <div class="d-flex justify-content-between align-items-center py-1">
                      <span class="extra-small" style="color:var(--text-secondary);" data-i18n="performance_trend_30d">30-Day Change</span>
                      <span class="fw-bold extra-small ${currTrend30 >= 0 ? "text-success" : "text-danger"}">
                        ${currTrend30 >= 0 ? "+" : ""}${currTrend30.toFixed(2)}%
                      </span>
                    </div>
                    <div class="d-flex justify-content-between align-items-center py-1">
                      <span class="extra-small" style="color:var(--text-secondary);" data-i18n="performance_trend_90d">90-Day Change</span>
                      <span class="fw-bold extra-small ${currTrend90 >= 0 ? "text-success" : "text-danger"}">
                        ${currTrend90 >= 0 ? "+" : ""}${currTrend90.toFixed(2)}%
                      </span>
                    </div>
                  `
                      : ""
                  }
                </div>
              </div>

              <!-- Currency Disclaimer Alert -->
              <div class="alert alert-secondary m-0 extra-small py-2 px-3 d-flex align-items-start gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color); color:var(--text-secondary);">
                <i class="bi bi-info-circle text-primary mt-1"></i>
                <span data-i18n="${hasCurrHistory ? "performance_currency_disclaimer_history" : "performance_currency_disclaimer_snapshot"}">
                  ${hasCurrHistory ? "Exchange rate performance against EGP based on historical data." : "Historical rate data is unavailable yet. Showing current exchange rate snapshot."}
                </span>
              </div>
            </div>
          </div>
        </div>`;
}
