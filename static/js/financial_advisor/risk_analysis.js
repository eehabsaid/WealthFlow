"use strict";
// Risk analysis tab rendering and load handlers
// This file is part of the financial_advisor module. Do not edit directly.

let _riskAnalysisLoaded = false;
let _riskAnalysisData = null;

function _renderRiskAnalysisLoading() {
  const pane = document.getElementById("fa-pane-risk-analysis");
  if (!pane) return;
  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="risk_analysis_loading"></div>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

function _renderRiskAnalysisError() {
  const pane = document.getElementById("fa-pane-risk-analysis");
  if (!pane) return;
  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="risk_analysis_error"></span>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

function _renderRiskAnalysis(payload) {
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

  pane.innerHTML = `
    <div class="portfolio-optimizer-wrap">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div style="color:var(--text-secondary);" data-i18n="risk_analysis_subtitle"></div>
        <div class="portfolio-optimizer-date">
          <span data-i18n="portfolio_optimizer_as_of"></span>
          <strong>${payload?.as_of || "-"}</strong>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-md-6">
          <div class="portfolio-card portfolio-health-card h-100">
            <div class="portfolio-card-title d-flex justify-content-center align-items-center">
              <i class="bi bi-shield-check me-2" style="color:var(--text-secondary);"></i>
              <span data-i18n="portfolio_optimizer_health_score"></span>
            </div>
            <div class="portfolio-score-ring" style="background:${healthRing};">
              <div class="portfolio-score-center">${Math.round(healthScore)}</div>
            </div>
            <div class="portfolio-score-label" style="color:#34c759;" data-i18n="${health.label_key || "portfolio_optimizer_health_attention"}"></div>
            <div class="portfolio-score-footnote mt-2" data-i18n="risk_analysis_health_note"></div>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="portfolio-card portfolio-health-card h-100">
            <div class="portfolio-card-title d-flex justify-content-center align-items-center">
              <i class="bi bi-shield-exclamation me-2" style="color:var(--text-secondary);"></i>
              <span data-i18n="risk_analysis_risk_score"></span>
            </div>
            <div class="portfolio-score-ring" style="background:${riskRing};">
              <div class="portfolio-score-center">${Math.round(riskScore)}</div>
            </div>
            <div class="portfolio-score-label" style="color:${riskColor};" data-i18n="${score.level_key || "risk_analysis_level_moderate"}"></div>
            <div class="portfolio-score-footnote mt-2" data-i18n="risk_analysis_score_note"></div>
          </div>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-6">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="risk_analysis_breakdown_title"></div>
            <div class="p-2">${breakdownHtml}</div>
          </div>
        </div>
        <div class="col-12 col-xl-6">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="risk_analysis_radar_title"></div>
            <div class="portfolio-chart-wrap d-flex justify-content-center align-items-center h-100" style="min-height:300px;">
              <canvas id="riskRadarChart" style="max-height:300px;"></canvas>
            </div>
          </div>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-5">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="risk_analysis_findings_title"></div>
            <div class="p-2">${findingsHtml}</div>
          </div>
        </div>
        <div class="col-12 col-xl-7">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title d-flex justify-content-between">
              <span data-i18n="risk_analysis_stress_title"></span>
              <span style="font-size:0.8em;font-weight:normal;color:var(--text-secondary);" data-i18n="risk_analysis_stress_col_impact"></span>
            </div>
            <div class="p-2">${stressHtml}</div>
          </div>
        </div>
      </div>

      <div class="portfolio-card mb-3">
        <div class="portfolio-card-title" data-i18n="risk_analysis_whatif_title"></div>
        <div class="row g-3 p-2">${sensitivitiesHtml}</div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-8">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title d-flex justify-content-between align-items-center">
              <div data-i18n="risk_analysis_actions_title"></div>
            </div>
            <div class="p-2">${actionsHtml}</div>
          </div>
        </div>
        <div class="col-12 col-xl-4">
          <div class="portfolio-card h-100">
            <div class="portfolio-card-title" data-i18n="risk_analysis_income_title"></div>
            <div class="d-flex justify-content-center align-items-center mb-4 mt-3">
              <div style="position:relative; width:180px; height:180px;">
                <canvas id="incomeStabilityChart"></canvas>
                <div style="position:absolute;top:0;left:0;right:0;bottom:0;display:flex;align-items:center;justify-content:center;">
                  <i class="bi bi-briefcase text-secondary fs-1"></i>
                </div>
              </div>
            </div>
            <div class="p-2 mb-3 mt-4">${incomeHtml}</div>
            <div class="d-flex justify-content-between align-items-center pt-3 border-top" style="border-color:var(--border-color) !important;">
              <span style="color:var(--text-secondary);" data-i18n="risk_analysis_income_score_label"></span>
              <div class="d-flex align-items-center">
                <span class="fs-4 fw-bold me-3" style="color:#34c759;">${Math.round(incomeStability.score)} <span style="font-size:0.5em;color:var(--text-secondary);">/100</span></span>
                <span class="portfolio-severity-badge ${incomeStability.score >= 60 ? "portfolio-badge-low" : incomeStability.score >= 40 ? "portfolio-badge-medium" : "portfolio-badge-high"}" data-i18n="${incomeStability.level_key}"></span>
              </div>
            </div>
            <div class="text-center mt-2" style="font-size:0.85em;color:var(--text-secondary);" data-i18n="risk_analysis_income_footer"></div>
          </div>
        </div>
      </div>

      <!-- Overall Recommendation Card -->
      <div class="portfolio-card mb-3" style="border-left: 4px solid var(--accent-primary);">
        <div class="p-3">
          <h4 style="color:var(--text-primary); margin-bottom: 15px;" data-i18n="risk_analysis_overall_rec_title"></h4>
          <p style="color:var(--text-secondary); font-size: 1.05em; line-height: 1.6; margin-bottom: 20px;" data-i18n="${payload?.overall_recommendation?.score_desc_key}"></p>
          
          <div class="p-3 rounded" style="background:var(--bg-secondary);">
            <div style="font-size: 0.85em; color: var(--accent-primary); font-weight: bold; text-transform: uppercase; margin-bottom: 8px;" data-i18n="risk_analysis_overall_top_action"></div>
            <div class="d-flex align-items-center mb-2">
              <i class="bi bi-star-fill me-2" style="color: #ff9500;"></i>
              <strong style="color:var(--text-primary); font-size: 1.1em;" data-i18n="${payload?.overall_recommendation?.top_action_title_key}"></strong>
            </div>
            <div style="color:var(--text-secondary); padding-left: 28px;" data-i18n="${payload?.overall_recommendation?.top_action_desc_key}"></div>
          </div>
        </div>
      </div>
    </div>
  `;

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

  _drawRiskRadarChart(payload);
  _drawIncomeStabilityChart(payload);
}

function _drawRiskRadarChart(payload) {
  if (typeof _destroyChart === "function") _destroyChart("riskRadarChart");
  const radarData = payload?.radar || {};
  if (!radarData.labels || !radarData.values) return;

  const canvas = document.getElementById("riskRadarChart");
  if (!canvas || !window.Chart) return;
  const labels = radarData.labels.map((k) => (typeof t === "function" ? t(k, k) : k));

  document.addEventListener("languageChanged", () => {
    if (window._riskRadarChart) {
      window._riskRadarChart.data.labels = radarData.labels.map((k) =>
        typeof t === "function" ? t(k, k) : k
      );
      window._riskRadarChart.update();
    }
  });
  const textPrimary =
    typeof _themeColor === "function" ? _themeColor("--text-primary", "#333") : "#333";
  const gridColor =
    typeof _themeColor === "function" ? _themeColor("--border-color", "#e2e8f0") : "#e2e8f0";
  const isRtl = typeof _pageDirection === "function" ? _pageDirection() === "rtl" : false;

  // Ensure chart updates on language change
  const updateChartLabels = () => {
    if (!window._riskRadarChart) return;
    const translatedLabels = radarData.labels.map((k) => (typeof t === "function" ? t(k, k) : k));
    window._riskRadarChart.data.labels = translatedLabels;
    window._riskRadarChart.data.datasets[0].label =
      typeof t === "function" ? t("risk_analysis_risk_score", "Risk Score") : "Risk Score";
    window._riskRadarChart.update();
  };

  if (window._riskRadarChart) {
    window._riskRadarChart.destroy();
  }

  window._riskRadarChart = new Chart(canvas, {
    type: "radar",
    data: {
      labels: labels,
      datasets: [
        {
          label:
            typeof t === "function" ? t("risk_analysis_risk_score", "Risk Score") : "Risk Score",
          data: radarData.values,
          backgroundColor: "rgba(255, 149, 0, 0.2)",
          borderColor: "rgba(255, 149, 0, 1)",
          pointBackgroundColor: "rgba(255, 149, 0, 1)",
          pointBorderColor: "#fff",
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: "rgba(255, 149, 0, 1)",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      rtl: isRtl,
      scales: {
        r: {
          angleLines: { color: gridColor },
          grid: { color: gridColor },
          pointLabels: {
            color: "#888",
            font: { size: 11, family: "system-ui, -apple-system, sans-serif" },
          },
          ticks: {
            backdropColor: "transparent",
            color:
              typeof _themeColor === "function" ? _themeColor("--text-secondary", "#666") : "#666",
            stepSize: 20,
            min: 0,
            max: 100,
            display: true,
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor:
            typeof _themeColor === "function" ? _themeColor("--bg-secondary", "#fff") : "#fff",
          titleColor: textPrimary,
          bodyColor: textPrimary,
          borderColor: gridColor,
          borderWidth: 1,
          displayColors: false,
          callbacks: {
            label: function (context) {
              return context.formattedValue + " / 100";
            },
          },
        },
      },
    },
  });
}

function _drawIncomeStabilityChart(payload) {
  if (typeof _destroyChart === "function") _destroyChart("incomeStabilityChart");
  const sources = payload?.income_stability?.sources || [];
  if (sources.length === 0) return;

  const canvas = document.getElementById("incomeStabilityChart");
  if (!canvas || !window.Chart) return;

  const labels = sources.map((s) => (typeof t === "function" ? t(s.label_key, s.id) : s.id));
  const data = sources.map((s) => s.percentage);
  const bgColors = sources.map((s) =>
    s.id === "salary" ? "rgba(52, 199, 89, 0.8)" : "rgba(0, 122, 255, 0.8)"
  );
  const borderColors = sources.map((s) =>
    s.id === "salary" ? "rgb(52, 199, 89)" : "rgb(0, 122, 255)"
  );
  const isRtl = typeof _pageDirection === "function" ? _pageDirection() === "rtl" : false;

  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: bgColors,
          borderColor: borderColors,
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      rtl: isRtl,
      cutout: "75%",
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor:
            typeof _themeColor === "function" ? _themeColor("--bg-secondary", "#fff") : "#fff",
          titleColor:
            typeof _themeColor === "function" ? _themeColor("--text-primary", "#333") : "#333",
          bodyColor:
            typeof _themeColor === "function" ? _themeColor("--text-primary", "#333") : "#333",
          borderColor:
            typeof _themeColor === "function"
              ? _themeColor("--border-color", "#e2e8f0")
              : "#e2e8f0",
          borderWidth: 1,
          callbacks: {
            label: function (context) {
              return context.formattedValue + "%";
            },
          },
        },
      },
    },
  });
}

async function loadRiskAnalysis(force = false) {
  if (_riskAnalysisData && !force) {
    _renderRiskAnalysis(_riskAnalysisData);
    _riskAnalysisLoaded = true;
    return;
  }

  _renderRiskAnalysisLoading();
  try {
    const response = await fetch("/api/financial-advisor/risk-analysis/");
    if (!response.ok) {
      throw new Error("risk_analysis_fetch_failed");
    }
    const payload = await response.json();
    _riskAnalysisData = payload;
    _renderRiskAnalysis(payload);
    _riskAnalysisLoaded = true;
  } catch (error) {
    _renderRiskAnalysisError();
  }
}

window.loadRiskAnalysis = loadRiskAnalysis;
