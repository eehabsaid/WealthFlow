"use strict";
// renderRiskAnalysis orchestrator: computes all derived values from the
// payload, then delegates to buildRiskAnalysisPaneHtml (render_template.js)
// for the actual markup.

window.RA = window.RA || {};

window.RA.renderRiskAnalysis = function (payload) {
  const pane = document.getElementById("fa-pane-risk-analysis");
  if (!pane) return;

  const health = payload.portfolio_health || {};
  const score = payload.risk_score || {};
  const breakdown = payload.breakdown || [];
  const findings = payload.findings || [];
  const stressTests = payload.stress_tests || [];
  const sensitivities = payload.sensitivities || [];
  const priorityActions = payload.priority_actions || [];
  const incomeStability = payload.income_stability || {};

  const {
    healthScore,
    healthRing,
    riskScore,
    riskRing,
    riskColor,
    breakdownHtml,
    findingsHtml,
    stressHtml,
    sensitivitiesHtml,
    actionsHtml,
    incomeHtml,
  } = window.RA.buildRiskAnalysisFragments({
    health,
    score,
    breakdown,
    findings,
    stressTests,
    sensitivities,
    priorityActions,
    incomeStability,
  });

  pane.innerHTML = window.RA.buildRiskAnalysisPaneHtml({
    payload,
    health,
    score,
    breakdown,
    findings,
    stressTests,
    sensitivities,
    priorityActions,
    incomeStability,
    healthScore,
    healthRing,
    riskScore,
    riskRing,
    riskColor,
    breakdownHtml,
    findingsHtml,
    stressHtml,
    sensitivitiesHtml,
    actionsHtml,
    incomeHtml,
  });

  if (typeof applyTranslations === "function") {
    // Inject dynamic translation parameters
    pane.querySelectorAll("[data-param]").forEach((el) => {
      const parent = el.closest("[data-i18n]");
      if (parent) {
        parent.setAttribute(`data-i18n-param-${el.getAttribute("data-param")}`, el.textContent);
      }
    });
    applyTranslations();
  }

  window.RA.drawRiskRadarChart(payload);
  window.RA.drawIncomeStabilityChart(payload);
};
