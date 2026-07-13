"use strict";

let _overviewLoaded = false;
let _overviewData = null;

function _renderOverviewLoading() {
  const container = document.getElementById("fa-overview-content");
  if (!container) return;

  container.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary); text-align:center;">
        <div class="spinner-border spinner-border-sm me-2" role="status" style="color:var(--accent-primary);"></div>
        <span data-i18n="cash_flow_loading">Loading...</span>
      </div>
    </div>
  `;
  applyTranslations();
}

function _renderOverviewError() {
  const container = document.getElementById("fa-overview-content");
  if (!container) return;

  container.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="cash_flow_error">Unable to load overview dashboard.</span>
    </div>
  `;
  applyTranslations();
}

function _categoryColor(key) {
  const colors = {
    "cash": "var(--accent-green)",
    "banks": "var(--accent-primary)",
    "certificates": "#8c7cf0",
    "gold": "var(--accent-yellow)",
    "real_estate": "#3ddc84",
    "vehicles": "#5da9ff",
    "other_assets": "#b178ff"
  };
  return colors[key] || "var(--accent-primary)";
}

function _formatOverviewAiSummary(execSummary) {
  if (!execSummary || !execSummary.recommendation_paragraphs) return "";

  // Render list of paragraphs with spacing
  return execSummary.recommendation_paragraphs.map(p => {
    let text = t(p.key, p.fallback);
    if (p.params) {
      for (const [k, v] of Object.entries(p.params)) {
        if (k === "asset_class_key") {
          text = text.replace("{asset_class}", t(v, v));
        } else if (k === "amount") {
          text = text.replace(`{${k}}`, _money(v));
        } else {
          text = text.replace(`{${k}}`, fmt(v));
        }
      }
    }
    return `<p class="mb-2" style="margin-bottom:8px !important; line-height: 1.6; color: var(--text-secondary);">${_escapeHtml(text)}</p>`;
  }).join("");
}

function _formatGoalDate(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const day = d.getDate();
    const monthKey = `month_short_${d.getMonth() + 1}`;
    const year = d.getFullYear();
    return `${day} ${t(monthKey, monthKey)} ${year}`;
  } catch(e) {
    return dateStr;
  }
}

function _alertBadge(severity) {
  const badgeClasses = {
    "danger": "bg-danger text-white",
    "warning": "bg-warning text-dark",
    "info": "bg-info text-dark",
    "success": "bg-success text-white"
  };
  const labelKey = `portfolio_optimizer_severity_${severity}`;
  const fallback = severity.toUpperCase();
  return `<span class="badge ${badgeClasses[severity] || 'bg-secondary'} ms-2" style="font-size:8px; padding: 4px 6px; letter-spacing: 0.5px; vertical-align: middle; flex-shrink: 0;">${t(labelKey, fallback)}</span>`;
}

function _renderOverview(payload) {
  const container = document.getElementById("fa-overview-content");
  if (!container) return;

  const kpis = payload.kpis || {};
  const totalNetWorth = Number(kpis.total_net_worth || 0);

  // 1. Graceful Empty State check
  if (totalNetWorth <= 10.0) {
    container.innerHTML = `
      <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
        <div class="card-body" style="padding:48px; text-align:center;">
          <div style="font-size:42px; color:var(--text-secondary); opacity:0.3; margin-bottom:16px;">
            <i class="bi bi-wallet2"></i>
          </div>
          <h4 style="color:var(--text-primary); margin-bottom:12px;" data-i18n="overview_empty_state_title">No financial data available yet.</h4>
          <p style="color:var(--text-secondary); max-width:520px; margin:0 auto 24px auto; line-height:1.6;" data-i18n="overview_empty_state_desc">Start by adding bank accounts, fixed assets, or monthly expenses to receive structured AI financial insights and overview metrics.</p>
          <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
            <a href="#balance" class="btn btn-sm btn-outline-primary px-3 py-2" style="border-radius:6px; font-weight:600;"><i class="bi bi-bank me-1"></i> <span data-i18n="balance_tab_accounts">Accounts</span></a>
            <a href="#fixed-assets" class="btn btn-sm btn-outline-primary px-3 py-2" style="border-radius:6px; font-weight:600;"><i class="bi bi-house me-1"></i> <span data-i18n="nav_fixed_assets">Assets</span></a>
            <a href="#expenses" class="btn btn-sm btn-outline-primary px-3 py-2" style="border-radius:6px; font-weight:600;"><i class="bi bi-cart me-1"></i> <span data-i18n="nav_expenses_reports">Expenses</span></a>
          </div>
        </div>
      </div>
    `;
    applyTranslations();
    return;
  }

  const healthScore = Number(payload.health_score || 0);

  // Health Score Color Indicator (Standardized Theme Colors)
  let healthColor = "var(--accent-green)";
  if (healthScore < 60) healthColor = "var(--accent-red)";
  else if (healthScore < 75) healthColor = "var(--accent-yellow)";
  else if (healthScore < 90) healthColor = "#2d7fff"; // Good (standard blue)

  const healthRing = `conic-gradient(${healthColor} ${healthScore}%, rgba(123,147,201,0.12) 0)`;

  // Legend highlight calculation
  const rangeExcellentActive = healthScore >= 90;
  const rangeGoodActive = (healthScore >= 75 && healthScore < 90);
  const rangeAverageActive = (healthScore >= 60 && healthScore < 75);
  const rangeNeedsActive = healthScore < 60;

  // Recommendation Paragraphs (Limited to 3 items)
  const recParagraphsHtml = _formatOverviewAiSummary(payload.executive_summary);

  // Alerts list with severity badge and empty state fallback
  const alertsHtml = (payload.alerts || []).length > 0
    ? (payload.alerts || []).map(alert => {
        let desc = t(alert.desc_key, alert.desc_fallback);
        if (alert.params) {
          for (const [k, v] of Object.entries(alert.params)) {
            if (k === "amount") desc = desc.replace(`{${k}}`, _money(v));
            else desc = desc.replace(`{${k}}`, fmt(v));
          }
        }
        return `
          <div class="overview-alert-item animate__animated animate__fadeIn" style="cursor:pointer;" onclick="switchFinancialAdvisorTab('${alert.target_tab}')">
            <div class="overview-alert-icon-wrap ${alert.class}">
              <i class="bi ${alert.icon}"></i>
            </div>
            <div class="overview-alert-details">
              <div class="d-flex align-items-center justify-content-between mb-1">
                <div class="overview-alert-title" style="color: var(--text-primary);">${t(alert.title_key, alert.title_fallback)}</div>
                <div style="margin-left: 16px; flex-shrink: 0;">${_alertBadge(alert.severity)}</div>
              </div>
              <div class="overview-alert-desc" style="color: var(--text-secondary);">${desc}</div>
            </div>
          </div>
        `;
      }).join("")
    : `<div style="text-align:center; padding:32px 16px; color:var(--text-secondary); font-size:13px;" data-i18n="overview_no_alerts">No alerts</div>`;

  // Net Worth trend calculations
  const nwTrendIsUp = Number(kpis.net_worth_growth_yoy || 0) >= 0;
  const nwTrendClass = nwTrendIsUp ? "up" : "down";
  const nwTrendText = nwTrendIsUp
    ? t("overview_kpi_yoy_trend_up", `↑ {pct}% vs last year`).replace("{pct}", fmt(Math.abs(kpis.net_worth_growth_yoy)))
    : t("overview_kpi_yoy_trend_down", `↓ {pct}% vs last year`).replace("{pct}", fmt(Math.abs(kpis.net_worth_growth_yoy)));

  // Cash Flow expected change
  const cfChangeVal = Number(payload.cash_flow.expected_change_30d || 0);
  const cfChangeSign = cfChangeVal >= 0 ? "+" : "";
  const cfChangeClass = cfChangeVal >= 0 ? "up" : "down";

  // Wealth Growth expected growth
  const wgGrowthVal = Number(payload.wealth_growth.expected_growth_pct || 0);
  const wgGrowthSign = wgGrowthVal >= 0 ? "+" : "";

  // Dynamic Opportunities list with colored severity badge and empty state fallback
  const opportunitiesHtml = (payload.opportunities || []).length > 0
    ? (payload.opportunities || []).map(opp => {
        let oppIcon = "bi-lightbulb-fill";
        let oppClass = "alert-info-badge";
        if (opp.key.includes("cash") || opp.key.includes("liquidity")) {
          oppIcon = "bi-graph-up-arrow";
          oppClass = "alert-info-badge";
        } else if (opp.key.includes("gold")) {
          oppIcon = "bi-safe2-fill";
          oppClass = "alert-warning-badge";
        } else if (opp.key.includes("certificates")) {
          oppIcon = "bi-bank2";
          oppClass = "alert-success-badge";
        } else if (opp.key.includes("mortgage")) {
          oppIcon = "bi-house-door-fill";
          oppClass = "alert-success-badge";
        }

        let badgeClass = "bg-info text-dark";
        if (opp.priority === "high") badgeClass = "bg-danger";
        else if (opp.priority === "medium") badgeClass = "bg-warning text-dark";

        // Remove duplication on impact description wording
        let impactDesc = t(opp.impact_key, opp.impact_key);
        const prefixes = [
          "Potential impact: ", "Potential impact:",
          "الأثر المحتمل: ", "الأثر المحتمل:",
          "Möglicher Effekt: ", "Möglicher Effekt:",
          "Impact potentiel : ", "Impact potentiel :", "Impact potentiel:",
          "Potential impact "
        ];
        for (const prefix of prefixes) {
          if (impactDesc.startsWith(prefix)) {
            impactDesc = impactDesc.substring(prefix.length);
            break;
          }
        }
        if (impactDesc) {
          impactDesc = impactDesc.charAt(0).toUpperCase() + impactDesc.slice(1);
        }

        return `
          <div class="overview-opp-item animate__animated animate__fadeIn" onclick="switchFinancialAdvisorTab('${opp.target_tab}')">
            <div class="overview-opp-icon-wrap ${oppClass}">
              <i class="bi ${oppIcon}"></i>
            </div>
            <div class="overview-opp-details">
              <div class="d-flex align-items-center justify-content-between">
                <span class="overview-opp-title">${t(opp.key, opp.key)}</span>
                <span class="badge ${badgeClass} ms-2" style="font-size:9px; text-transform:uppercase;">${t("portfolio_optimizer_severity_" + opp.priority, opp.priority)}</span>
              </div>
              <div class="overview-opp-desc" style="color: var(--text-secondary);"><span data-i18n="overview_estimated_impact">Estimated Impact</span>: ${impactDesc}</div>
            </div>
            <i class="bi bi-chevron-right overview-opp-arrow ms-2" style="color: var(--text-secondary);"></i>
          </div>
        `;
      }).join("")
    : `<div style="text-align:center; padding:32px 16px; color:var(--text-secondary); font-size:13px;" data-i18n="overview_no_optimization_opportunities">No optimization opportunities</div>`;

  // Portfolio allocation list rows (vertical alignment right)
  const allocationRowsHtml = (payload.portfolio.allocation_cards || []).map(card => {
    return `
      <div class="d-flex align-items-center justify-content-between mb-1 pb-1 border-bottom" style="border-color:var(--border-color) !important; font-size:11px; line-height: 1.2;">
        <span style="color:var(--text-secondary); display:inline-flex; align-items:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex: 1;">
          <i class="bi bi-circle-fill me-2" style="font-size:6px; color:${_categoryColor(card.key)}; margin-right:6px;"></i>
          ${t(card.label_key, card.key)}
        </span>
        <span class="fw-bold" style="color:var(--text-primary); margin-left: 12px; margin-right: 16px; flex-shrink: 0;">
          ${_money(card.value)}
        </span>
        <span class="fw-bold text-end" style="color:var(--text-primary); width: 48px; flex-shrink: 0;">
          ${fmt(card.percentage)}%
        </span>
      </div>
    `;
  }).join("");

  const goalProgressPct = Math.round(payload.goals.progress_pct || 0);
  const goalRing = `conic-gradient(var(--accent-primary) ${goalProgressPct}%, rgba(123,147,201,0.12) 0)`;

  // Localized date formatting
  const monthName = t(payload.as_of.month_key, payload.as_of.month_key);

  // Build the complete layout
  container.innerHTML = `
    <!-- ROW 1: Financial Health, AI Executive Summary, Alerts (Bottom Margin mb-4 for Spacing Rhythm) -->
    <div class="row g-3 mb-4">
      <!-- Financial Health Card -->
      <div class="col-12 col-lg-3">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title mb-2">
              <span data-i18n="overview_kpi_portfolio_health">Portfolio Health</span>
              <i class="bi bi-info-circle ms-2" style="color: var(--text-secondary); cursor: pointer;" data-bs-toggle="tooltip" data-bs-placement="top" data-i18n="[title]overview_health_score_tooltip"></i>
            </div>
            <div class="overview-score-ring" style="background:${healthRing};">
              <div class="overview-score-center">
                <div class="overview-score-value" style="font-size: 46px;">${healthScore}</div>
                <div class="overview-score-total" style="color: var(--text-secondary);">/100</div>
              </div>
            </div>
            <!-- Score Range Legends with Dynamic Highlight Range -->
            <div style="font-size: 11px; margin-top: 14px; border-top: 1px solid var(--border-color); padding-top: 10px;">
              <div class="d-flex align-items-center mb-1" style="opacity: ${rangeExcellentActive ? '1' : '0.45'}; font-weight: ${rangeExcellentActive ? '700' : 'normal'};">
                <span class="d-inline-block rounded-circle me-2" style="width:8px; height:8px; background:var(--accent-green); flex-shrink:0;"></span>
                <span style="color:var(--text-primary);">${rangeExcellentActive ? '✔ ' : ''}<span data-i18n="overview_legend_excellent">Excellent (90-100)</span></span>
              </div>
              <div class="d-flex align-items-center mb-1" style="opacity: ${rangeGoodActive ? '1' : '0.45'}; font-weight: ${rangeGoodActive ? '700' : 'normal'};">
                <span class="d-inline-block rounded-circle me-2" style="width:8px; height:8px; background:#2d7fff; flex-shrink:0;"></span>
                <span style="color:var(--text-primary);">${rangeGoodActive ? '✔ ' : ''}<span data-i18n="overview_legend_good">Good (75-89)</span></span>
              </div>
              <div class="d-flex align-items-center mb-1" style="opacity: ${rangeAverageActive ? '1' : '0.45'}; font-weight: ${rangeAverageActive ? '700' : 'normal'};">
                <span class="d-inline-block rounded-circle me-2" style="width:8px; height:8px; background:var(--accent-yellow); flex-shrink:0;"></span>
                <span style="color:var(--text-primary);">${rangeAverageActive ? '✔ ' : ''}<span data-i18n="overview_legend_average">Average (60-74)</span></span>
              </div>
              <div class="d-flex align-items-center" style="opacity: ${rangeNeedsActive ? '1' : '0.45'}; font-weight: ${rangeNeedsActive ? '700' : 'normal'};">
                <span class="d-inline-block rounded-circle me-2" style="width:8px; height:8px; background:var(--accent-red); flex-shrink:0;"></span>
                <span style="color:var(--text-primary);">${rangeNeedsActive ? '✔ ' : ''}<span data-i18n="overview_legend_needs_attention">Needs Attention (&lt;60)</span></span>
              </div>
            </div>
          </div>
          <div>
            <div class="overview-health-label" style="color:${healthColor};">${t(payload.health_status_key, "Good")}</div>
            <div class="overview-health-desc" style="color: var(--text-secondary);">${t(payload.health_desc_key, "")}</div>
          </div>
        </div>
      </div>

      <!-- AI Executive Summary Card (Structured summary dotted leaders & text-primary contrast values) -->
      <div class="col-12 col-lg-6">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div class="overview-card-title">
            <span>
              <i class="bi bi-brilliance text-primary me-2"></i>
              <span data-i18n="financial_advisor_tab_ai_financial_advisor">AI Executive Summary</span>
            </span>
          </div>
          <div class="overview-ai-card-content flex-row align-items-start gap-4" style="height: calc(100% - 75px);">
            <!-- Left Grid with dotted leaders and recommendation paragraphs -->
            <div style="flex:1.25; width:0; height:100%; display:flex; flex-direction:column; justify-content:space-between;">
              <div class="mb-3 pb-2 border-bottom" style="border-color:var(--border-color) !important;">
                
                <!-- Row 1: Portfolio Health -->
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="overview_kpi_portfolio_health" style="flex-shrink:0;">Portfolio Health</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:${healthColor}; flex-shrink:0;">${t(payload.executive_summary.health_status_key, payload.executive_summary.health_status_fallback)}</span>
                </div>

                <!-- Row 2: Net Worth -->
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="overview_kpi_total_net_worth" style="flex-shrink:0;">Net Worth</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:var(--text-primary); flex-shrink:0; display:inline-flex; align-items:center;">
                    ${_money(kpis.total_net_worth)} 
                    <span class="ms-2" style="font-size:11px; font-weight:600; color:${nwTrendIsUp ? 'var(--accent-green)' : 'var(--accent-red)'}; margin-left:6px;">${nwTrendText}</span>
                  </span>
                </div>

                <!-- Row 3: Liquidity -->
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="portfolio_optimizer_liquidity" style="flex-shrink:0;">Liquidity</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:var(--text-primary); flex-shrink:0;">
                    ${fmt(payload.executive_summary.emergency_months)} <span data-i18n="portfolio_optimizer_months_short">mo</span> 
                    <span style="color: var(--text-secondary); font-size:11px; font-weight:normal;">(${t(payload.executive_summary.liquidity_status_key, payload.executive_summary.liquidity_status_fallback)})</span>
                  </span>
                </div>

                <!-- Row 4: Diversification -->
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="portfolio_optimizer_diversification_rating" style="flex-shrink:0;">Diversification</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:var(--text-primary); flex-shrink:0;">${t(payload.executive_summary.diversification_status_key, payload.executive_summary.diversification_status_fallback)}</span>
                </div>

                <!-- Row 5: Goals -->
                <div class="d-flex align-items-center justify-content-between" style="font-size:13px;">
                  <span style="color: var(--text-secondary);" data-i18n="goal_planning_goal_progress" style="flex-shrink:0;">Goals</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold text-end" style="color:var(--text-primary); flex-shrink:0;">
                    <span style="color: var(--accent-green);">${payload.goals.completed}</span> / 
                    <span style="color: var(--accent-primary);">${payload.goals.on_track}</span> / 
                    <span style="color: var(--accent-red);">${payload.goals.delayed}</span>
                  </span>
                </div>

              </div>
              <div class="overview-rec-paragraphs">
                ${recParagraphsHtml}
              </div>
            </div>
            <img class="overview-ai-graphic d-none d-sm-block animate__animated animate__fadeIn" src="/static/images/financial_advisor_overview_hero.svg" alt="AI illustration" style="align-self: flex-start; margin-top: 6px;">
          </div>
          <div class="overview-ai-footer">
            <span>
              <i class="bi bi-calendar3 me-1"></i>
              <span data-i18n="overview_last_updated">Last Updated</span>
            </span>
            <button onclick="switchFinancialAdvisorTab('ai-financial-advisor')">
              <span data-i18n="overview_view_details">View Details</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Alerts Card -->
      <div class="col-12 col-lg-3">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-bell-fill text-warning me-2"></i>
                <span data-i18n="overview_alert_title">Alerts</span>
              </span>
              <a href="javascript:void(0);" onclick="switchFinancialAdvisorTab('opportunity-detection')" style="font-size:12px; font-weight:600; text-decoration:none; color:var(--accent-primary);" data-i18n="overview_view_all">View All</a>
            </div>
            <div class="overview-alerts-list">
              ${alertsHtml}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ROW 2: Four KPI Cards (Lift-on-Hover Effect) -->
    <div class="row g-3 mb-3">
      <!-- KPI 1: Net Worth -->
      <div class="col-12 col-sm-6 col-xl-3" style="cursor:pointer;" onclick="window.location.hash='#balance'">
        <div class="overview-card overview-kpi-card h-100">
          <div class="overview-kpi-icon-wrap" style="background:rgba(123, 147, 201, 0.12); color:#a07cf0; width: 52px; height: 52px; font-size: 28px;">
            <i class="bi bi-wallet2"></i>
          </div>
          <div class="overview-kpi-details">
            <div class="overview-kpi-label" data-i18n="overview_kpi_total_net_worth">Total Net Worth</div>
            <div class="overview-kpi-value">${_money(kpis.total_net_worth)}</div>
            <div class="overview-kpi-trend ${nwTrendClass}">${nwTrendText}</div>
          </div>
        </div>
      </div>

      <!-- KPI 2: Liquid Assets -->
      <div class="col-12 col-sm-6 col-xl-3" style="cursor:pointer;" onclick="window.location.hash='#balance'">
        <div class="overview-card overview-kpi-card h-100">
          <div class="overview-kpi-icon-wrap" style="background:rgba(79, 143, 247, 0.12); color:#4f8ff7; width: 52px; height: 52px; font-size: 28px;">
            <i class="bi bi-droplet-fill"></i>
          </div>
          <div class="overview-kpi-details">
            <div class="overview-kpi-label" data-i18n="overview_kpi_liquid_assets">Liquid Assets</div>
            <div class="overview-kpi-value">${_money(kpis.liquid_assets)}</div>
            <div class="overview-kpi-trend neutral">
              ${t("overview_kpi_months_expenses", "{months} months of expenses").replace("{months}", fmt(Math.round(kpis.emergency_months * 10) / 10))}
            </div>
          </div>
        </div>
      </div>

      <!-- KPI 3: Fixed Assets -->
      <div class="col-12 col-sm-6 col-xl-3" style="cursor:pointer;" onclick="window.location.hash='#fixed-assets'">
        <div class="overview-card overview-kpi-card h-100">
          <div class="overview-kpi-icon-wrap" style="background:rgba(243, 200, 70, 0.12); color:#f3c846; width: 52px; height: 52px; font-size: 28px;">
            <i class="bi bi-house-fill"></i>
          </div>
          <div class="overview-kpi-details">
            <div class="overview-kpi-label" data-i18n="overview_kpi_fixed_assets">Fixed Assets</div>
            <div class="overview-kpi-value">${_money(kpis.fixed_assets)}</div>
            <div class="overview-kpi-trend neutral">
              ${t("overview_kpi_pct_net_worth", "{pct}% of net worth").replace("{pct}", fmt(kpis.fixed_assets_pct))}
            </div>
          </div>
        </div>
      </div>

      <!-- KPI 4: Portfolio Health -->
      <div class="col-12 col-sm-6 col-xl-3" style="cursor:pointer;" onclick="switchFinancialAdvisorTab('portfolio-optimizer')">
        <div class="overview-card overview-kpi-card h-100">
          <div class="overview-kpi-icon-wrap" style="background:rgba(80, 216, 144, 0.12); color:#50d890; width: 52px; height: 52px; font-size: 28px;">
            <i class="bi bi-pie-chart-fill"></i>
          </div>
          <div class="overview-kpi-details">
            <div class="overview-kpi-label" data-i18n="overview_kpi_portfolio_health">Portfolio Health</div>
            <div class="overview-kpi-value">${Math.round(kpis.portfolio_health)}/100</div>
            <div class="overview-kpi-trend" style="color:${healthColor};">${t(kpis.portfolio_health_status_key, "Good")}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ROW 3: Cash Flow, Wealth Growth, Top Opportunities -->
    <div class="row g-3 mb-3">
      <!-- Cash Flow Summary -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-arrow-down-up text-primary me-2"></i>
                <span data-i18n="overview_cash_flow_title">Cash Flow Summary</span>
              </span>
            </div>
            <div class="overview-summary-body">
              <div class="overview-summary-stats">
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_cash_flow_current">Current Cash Balance</div>
                  <div class="overview-stat-value">${_money(payload.cash_flow.current_cash)}</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_cash_flow_change">Expected Change (Next 30 Days)</div>
                  <div class="overview-stat-value ${cfChangeClass}">${cfChangeSign}${_money(cfChangeVal)}</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_cash_flow_next_event">Next Financial Event</div>
                  <div class="overview-stat-value" style="color: var(--text-primary); font-size:12px; font-weight:700;">
                    ${payload.cash_flow.largest_event ? `${t('cash_flow_event_' + payload.cash_flow.largest_event.type, payload.cash_flow.largest_event.type)}: +${_money(payload.cash_flow.largest_event.amount)}` : "-"}
                  </div>
                </div>
              </div>
              <div class="overview-sparkline-wrap">
                <canvas id="overviewCashFlowChart"></canvas>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${payload.cash_flow.target_tab}')">
              <span data-i18n="overview_cash_flow_view">View Cash Flow Forecast</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Wealth Growth Summary -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-graph-up text-purple me-2"></i>
                <span data-i18n="overview_wealth_growth_title">Wealth Growth Summary</span>
              </span>
            </div>
            <div class="overview-summary-body">
              <div class="overview-summary-stats">
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_wealth_growth_current">Current Net Worth</div>
                  <div class="overview-stat-value">${_money(payload.wealth_growth.current_net_worth)}</div>
                </div>
                <div class="overview-stat-row">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_wealth_growth_expected">Expected Net Worth (1 Year)</div>
                  <div class="overview-stat-value" style="color:#8c7cf0;">${_money(payload.wealth_growth.expected_net_worth_1y)}</div>
                </div>
                <div class="overview-stat-row" style="display:flex; gap:16px;">
                  <div>
                    <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_wealth_growth_projected">Projected Growth</div>
                    <div class="overview-stat-value text-success" style="font-size:13px;">${wgGrowthSign}${fmt(wgGrowthVal)}%</div>
                  </div>
                  <div>
                    <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_wealth_growth_cagr">Current CAGR (3 Years)</div>
                    <div class="overview-stat-value text-success" style="font-size:13px;">+${fmt(payload.wealth_growth.cagr_3y)}%</div>
                  </div>
                </div>
              </div>
              <div class="overview-sparkline-wrap">
                <canvas id="overviewWealthGrowthChart"></canvas>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${payload.wealth_growth.target_tab}')">
              <span data-i18n="overview_wealth_growth_view">View Wealth Growth Forecast</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Top Opportunities -->
      <div class="col-12 col-lg-4">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-lightbulb-fill text-warning me-2"></i>
                <span data-i18n="overview_top_opportunities">Top Opportunities</span>
              </span>
              <a href="javascript:void(0);" onclick="switchFinancialAdvisorTab('opportunity-detection')" style="font-size:12px; font-weight:600; text-decoration:none; color:var(--accent-primary);" data-i18n="overview_view_all">View All</a>
            </div>
            <div class="overview-opportunities-list">
              ${opportunitiesHtml}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ROW 4: Portfolio Summary, Goal Progress -->
    <div class="row g-3 mb-3">
      <!-- Portfolio Summary (Scrollbar-Free Allocation Grid) -->
      <div class="col-12 col-lg-6">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-pie-chart text-success me-2"></i>
                <span data-i18n="overview_portfolio_title">Portfolio Summary</span>
              </span>
            </div>
            <div class="overview-portfolio-body">
              <!-- Allocation categories list (scrollbar-free sizing) -->
              <div class="overview-portfolio-stats" style="padding-right: 6px; overflow: hidden; flex: 1;">
                ${allocationRowsHtml}
              </div>
              <!-- Donut Chart with Increased Text Readability -->
              <div class="overview-chart-donut-wrap">
                <canvas id="overviewPortfolioDonutChart"></canvas>
                <div style="position:absolute; top:52%; left:50%; transform:translate(-50%, -56%); text-align:center; pointer-events:none; width: 85%;">
                  <div style="font-size:10px; color:var(--text-secondary); font-weight:600; text-transform:uppercase; letter-spacing:0.8px; margin-bottom: 2px;" data-i18n="overview_total_portfolio">Total Portfolio</div>
                  <div style="font-size:15px; font-weight:800; color:var(--text-primary); line-height:1.2;">${_money(payload.portfolio.total_portfolio)}</div>
                </div>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${payload.portfolio.target_tab}')">
              <span data-i18n="overview_portfolio_view">View Portfolio Optimizer</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Goal Progress -->
      <div class="col-12 col-lg-6">
        <div class="overview-card d-flex flex-column justify-content-between h-100">
          <div>
            <div class="overview-card-title">
              <span>
                <i class="bi bi-bullseye text-danger me-2"></i>
                <span data-i18n="overview_goal_title">Goal Progress</span>
              </span>
            </div>
            <div class="overview-goal-body">
              <!-- Dotted leader rows layout -->
              <div class="overview-goal-stats" style="flex:1;">
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:12px; line-height: 1.2;">
                  <span style="color: var(--text-secondary);" data-i18n="overview_goal_total">Total Goals</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold" style="color: var(--text-primary);">${payload.goals.total}</span>
                </div>
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:12px; line-height: 1.2;">
                  <span style="color: var(--text-secondary);" data-i18n="goal_planning_status_completed">Completed</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold" style="color: var(--accent-green);">${payload.goals.completed}</span>
                </div>
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:12px; line-height: 1.2;">
                  <span style="color: var(--text-secondary);" data-i18n="goal_planning_status_on_track">On Track</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold" style="color: var(--accent-primary);">${payload.goals.on_track}</span>
                </div>
                <div class="d-flex align-items-center justify-content-between mb-2 pb-1" style="font-size:12px; line-height: 1.2;">
                  <span style="color: var(--text-secondary);" data-i18n="goal_planning_status_delayed">Delayed</span>
                  <span style="flex:1; border-bottom:1px dotted var(--border-color); margin:0 8px; align-self:flex-end; opacity:0.4;"></span>
                  <span class="fw-bold" style="color: var(--accent-red);">${payload.goals.delayed}</span>
                </div>
                
                <!-- Standardized Next Goal Due Field -->
                <div class="overview-stat-row mt-3 pt-2 border-top" style="border-color:var(--border-color) !important;">
                  <div class="overview-stat-label" style="color: var(--text-secondary);" data-i18n="overview_kpi_next_goal">Next Goal</div>
                  <div class="overview-stat-value text-primary" style="font-size:13px; font-weight:700; margin-top:2px;">
                    ${payload.goals.next_goal_due ? payload.goals.next_goal_due.name : `<span style="color: var(--text-secondary);" data-i18n="overview_no_financial_goals_yet">No financial goals created yet</span>`}
                  </div>
                  ${payload.goals.next_goal_due ? `
                  <div class="overview-stat-label mt-1" style="font-size:10px; color: var(--text-secondary);"><span data-i18n="overview_goal_due_label">Due:</span> <span class="fw-bold" style="color: var(--text-primary);">${_formatGoalDate(payload.goals.next_goal_due.target_date)}</span></div>
                  ` : ''}
                </div>
              </div>
              
              <div class="overview-chart-donut-wrap d-flex align-items-center justify-content-center">
                <div class="overview-score-ring" style="background:${goalRing}; margin:0;">
                  <div class="overview-score-center" style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <div class="overview-score-value" style="font-size:24px;">${goalProgressPct}%</div>
                    <div style="font-size:10px; color:var(--text-secondary); margin-top:2px;" data-i18n="goal_planning_on_track_goals">On Track</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="overview-btn-footer">
            <button onclick="switchFinancialAdvisorTab('${payload.goals.target_tab}')">
              <span data-i18n="overview_goal_view">View Goal Planning</span>
              <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Note with localized server Last Updated time -->
    <div style="font-size:11px; color:var(--text-secondary); text-align:center; padding:16px 0;">
      <div style="margin-bottom: 6px;">All data is based on your transactions and accounts. Please keep your data updated for accurate insights.</div>
      <div style="font-size:10px; opacity:0.85;">
        <span data-i18n="overview_last_updated">Last Updated</span>
        <div style="margin-top: 4px; font-weight: 700; color: var(--text-primary);">${payload.as_of.day} ${monthName} ${payload.as_of.year} &bull; ${payload.as_of.time}</div>
      </div>
    </div>
  `;

  applyTranslations();

  // Initialize tooltips
  const tooltipTriggerList = [].slice.call(container.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  _drawOverviewCharts(payload);
}

function _drawOverviewCharts(payload) {
  if (!window.Chart) return;

  // 1. Cash Flow Sparkline
  const cfCanvasId = "overviewCashFlowChart";
  const cfCanvas = document.getElementById(cfCanvasId);
  if (cfCanvas) {
    _destroyChart(cfCanvasId);
    const cfTimeline = payload.cash_flow.sparkline || [];
    const labels = cfTimeline.map(p => p.month);
    const values = cfTimeline.map(p => p.balance);

    new Chart(cfCanvas, {
      type: "line",
      data: {
        labels,
        datasets: [{
          data: values,
          borderColor: "var(--accent-primary)",
          borderWidth: 2.5,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.45,
          fill: true,
          backgroundColor: "rgba(26, 110, 245, 0.06)"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: { x: { display: false }, y: { display: false } }
      }
    });
  }

  // 2. Wealth Growth Sparkline
  const wgCanvasId = "overviewWealthGrowthChart";
  const wgCanvas = document.getElementById(wgCanvasId);
  if (wgCanvas) {
    _destroyChart(wgCanvasId);
    const wgTimeline = payload.wealth_growth.sparkline || [];
    const labels = wgTimeline.map(p => p.month);
    const values = wgTimeline.map(p => p.balance);

    new Chart(wgCanvas, {
      type: "line",
      data: {
        labels,
        datasets: [{
          data: values,
          borderColor: "#8c7cf0",
          borderWidth: 2.5,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.45,
          fill: true,
          backgroundColor: "rgba(140, 124, 240, 0.06)"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        scales: { x: { display: false }, y: { display: false } }
      }
    });
  }

  // 3. Portfolio Donut
  const pfCanvasId = "overviewPortfolioDonutChart";
  const pfCanvas = document.getElementById(pfCanvasId);
  if (pfCanvas) {
    _destroyChart(pfCanvasId);
    const chartData = payload.portfolio.allocation_chart || {};
    const labels = (chartData.labels || []).map(labelKey => t(labelKey, labelKey));
    const values = chartData.values || [];

    new Chart(pfCanvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data: values,
          borderColor: "var(--bg-secondary)",
          borderWidth: 2.5,
          backgroundColor: [
            "var(--accent-green)",
            "var(--accent-primary)",
            "#8c7cf0",
            "var(--accent-yellow)",
            "#3ddc84",
            "#5da9ff",
            "#b178ff"
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "75%",
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || "";
                const val = context.parsed || 0;
                return ` ${label}: ${_money(val)}`;
              }
            }
          }
        }
      }
    });
  }
}

async function loadOverview(force = false) {
  if (_overviewData && !force) {
    _renderOverview(_overviewData);
    _overviewLoaded = true;
    return;
  }

  _renderOverviewLoading();
  try {
    const response = await fetch("/api/financial-advisor/overview/");
    if (!response.ok) {
      throw new Error("overview_fetch_failed");
    }
    const payload = await response.json();
    _overviewData = payload;
    _renderOverview(payload);
    _overviewLoaded = true;
  } catch (error) {
    console.error("Overview error:", error);
    _renderOverviewError();
  }
}

function switchFinancialAdvisorTab(tabId) {
  const tabButton = document.getElementById(`fa-tab-${tabId}`);
  if (tabButton) {
    tabButton.click();
    const tabTrigger = new bootstrap.Tab(tabButton);
    tabTrigger.show();
  }
}

// Bind to window context
window.loadOverview = loadOverview;
window.switchFinancialAdvisorTab = switchFinancialAdvisorTab;
