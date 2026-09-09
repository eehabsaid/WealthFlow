"use strict";

// Performance tab — view orchestrator. Computes the render context and
// assembles the section builders into the final page markup. Split out of
// performance.js (200-line backlog).
// ════════════════════════════════════════════════════════════════════════════

function renderPerformanceView(container) {
  if (!_performanceData) return;
  const gold = _performanceData.gold || {};
  const currencies = _performanceData.currencies || {};
  const currData = currencies.data || {};
  const hasCurrHistory = currencies.rate_history_available;

  const goldTrend7 = gold.trend_7d || 0;
  const goldTrend30 = gold.trend_30d || 0;
  const goldTrend7Icon = goldTrend7 >= 0 ? "bi-arrow-up-right" : "bi-arrow-down-right";
  const goldTrend7BadgeBg = goldTrend7 >= 0 ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)";
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

  const ctx = {
    gold,
    hasCurrHistory,
    goldTrend7,
    goldTrend7Icon,
    goldTrend7BadgeBg,
    goldTrend7BadgeColor,
    goldTrend30,
    goldTrend30Icon,
    goldTrend30BadgeBg,
    goldTrend30BadgeColor,
    impact7d,
    impact30d,
    currRate,
    currTrend7,
    currTrend30,
    currTrend90,
    hasGoldHistory,
    goldTimeframe: _goldTimeframe,
    currencyTimeframe: _currencyTimeframe,
    selectedCurrency: _selectedCurrency,
  };

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
${buildGoldOverviewSection(ctx)}
${buildGoldChartExposureRow(ctx)}
${buildCurrencyChartAnalysisRow(ctx)}
      </div>
    `;

  if (typeof applyTranslations === "function") applyTranslations();
  attachPerformanceEventListeners(container);

  // Render Charts
  if (hasGoldHistory) renderPerfGoldChart(gold);
  if (hasCurrHistory) renderPerfCurrencyChart(currData[_selectedCurrency] || {});
}
