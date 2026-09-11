"use strict";

function _buildComparisonRowsHtml(data) {
  if (!data) return "";

  const base = data.baseline || {};
  const adj = data.adjusted || {};
  const delta = data.delta || {};

  const nwBase = base.net_worth_12m || 0;
  const nwAdj = adj.net_worth_12m || 0;
  const nwDeltaVal = delta.net_worth_12m || 0;
  const nwFav = delta.net_worth_12m_favorable;
  const nwBadgeBg = nwFav
    ? "rgba(34,197,94,0.15)"
    : nwDeltaVal === 0
      ? "rgba(108,117,125,0.15)"
      : "rgba(239,68,68,0.15)";
  const nwBadgeColor = nwFav
    ? "var(--accent-green, #22c55e)"
    : nwDeltaVal === 0
      ? "var(--text-muted, #9ca3af)"
      : "var(--accent-red, #ef4444)";

  const riskBase = base.risk_score || 0;
  const riskAdj = adj.risk_score || 0;
  const riskDeltaVal = delta.risk_score || 0;
  const riskFav = delta.risk_score_favorable;
  const riskBadgeBg = riskFav
    ? "rgba(34,197,94,0.15)"
    : riskDeltaVal === 0
      ? "rgba(108,117,125,0.15)"
      : "rgba(239,68,68,0.15)";
  const riskBadgeColor = riskFav
    ? "var(--accent-green, #22c55e)"
    : riskDeltaVal === 0
      ? "var(--text-muted, #9ca3af)"
      : "var(--accent-red, #ef4444)";

  const covBase = base.cash_coverage_months;
  const covAdj = adj.cash_coverage_months;
  const covDeltaVal = delta.cash_coverage_months;
  const covFav = delta.cash_coverage_favorable;
  const covBadgeBg = covFav
    ? "rgba(34,197,94,0.15)"
    : covDeltaVal === 0 || covDeltaVal === null
      ? "rgba(108,117,125,0.15)"
      : "rgba(239,68,68,0.15)";
  const covBadgeColor = covFav
    ? "var(--accent-green, #22c55e)"
    : covDeltaVal === 0 || covDeltaVal === null
      ? "var(--text-muted, #9ca3af)"
      : "var(--accent-red, #ef4444)";

  return `
    <div class="d-flex flex-column gap-3">
      <!-- Metric 1: Net Worth -->
      <div class="p-3 rounded d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
        <div class="fw-medium" style="color:var(--text-primary);" data-i18n="whatif_networth_12m">Net Worth (12 months)</div>
        <div class="d-flex align-items-center gap-3">
          <span class="small" style="color:var(--text-secondary);">${_money(nwBase)}</span>
          <i class="bi bi-arrow-right text-muted"></i>
          <span class="fw-bold" style="color:var(--text-primary);">${_money(nwAdj)}</span>
          <span class="badge px-2 py-1 fw-semibold" style="background:${nwBadgeBg}; color:${nwBadgeColor};">
            ${_fmtDelta(nwDeltaVal)}
          </span>
        </div>
      </div>

      <!-- Metric 2: Risk Score -->
      <div class="p-3 rounded d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
        <div class="fw-medium" style="color:var(--text-primary);" data-i18n="whatif_risk_score">Risk Score</div>
        <div class="d-flex align-items-center gap-3">
          <span class="small" style="color:var(--text-secondary);">${riskBase.toFixed(1)}</span>
          <i class="bi bi-arrow-right text-muted"></i>
          <span class="fw-bold" style="color:var(--text-primary);">${riskAdj.toFixed(1)}</span>
          <span class="badge px-2 py-1 fw-semibold" style="background:${riskBadgeBg}; color:${riskBadgeColor};">
            ${_fmtDelta(riskDeltaVal, false, 1)}
          </span>
        </div>
      </div>

      <!-- Metric 3: Cash Coverage -->
      <div class="p-3 rounded d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2" style="background:var(--bg-tertiary); border:1px solid var(--border-color);">
        <div class="fw-medium" style="color:var(--text-primary);" data-i18n="whatif_cash_coverage">Cash Coverage (months)</div>
        <div class="d-flex align-items-center gap-3">
          <span class="small" style="color:var(--text-secondary);">${covBase !== null && covBase !== undefined ? covBase.toFixed(1) : "-"}</span>
          <i class="bi bi-arrow-right text-muted"></i>
          <span class="fw-bold" style="color:var(--text-primary);">${covAdj !== null && covAdj !== undefined ? covAdj.toFixed(1) : "-"}</span>
          <span class="badge px-2 py-1 fw-semibold" style="background:${covBadgeBg}; color:${covBadgeColor};">
            ${_fmtDelta(covDeltaVal, false, 1)}
          </span>
        </div>
      </div>
    </div>
  `;
}
