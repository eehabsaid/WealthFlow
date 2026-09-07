"use strict";
// Risk analysis tab rendering and load handlers
// This file is part of the financial_advisor module. Do not edit directly.
// Split from the former monolithic risk_analysis.js (200-line rule).

window.RA = window.RA || {};
window.RA.state = {
  riskAnalysisLoaded: false,
  riskAnalysisData: null,
};

// Split from the former monolithic risk_analysis.js (200-line rule).
// Sibling files:
// - render_loading_error.js  Loading/error placeholder renderers
// - render_main.js           renderRiskAnalysis orchestrator (computes ctx, delegates HTML)
// - render_template.js       Main pane HTML template builder
// - radar_chart.js           Risk radar chart drawing
// - income_chart.js          Income stability chart drawing
// - loader.js                loadRiskAnalysis data fetch + dispatch

