"use strict";

// Overview tab — list-builder helpers (alerts, opportunities, allocation
// rows). Split out of overview_render.js (200-line backlog). Bare globals.
// ════════════════════════════════════════════════════════════════════════════

function buildOverviewAlertsHtml(payload) {
  const alertsHtml =
    (payload.alerts || []).length > 0
      ? (payload.alerts || [])
          .map((alert) => {
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
          })
          .join("")
      : `<div style="text-align:center; padding:32px 16px; color:var(--text-secondary); font-size:13px;" data-i18n="overview_no_alerts">No alerts</div>`;
  return alertsHtml;
}

function buildOverviewOpportunitiesHtml(payload) {
  const opportunitiesHtml =
    (payload.opportunities || []).length > 0
      ? (payload.opportunities || [])
          .map((opp) => {
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
              "Potential impact: ",
              "Potential impact:",
              "الأثر المحتمل: ",
              "الأثر المحتمل:",
              "Möglicher Effekt: ",
              "Möglicher Effekt:",
              "Impact potentiel : ",
              "Impact potentiel :",
              "Impact potentiel:",
              "Potential impact ",
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
          })
          .join("")
      : `<div style="text-align:center; padding:32px 16px; color:var(--text-secondary); font-size:13px;" data-i18n="overview_no_optimization_opportunities">No optimization opportunities</div>`;
  return opportunitiesHtml;
}

function buildOverviewAllocationRowsHtml(portfolio) {
  const allocationRowsHtml = (portfolio.allocation_cards || [])
    .map((card) => {
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
    })
    .join("");
  return allocationRowsHtml;
}
