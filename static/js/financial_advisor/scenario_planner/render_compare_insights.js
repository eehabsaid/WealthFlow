"use strict";
window.SP = window.SP || {};


  // ── Requirement 3: Scrollable N-Scenario Comparison Table ─────────────────

  window.SP.buildComparePaneHtml = function() {
    const base = window.SP.state.scenarioPlannerData?.baseline || {};
    const scenarios = window.SP.state.scenarioPlannerData?.scenarios || [];

    return `
      <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
        <h5 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="scenario_planner_compare_title">Side-by-Side N-Scenario Comparison</h5>

        <!-- Requirement 3: Scrollable N-scenario table -->
        <div style="overflow-x:auto;">
          <table class="table table-dark table-borderless align-middle m-0" style="background:transparent;">
            <thead>
              <tr class="border-bottom border-secondary">
                <th style="color:var(--text-muted); font-size:12px;" data-i18n="scenario_planner_metric_header">Metric</th>
                <th style="color:var(--text-muted); font-size:12px;">Baseline</th>
                ${scenarios.map((sc) => `<th style="color:var(--accent-primary); font-size:12px;">${sc.name}</th>`).join("")}
              </tr>
            </thead>
            <tbody>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_nw">Net Worth (12m)</td>
                <td class="fw-bold text-light">${window.SP.money(base.net_worth_12m)}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${window.SP.money(sc.net_worth_12m)}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_cashflow">Monthly Cash Flow</td>
                <td class="fw-bold text-light">${window.SP.money(base.monthly_cash_flow)}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${window.SP.money(sc.monthly_cash_flow)}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_debt">Total Debt</td>
                <td class="fw-bold text-light">${window.SP.money(base.total_debt)}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${window.SP.money(sc.total_debt)}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_coverage">Cash Coverage (months)</td>
                <td class="fw-bold text-light">${base.cash_coverage_months ?? "-"}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${sc.cash_coverage_months ?? "-"}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_risk">Risk Score</td>
                <td class="fw-bold text-light">${base.risk_score}</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${sc.risk_score}</td>`).join("")}
              </tr>
              <tr class="border-bottom border-secondary border-opacity-10">
                <td class="fw-semibold text-secondary" data-i18n="scenario_planner_metric_readiness">Retirement Readiness</td>
                <td class="fw-bold text-light">${base.retirement_readiness?.readiness_pct ?? 0}%</td>
                ${scenarios.map((sc) => `<td class="fw-bold text-light">${sc.retirement_readiness?.readiness_pct ?? 0}%</td>`).join("")}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // ── Requirement 5: Actionable Insights with Financial Impact & Alternatives

  window.SP.buildInsightsPaneHtml = function() {
    const scenarios = window.SP.state.scenarioPlannerData?.scenarios || [];
    if (scenarios.length === 0) {
      return `
        <div class="alert alert-info" data-i18n="scenario_planner_insights_no_scenarios">
          Select or compare at least one scenario to generate financial insights.
        </div>
      `;
    }

    return `
      <div class="d-flex flex-column gap-3">
        ${scenarios
          .map((sc) => {
            const insights = sc.insights || [];
            return `
            <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <h6 class="fw-bold mb-3" style="color:var(--text-primary);">${sc.name} — Actionable Financial Insights</h6>
              <div class="d-flex flex-column gap-3">
                ${insights
                  .map(
                    (ins) => `
                  <div class="p-3 rounded d-flex align-items-start gap-3" style="background:var(--bg-tertiary); border:1px solid var(--border-color); border-radius:10px;">
                    <i class="bi ${ins.severity === "good" ? "bi-check-circle-fill text-success" : ins.severity === "bad" ? "bi-exclamation-octagon-fill text-danger" : "bi-exclamation-triangle-fill text-warning"} fs-4 mt-1"></i>
                    <div class="w-100">
                      <div class="fw-bold small text-light mb-1" data-i18n="${ins.title_key}">${ins.title_key}</div>
                      <div class="extra-small text-muted mb-2" data-i18n="${ins.body_key}">${ins.body_key}</div>

                      <!-- Structured Impact, Action, and Alternative -->
                      <div class="p-2 rounded bg-dark bg-opacity-50 border border-secondary border-opacity-25 d-flex flex-column gap-1">
                        ${ins.impact_text ? `<div class="extra-small text-info"><strong><i class="bi bi-pie-chart-fill me-1"></i>Financial Impact:</strong> ${ins.impact_text}</div>` : ""}
                        ${ins.action_text ? `<div class="extra-small text-primary"><strong><i class="bi bi-lightning-charge-fill me-1"></i>Recommended Action:</strong> ${ins.action_text}</div>` : ""}
                        ${ins.alternative_text ? `<div class="extra-small text-warning"><strong><i class="bi bi-arrow-repeat me-1"></i>Alternative Option:</strong> ${ins.alternative_text}</div>` : ""}
                      </div>
                    </div>
                  </div>
                `
                  )
                  .join("")}
              </div>
            </div>
          `;
          })
          .join("")}
      </div>
    `;
  }

