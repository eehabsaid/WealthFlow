"use strict";
window.SP = window.SP || {};


  // ── Requirement 4: Enhanced KPI Cards with Visual Change Indicators ───────

  window.SP.buildDashboardPaneHtml = function() {
    const base = window.SP.state.scenarioPlannerData?.baseline || {};
    const scList = window.SP.state.scenarioPlannerData?.scenarios || [];
    const activeSc = scList.find((s) => s.id === window.SP.state.activeScenarioId) || scList[0] || base;

    // Deltas vs Baseline
    const nwVal = activeSc.net_worth_12m || 0;
    const nwBase = base.net_worth_12m || 0;
    const nwDelta = nwVal - nwBase;

    const flowVal = activeSc.monthly_cash_flow || 0;
    const flowBase = base.monthly_cash_flow || 0;
    const flowDelta = flowVal - flowBase;

    const debtVal = activeSc.total_debt || 0;
    const debtBase = base.total_debt || 0;
    const debtDelta = debtVal - debtBase;

    const covVal = activeSc.cash_coverage_months;
    const covBase = base.cash_coverage_months;
    const covDelta = covVal !== null && covBase !== null ? covVal - covBase : 0;

    const retireObj = activeSc.retirement_readiness || {};
    const readinessPct = retireObj.readiness_pct || 0;
    const baseReadiness = base.retirement_readiness?.readiness_pct || 0;
    const readinessDelta = readinessPct - baseReadiness;

    function _renderKpiBadge(delta, isInverse = false) {
      if (delta === 0 || isNaN(delta)) {
        return `<span class="badge bg-secondary extra-small"><i class="bi bi-dash"></i> Baseline</span>`;
      }
      const isGood = isInverse ? delta < 0 : delta > 0;
      const colorClass = isGood ? "bg-success text-white" : "bg-danger text-white";
      const icon = isGood ? "bi-arrow-up-right" : "bi-arrow-down-right";
      const sign = delta > 0 ? "+" : "";
      return `<span class="badge ${colorClass} extra-small"><i class="bi ${icon}"></i> ${sign}${typeof delta === "number" ? delta.toFixed(1) : delta}</span>`;
    }

    return `
      <div class="d-flex flex-column gap-4">
        <!-- Requirement 4: Enhanced KPI Cards with Visual Change Indicators -->
        <div class="row row-cols-1 row-cols-md-5 g-3">
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_networth">Net Worth (12m)</div>
                ${_renderKpiBadge(nwDelta)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${window.SP.money(nwVal)}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${window.SP.money(nwBase)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_cashflow">Monthly Cash Flow</div>
                ${_renderKpiBadge(flowDelta)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${window.SP.money(flowVal)}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${window.SP.money(flowBase)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_debt">Total Debt</div>
                ${_renderKpiBadge(debtDelta, true)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${window.SP.money(debtVal)}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${window.SP.money(debtBase)}</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_coverage">Cash Coverage</div>
                ${_renderKpiBadge(covDelta)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${covVal !== null && covVal !== undefined ? covVal + " mo" : "-"}</div>
              <div class="extra-small text-muted mt-1">Baseline: ${covBase ?? "-"} mo</div>
            </div>
          </div>
          <div class="col">
            <div class="card border-0 p-3 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between">
                <div class="extra-small text-muted fw-bold uppercase" data-i18n="scenario_planner_kpi_readiness">Retirement Readiness</div>
                ${_renderKpiBadge(readinessDelta)}
              </div>
              <div class="fs-5 fw-bold mt-2" style="color:var(--text-primary);">${readinessPct}%</div>
              <div class="extra-small text-muted mt-1">Baseline: ${baseReadiness}%</div>
            </div>
          </div>
        </div>

        <!-- MULTI-SERIES CHART CARD (Requirement 3) -->
        <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
          <h5 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="scenario_planner_chart_title">Net Worth Trajectory Comparison</h5>
          <div style="height:320px; position:relative;">
            <canvas id="scenarioPlannerChart"></canvas>
          </div>
        </div>
      </div>
    `;
  }

