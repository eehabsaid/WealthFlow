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

  const healthScore = Number(health.score || 0);
  const healthRing = `conic-gradient(#34c759 ${Math.max(0, Math.min(100, healthScore))}%, rgba(123,147,201,0.20) 0)`;

  const riskScore = Number(score.score || 0);
  const riskColor = riskScore > 66 ? "#ff3b30" : riskScore > 33 ? "#ff9500" : "#34c759";
  const riskRing = `conic-gradient(${riskColor} ${Math.max(0, Math.min(100, riskScore))}%, rgba(123,147,201,0.20) 0)`;

  const breakdownHtml = breakdown
    .map((item) => {
      const levelColorClass =
        item.level === "high"
          ? "portfolio-badge-high"
          : item.level === "moderate"
            ? "portfolio-badge-medium"
            : "portfolio-badge-low";
      const barColor =
        item.level === "high" ? "#ff3b30" : item.level === "moderate" ? "#ff9500" : "#34c759";
      const paramsStr = JSON.stringify(item.reason_params || {})
        .replace(/'/g, "&apos;")
        .replace(/"/g, "&quot;");
      return `
      <div class="mb-3">
        <div class="d-flex align-items-center mb-1">
          <div style="flex:1; color: var(--text-primary);">
            <i class="bi bi-circle-fill me-3" style="color:${barColor};font-size:1.2rem; min-width: 24px; text-align: center;"></i>
            <strong data-i18n="${item.label_key}"></strong>
          </div>
          
          <div style="flex:1; padding:0 10px;">
            <!-- FIX: Added border and background fallback so empty track stays perfectly visible -->
            <div class="progress" style="height: 10px; background: rgba(148, 163, 184, 0.15); border: 1px solid rgba(148, 163, 184, 0.1);">
              <div class="progress-bar" role="progressbar" style="width: ${item.score}%; background:${barColor};" aria-valuenow="${item.score}" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
          </div>
          
          <div style="width:70px; text-align:right; font-weight:bold; color: var(--text-primary); font-size: 0.95em;">
            <span style="font-size: 0.9em; font-weight: bold;">${Math.round(item.score)}</span>
            <span style="font-size: 0.9em; font-weight: bold;">/100</span>
          </div>
          
          <div style="width:100px; text-align:right;">
            <span class="portfolio-severity-badge ${levelColorClass}" data-i18n="${item.level_key}"></span>
          </div>
        </div>
        
        <div style="padding-inline-start: 20px; font-size: 0.85em; color: var(--text-primary);" 
            data-i18n-key="${item.reason_key}" 
            data-i18n-params="${paramsStr}">
        </div>
      </div>
    `;
    })
    .join("");

  const findingsHtml = findings
    .map((item) => {
      const paramsStr = JSON.stringify(item.title_params || {})
        .replace(/'/g, "&apos;")
        .replace(/"/g, "&quot;");
      return `
    <div class="d-flex mb-3 align-items-start">
      <div class="me-3 mt-1">
        <i class="bi ${item.severity === "high" ? "bi-exclamation-triangle-fill" : item.severity === "medium" ? "bi-exclamation-circle-fill" : item.severity === "low" ? "bi-check-circle-fill" : "bi-info-circle-fill"}" style="font-size:1.5rem;color:${item.severity === "high" ? "#ff3b30" : item.severity === "medium" ? "#ff9500" : item.severity === "low" ? "#34c759" : "#007aff"};"></i>
      </div>
      <div>
        <div style="font-weight:bold; color:var(--text-primary); font-size: 1.15em;" data-i18n-key="${item.title_key}" data-i18n-params="${paramsStr}"></div>
        <div style="color:var(--text-secondary); font-size:0.9em;" data-i18n="${item.desc_key}"></div>
      </div>
    </div>
    `;
    })
    .join("");

  const stressHtml = stressTests
    .map(
      (item) => `
    <div class="d-flex align-items-center mb-3 p-3 rounded" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="me-3" style="min-width: 90px; text-align: end;" dir="ltr">
        <span class="fs-5" style="font-weight:bold; color:${item.impact_pct >= 0 ? "#34c759" : "#ff6b6b"};">${item.impact_pct >= 0 ? "+" : ""}${item.impact_pct}%</span>
        <div style="font-size:0.75em; color:${item.impact_amount >= 0 ? "#34c759" : "#ff6b6b"};">${item.impact_amount >= 0 ? "+" : ""}${fmt(item.impact_amount)}</div>
      </div>
      <div style="flex:3; padding:0 15px; border-inline-start: 1px solid var(--border-color);">
        <div style="font-weight:bold; color:var(--text-primary); font-size: 1.15em; margin-bottom: 4px;" data-i18n="${item.title_key}"></div>
        <div style="color:var(--text-primary); font-size: 0.85em;" data-i18n="${item.desc_key}"></div>
      </div>
      <div class="ms-3">
        <div style="width:40px;height:40px;border-radius:50%;background:var(--bg-primary);display:flex;align-items:center;justify-content:center; border: 1px solid var(--border-color);">
          <i class="bi ${item.icon}" style="color:var(--text-primary); font-size:1.2rem;"></i>
        </div>
      </div>
    </div>
  `
    )
    .join("");

  const sensitivitiesHtml = sensitivities
    .map(
      (item) => `
    <div class="col-12 col-md-6 col-xl-3 mb-3">
      <div class="p-3 rounded h-100 d-flex flex-column" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
        <div class="d-flex align-items-center mb-2">
          <i class="bi ${item.icon} me-2 fs-5" style="color:var(--text-primary);"></i>
          <span style="font-weight:bold; color:var(--text-primary);" data-i18n="${item.action_key}"></span>
        </div>
        <div class="mb-3" style="font-size:0.85em; color:var(--text-primary); flex-grow:1;" data-i18n="${item.title_key}"></div>
        <div class="p-2 rounded" style="background:var(--bg-primary);">
          <div class="mb-1" style="color:var(--text-primary); font-size:0.85em;" data-i18n="risk_analysis_score_label"></div>
          <div class="d-flex align-items-end mb-1" dir="ltr">
            <span class="fs-3 fw-bold me-2" style="color:${item.oldColor || "var(--text-primary)"};">${Math.round(item.current_score)}</span>
            <i class="bi bi-arrow-right me-2 mb-1" style="color:var(--text-primary);"></i>
            <span class="fs-3 fw-bold" style="color:${item.change > 0 ? "#ff6b6b" : "#34c759"};">${Math.round(item.projected_score)}</span>
          </div>
          <div class="d-flex justify-content-between" style="font-size:0.85em;" dir="ltr">
            <span style="color:var(--text-primary);" data-i18n="risk_analysis_change_label"></span>
            <span style="font-weight:bold; color:${item.change > 0 ? "#ff6b6b" : "#34c759"};">${item.change > 0 ? "+" : ""}${item.change} pts</span>
          </div>
        </div>
      </div>
    </div>
  `
    )
    .join("");

  const actionsHtml = priorityActions
    .map(
      (item) => `
    <div class="d-flex mb-3 p-3 rounded align-items-start" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="me-3 mt-1">
        <div style="width:32px;height:32px;border-radius:50%;background:${item.priority_num === 1 ? "#ff3b30" : item.priority_num === 2 ? "#ff9500" : "#007aff"};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:0.9rem;">${item.priority_num}</div>
      </div>
      <div style="flex:1;">
        <h6 style="color:var(--text-primary); font-weight:bold; margin-bottom: 5px;" data-i18n="${item.title_key}"></h6>
        <p style="color:var(--text-secondary); font-size: 0.9em; margin-bottom: 12px;" data-i18n="${item.desc_key}"></p>
        <div class="d-flex flex-wrap gap-2 align-items-center">
          <span class="portfolio-severity-badge ${item.impact === "High" ? "portfolio-badge-low" : item.impact === "Medium" ? "portfolio-badge-medium" : "portfolio-badge-high"}">
            <i class="bi bi-lightning-charge me-1"></i> <span data-i18n="risk_analysis_actions_col_impact"></span>: <span data-i18n="${item.impact_key}"></span>
          </span>
          <span class="portfolio-severity-badge ${item.difficulty === "Easy" ? "portfolio-badge-low" : item.difficulty === "Medium" ? "portfolio-badge-medium" : "portfolio-badge-high"}">
            <i class="bi bi-tools me-1"></i> <span data-i18n="risk_analysis_actions_col_diff"></span>: <span data-i18n="${item.difficulty_key}"></span>
          </span>
          <div class="ms-auto" style="font-weight:bold; color:#34c759; font-size:0.9em;">
            <i class="bi bi-graph-down-arrow me-1"></i> -${item.improvement} pts
          </div>
        </div>
      </div>
    </div>
  `
    )
    .join("");

  const incomeSources = incomeStability.sources || [];
  const incomeHtml = incomeSources
    .map(
      (s) => `
    <div class="d-flex justify-content-between mb-2">
      <div style="color:var(--text-primary);"><i class="bi bi-circle-fill me-2" style="font-size:0.5em;color:${s.id === "salary" ? "#34c759" : "#007aff"};"></i><span data-i18n="${s.label_key}"></span></div>
      <div style="font-weight:bold; color:var(--text-primary);">${s.percentage}%</div>
    </div>
  `
    )
    .join("");

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
