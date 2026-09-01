"use strict";

(function () {
  let _performanceData = null;
  let _goldTimeframe = "30D";
  let _currencyTimeframe = "30D";
  let _selectedCurrency = "USD";
  let _goldChartInstance = null;
  let _currencyChartInstance = null;

  function formatMoneyEgp(val) {
    const num = Number(val) || 0;
    if (typeof fmtpresent === "function") {
      return `EGP ${fmtpresent(num)}`;
    }
    return `EGP ${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function formatImpactEgp(val) {
    const num = Number(val) || 0;
    const sign = num >= 0 ? "+" : "-";
    const absVal = Math.abs(num);
    if (typeof fmtpresent === "function") {
      return `${sign}EGP ${fmtpresent(absVal)}`;
    }
    return `${sign}EGP ${absVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function formatRateEgp(val) {
    const num = Number(val) || 0;
    return `${num.toFixed(2)} EGP`;
  }

  async function loadPerformance() {
    const container = document.getElementById("fa-pane-performance");
    if (!container) return;

    container.innerHTML = `
      <div class="d-flex justify-content-center align-items-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    `;

    try {
      const response = await fetch("/api/financial-advisor/performance/");
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      _performanceData = await response.json();
      renderPerformanceView(container);
    } catch (err) {
      console.error("Failed to load performance data:", err);
      container.innerHTML = `
        <div class="alert alert-danger my-3" role="alert">
          Failed to load Performance data. Please try again.
        </div>
      `;
    }
  }

  function renderPerformanceView(container) {
    if (!_performanceData) return;
    const gold = _performanceData.gold || {};
    const currencies = _performanceData.currencies || {};
    const currData = currencies.data || {};
    const hasCurrHistory = currencies.rate_history_available;

    const goldTrend7 = gold.trend_7d || 0;
    const goldTrend30 = gold.trend_30d || 0;
    const goldTrend7Icon = goldTrend7 >= 0 ? "bi-arrow-up-right" : "bi-arrow-down-right";
    const goldTrend7BadgeBg =
      goldTrend7 >= 0 ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)";
    const goldTrend7BadgeColor =
      goldTrend7 >= 0 ? "var(--accent-green, #22c55e)" : "var(--accent-red, #ef4444)";

    const goldTrend30Icon = goldTrend30 >= 0 ? "bi-arrow-up-right" : "bi-arrow-down-right";
    const goldTrend30BadgeBg =
      goldTrend30 >= 0 ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)";
    const goldTrend30BadgeColor =
      goldTrend30 >= 0 ? "var(--accent-green, #22c55e)" : "var(--accent-red, #ef4444)";

    const exposure = gold.exposure || {};
    const impact7d = exposure.impact_7d || 0;
    const impact30d = exposure.impact_30d || 0;

    const activeCurrencyObj = currData[_selectedCurrency] || currData["USD"] || {};
    const currRate = activeCurrencyObj.current_rate || 0;
    const currTrend7 = activeCurrencyObj.trend_7d || 0;
    const currTrend30 = activeCurrencyObj.trend_30d || 0;
    const currTrend90 = activeCurrencyObj.trend_90d || 0;

    const goldTimeseries = gold.timeseries || [];
    const hasGoldHistory = goldTimeseries.length > 0;

    container.innerHTML = `
      <div class="container-fluid p-0">
        <!-- Sub-header & Unit Bar -->
        <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-2 gap-2">
          <div>
            <p class="m-0 small" style="color:var(--text-secondary);" data-i18n="performance_header_subtitle">Analyze historical performance of key assets and currencies</p>
          </div>
          <div class="d-flex align-items-center gap-3">
            <span class="small d-flex align-items-center gap-1" style="color:var(--text-secondary);">
              <i class="bi bi-info-circle"></i>
              <span data-i18n="performance_all_values_egp">All values in EGP unless otherwise stated</span>
            </span>
          </div>
        </div>

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
        </div>

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
                  <button type="button" class="btn btn-outline-secondary ${_goldTimeframe === "7D" ? "active" : ""}" data-tf="7D">7D</button>
                  <button type="button" class="btn btn-outline-secondary ${_goldTimeframe === "30D" ? "active" : ""}" data-tf="30D">30D</button>
                  <button type="button" class="btn btn-outline-secondary ${_goldTimeframe === "90D" ? "active" : ""}" data-tf="90D">90D</button>
                  <button type="button" class="btn btn-outline-secondary ${_goldTimeframe === "ALL" ? "active" : ""}" data-tf="ALL">All</button>
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
        </div>

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
                    <option value="USD" ${_selectedCurrency === "USD" ? "selected" : ""}>🇺🇸 USD</option>
                    <option value="EUR" ${_selectedCurrency === "EUR" ? "selected" : ""}>🇪🇺 EUR</option>
                    <option value="SAR" ${_selectedCurrency === "SAR" ? "selected" : ""}>🇸🇦 SAR</option>
                  </select>
                </div>
                <div class="btn-group btn-group-sm" role="group" id="fa-curr-tf-group">
                  <button type="button" class="btn btn-outline-secondary ${_currencyTimeframe === "7D" ? "active" : ""}" data-tf="7D">7D</button>
                  <button type="button" class="btn btn-outline-secondary ${_currencyTimeframe === "30D" ? "active" : ""}" data-tf="30D">30D</button>
                  <button type="button" class="btn btn-outline-secondary ${_currencyTimeframe === "90D" ? "active" : ""}" data-tf="90D">90D</button>
                  <button type="button" class="btn btn-outline-secondary ${_currencyTimeframe === "ALL" ? "active" : ""}" data-tf="ALL">All</button>
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
                    <button class="nav-link btn-sm py-1 ${_selectedCurrency === "USD" ? "active" : ""}" data-curr="USD">USD</button>
                  </li>
                  <li class="nav-item">
                    <button class="nav-link btn-sm py-1 ${_selectedCurrency === "EUR" ? "active" : ""}" data-curr="EUR">EUR</button>
                  </li>
                  <li class="nav-item">
                    <button class="nav-link btn-sm py-1 ${_selectedCurrency === "SAR" ? "active" : ""}" data-curr="SAR">SAR</button>
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
        </div>
      </div>
    `;

    if (typeof applyTranslations === "function") applyTranslations();
    attachPerformanceEventListeners(container);

    // Render Charts
    if (hasGoldHistory) renderGoldChart(gold);
    if (hasCurrHistory) renderCurrencyChart(currData[_selectedCurrency] || {});
  }

  function attachPerformanceEventListeners(container) {
    // Gold Timeframe Buttons
    const goldTfGroup = container.querySelector("#fa-gold-tf-group");
    if (goldTfGroup) {
      goldTfGroup.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          _goldTimeframe = e.target.getAttribute("data-tf") || "30D";
          goldTfGroup.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
          e.target.classList.add("active");
          if (_performanceData && _performanceData.gold) {
            renderGoldChart(_performanceData.gold);
          }
        });
      });
    }

    // Single Currency Selector Dropdown (Updates same chart and analysis panel)
    const currSelect = container.querySelector("#fa-curr-select");
    if (currSelect) {
      currSelect.addEventListener("change", (e) => {
        _selectedCurrency = e.target.value;
        renderPerformanceView(container);
      });
    }

    // Currency Timeframe Buttons
    const currTfGroup = container.querySelector("#fa-curr-tf-group");
    if (currTfGroup) {
      currTfGroup.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          _currencyTimeframe = e.target.getAttribute("data-tf") || "30D";
          currTfGroup.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
          e.target.classList.add("active");
          if (_performanceData && _performanceData.currencies && _performanceData.currencies.data) {
            renderCurrencyChart(_performanceData.currencies.data[_selectedCurrency] || {});
          }
        });
      });
    }

    // Currency Analysis Tabs (Synchronized with dropdown)
    const currAnalysisTabs = container.querySelector("#fa-curr-analysis-tabs");
    if (currAnalysisTabs) {
      currAnalysisTabs.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          _selectedCurrency = e.target.getAttribute("data-curr") || "USD";
          renderPerformanceView(container);
        });
      });
    }
  }

  function renderGoldChart(goldObj) {
    if (typeof window.renderGoldChart === "function") {
      _goldChartInstance = window.renderGoldChart(goldObj, _goldTimeframe);
    }
  }

  function renderCurrencyChart(currObj) {
    if (typeof window.renderCurrencyChart === "function") {
      _currencyChartInstance = window.renderCurrencyChart(
        currObj,
        _currencyTimeframe,
        _selectedCurrency
      );
    }
  }

  window.loadPerformance = loadPerformance;
})();
