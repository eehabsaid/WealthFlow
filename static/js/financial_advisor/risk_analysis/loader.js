"use strict";
// loadRiskAnalysis: data fetch + dispatch to renderers.

window.RA = window.RA || {};

window.RA.loadRiskAnalysis = async function(force = false) {
  if (window.RA.state.riskAnalysisData && !force) {
    window.RA.renderRiskAnalysis(window.RA.state.riskAnalysisData);
    window.RA.state.riskAnalysisLoaded = true;
    return;
  }

  window.RA.renderRiskAnalysisLoading();
  try {
    const response = await fetch("/api/financial-advisor/risk-analysis/");
    if (!response.ok) {
      throw new Error("risk_analysis_fetch_failed");
    }
    const payload = await response.json();
    window.RA.state.riskAnalysisData = payload;
    window.RA.renderRiskAnalysis(payload);
    window.RA.state.riskAnalysisLoaded = true;
  } catch (error) {
    window.RA.renderRiskAnalysisError();
  }
}

window.loadRiskAnalysis = window.RA.loadRiskAnalysis;
