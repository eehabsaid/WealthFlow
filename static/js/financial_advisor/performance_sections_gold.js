"use strict";

// Performance tab — Gold overview hero + gold chart/exposure row builders.
// Split out of performance.js (200-line backlog). Bare globals; takes a
// pre-computed context object built by renderPerformanceView.
// ════════════════════════════════════════════════════════════════════════════

function buildGoldOverviewSection(ctx) {
  const { gold, goldTrend7, goldTrend7Icon, goldTrend7BadgeBg, goldTrend7BadgeColor,
    goldTrend30, goldTrend30Icon, goldTrend30BadgeBg, goldTrend30BadgeColor } = ctx;
  return `
        <!-- 1. Gold Performance Overview (Hero Section) -->
        <div class="mb-4">
          <div class="card border-0 p-3" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
            <div class="d-flex align-items-center mb-3">
              <span class="badge rounded-circle bg-primary me-2 d-inline-flex justify-content-center align-items-center" style="width:24px; height:24px; font-size:12px;">1</span>
              <h6 class="m-0 fw-bold" style="color:var(--text-primary);" data-i18n="performance_gold_overview_title">Gold Performance Overview</h6>
            </div>
            <div class="row g-3">
              <!-- Current Price Box -->
              <div class="col-12 col-md-4">
                <div class="p-3 rounded h-100 d-flex justify-content-between align-items-center" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
                  <div>
                    <div class="small" style="color:var(--text-secondary);" data-i18n="performance_gold_current_24k">Current 24K Gold Price</div>
                    <div class="fs-4 fw-bold text-primary mt-1">${formatMoneyEgp(gold.current_price_24k)}</div>
                    <div class="extra-small mt-1" style="color:var(--text-secondary);"><span data-i18n="performance_per_gram">per gram</span> &bull; <span data-i18n="performance_latest_update">Latest update:</span> ${gold.latest_update || ""}</div>
                  </div>
                  <div class="fs-1 text-warning opacity-75">
                    <i class="bi bi-box-seam-fill"></i>
                  </div>
                </div>
              </div>
              <!-- 7-Day Trend Box -->
              <div class="col-12 col-sm-6 col-md-4">
                <div class="p-3 rounded h-100 d-flex flex-column justify-content-between" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
                  <div class="small mb-2" style="color:var(--text-secondary);" data-i18n="performance_trend_7d">7-Day Trend</div>
                  <div class="d-flex align-items-center justify-content-between">
                    <span class="badge px-3 py-2 fs-6 fw-bold" style="background:${goldTrend7BadgeBg}; color:${goldTrend7BadgeColor};">
                      <i class="bi ${goldTrend7Icon} me-1"></i>${goldTrend7 >= 0 ? "+" : ""}${goldTrend7.toFixed(2)}%
                    </span>
                    <i class="bi bi-graph-up-arrow fs-3 opacity-50" style="color:${goldTrend7BadgeColor};"></i>
                  </div>
                </div>
              </div>
              <!-- 30-Day Trend Box -->
              <div class="col-12 col-sm-6 col-md-4">
                <div class="p-3 rounded h-100 d-flex flex-column justify-content-between" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
                  <div class="small mb-2" style="color:var(--text-secondary);" data-i18n="performance_trend_30d">30-Day Trend</div>
                  <div class="d-flex align-items-center justify-content-between">
                    <span class="badge px-3 py-2 fs-6 fw-bold" style="background:${goldTrend30BadgeBg}; color:${goldTrend30BadgeColor};">
                      <i class="bi ${goldTrend30Icon} me-1"></i>${goldTrend30 >= 0 ? "+" : ""}${goldTrend30.toFixed(2)}%
                    </span>
                    <i class="bi bi-graph-down-arrow fs-3 opacity-50" style="color:${goldTrend30BadgeColor};"></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>`;
}

function buildGoldChartExposureRow(ctx) {
  const { hasGoldHistory, goldTimeframe, impact7d, impact30d, hasCurrHistory,
    currencyTimeframe, selectedCurrency } = ctx;
  return `
        <!-- 2 & 3: Main Row 1 - Gold Chart & Exposure -->
        <div class="row g-4 mb-4">
          <!-- 2. Gold Performance Chart (Left Col - Wider) -->
          <div class="col-12 col-lg-8">
            <div class="card border-0 p-3 h-100 d-flex flex-column" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                <div class="d-flex align-items-center">
                  <span class="badge rounded-circle bg-primary me-2 d-inline-flex justify-content-center align-items-center" style="width:24px; height:24px; font-size:12px;">2</span>
                  <h6 class="m-0 fw-bold" style="color:var(--text-primary);" data-i18n="performance_gold_chart_title">Gold Performance (24K)</h6>
                </div>
                <div class="btn-group btn-group-sm" role="group" id="fa-gold-tf-group">
                  <button type="button" class="btn btn-outline-secondary ${goldTimeframe === "7D" ? "active" : ""}" data-tf="7D">7D</button>
                  <button type="button" class="btn btn-outline-secondary ${goldTimeframe === "30D" ? "active" : ""}" data-tf="30D">30D</button>
                  <button type="button" class="btn btn-outline-secondary ${goldTimeframe === "90D" ? "active" : ""}" data-tf="90D">90D</button>
                  <button type="button" class="btn btn-outline-secondary ${goldTimeframe === "ALL" ? "active" : ""}" data-tf="ALL">All</button>
                </div>
              </div>
              <div class="flex-grow-1 position-relative" style="min-height:260px;">
                ${
                  hasGoldHistory
                    ? `
                  <canvas id="fa-gold-performance-chart"></canvas>
                `
                    : `
                  <div class="d-flex flex-column justify-content-center align-items-center h-100 py-5" style="color:var(--text-secondary);">
                    <i class="bi bi-bar-chart-steps fs-1 mb-2"></i>
                    <p class="m-0 small" data-i18n="performance_no_gold_history">No gold price history available</p>
                  </div>
                `
                }
              </div>
              ${
                hasGoldHistory
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

          <!-- 3. Your Gold Exposure (Right Col) -->
          <div class="col-12 col-lg-4">
            <div class="card border-0 p-3 h-100 d-flex flex-column justify-content-between" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div>
                <div class="d-flex align-items-center mb-1">
                  <span class="badge rounded-circle bg-primary me-2 d-inline-flex justify-content-center align-items-center" style="width:24px; height:24px; font-size:12px;">3</span>
                  <h6 class="m-0 fw-bold" style="color:var(--text-primary);" data-i18n="performance_exposure_title">Your Gold Exposure (Illustrative)</h6>
                </div>
                <p class="extra-small mb-3 ms-4" style="color:var(--text-secondary);" data-i18n="performance_exposure_note">If recent trends apply to your total gold holding</p>

                <!-- 7-Day Impact Card -->
                <div class="p-3 mb-3 rounded" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
                  <div class="small" style="color:var(--text-secondary);" data-i18n="performance_impact_7d">7-Day Impact</div>
                  <div class="d-flex justify-content-between align-items-center mt-1">
                    <div class="fs-5 fw-bold ${impact7d >= 0 ? "text-success" : "text-danger"}">
                      ${formatImpactEgp(impact7d)}
                    </div>
                    <div class="rounded p-2" style="background:${impact7d >= 0 ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)"};">
                      <i class="bi ${impact7d >= 0 ? "bi-arrow-up-right text-success" : "bi-arrow-down-right text-danger"} fs-5"></i>
                    </div>
                  </div>
                </div>

                <!-- 30-Day Impact Card -->
                <div class="p-3 mb-3 rounded" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
                  <div class="small" style="color:var(--text-secondary);" data-i18n="performance_impact_30d">30-Day Impact</div>
                  <div class="d-flex justify-content-between align-items-center mt-1">
                    <div class="fs-5 fw-bold ${impact30d >= 0 ? "text-success" : "text-danger"}">
                      ${formatImpactEgp(impact30d)}
                    </div>
                    <div class="rounded p-2" style="background:${impact30d >= 0 ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)"};">
                      <i class="bi ${impact30d >= 0 ? "bi-arrow-up-right text-success" : "bi-arrow-down-right text-danger"} fs-5"></i>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Disclaimer Alert -->
              <div class="alert alert-secondary m-0 extra-small py-2 px-3 d-flex align-items-start gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color); color:var(--text-secondary);">
                <i class="bi bi-info-circle text-primary mt-1"></i>
                <span data-i18n="performance_exposure_disclaimer">These amounts are illustrative only and not financial forecasts or guarantees.</span>
              </div>
            </div>
          </div>
        </div>`;
}
