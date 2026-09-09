"use strict";
// Opportunity detection tab — single opportunity card HTML builder. Split
// out of opportunity_detection.js (200-line backlog). Bare global;
// converted from a forEach callback body (accumulating into `html +=`) to a
// standalone function that returns one card's markup. Original indentation
// preserved (not de-nested) to keep the returned markup byte-identical.
// ════════════════════════════════════════════════════════════════════════════

function buildOpportunityCardHtml(item) {
  const iconClass = _getOpportunityIconClass(item.key);
  const sev = String(item.severity || "medium").toLowerCase();
  const badgeClass =
    sev === "high"
      ? "opp-badge-high"
      : sev === "low"
        ? "opp-badge-low"
        : sev === "info"
          ? "opp-badge-info"
          : "opp-badge-medium";

  let signalsHtml = "";
  if (item.signals) {
    if ("idle_cash" in item.signals) {
      // Gold opportunity signals box
      const s = item.signals;
      const trend7Color = s.gold_trend_7d >= 0 ? "var(--accent-green)" : "var(--accent-red)";
      const trend30Color = s.gold_trend_30d >= 0 ? "var(--accent-green)" : "var(--accent-red)";
      signalsHtml = `
            <div class="opp-signals-box">
              <table class="opp-signals-table">
                <tr>
                  <td class="opp-signal-label" data-i18n="signal_idle_cash"></td>
                  <td class="opp-signal-val">${_fmtIntValue(s.idle_cash)} EGP</td>
                </tr>
                <tr>
                  <td class="opp-signal-label" data-i18n="signal_gold_trend_7d"></td>
                  <td class="opp-signal-val" style="color:${trend7Color};">${_fmtTrendPct(s.gold_trend_7d)}</td>
                </tr>
                <tr>
                  <td class="opp-signal-label" data-i18n="signal_gold_trend_30d"></td>
                  <td class="opp-signal-val" style="color:${trend30Color};">${_fmtTrendPct(s.gold_trend_30d)}</td>
                </tr>
                <tr>
                  <td class="opp-signal-label" data-i18n="signal_current_allocation"></td>
                  <td class="opp-signal-val">${s.current_gold_allocation_pct}% <span style="font-weight:400; color:var(--text-secondary);">(target &ge;${s.target_gold_min_pct}%)</span></td>
                </tr>
              </table>
            </div>
          `;
    } else if ("maturity_date" in item.signals) {
      // Certificate maturity opportunity signals box
      const s = item.signals;
      signalsHtml = `
            <div class="opp-signals-box">
              <table class="opp-signals-table">
                <tr>
                  <td class="opp-signal-label" data-i18n="signal_maturity_date"></td>
                  <td class="opp-signal-val">${formatDate(s.maturity_date) || "-"}</td>
                </tr>
                <tr>
                  <td class="opp-signal-label" data-i18n="signal_days_left"></td>
                  <td class="opp-signal-val">${s.days_left}</td>
                </tr>
                <tr>
                  <td class="opp-signal-label" data-i18n="signal_maturity_amount"></td>
                  <td class="opp-signal-val">${_fmtMoneyValue(s.maturity_value)} EGP</td>
                </tr>
                <tr>
                  <td class="opp-signal-label" data-i18n="signal_bank"></td>
                  <td class="opp-signal-val">${s.bank || "-"}</td>
                </tr>
              </table>
            </div>
          `;
    }
  }

  let highlightedHtml = "";
  if (item.highlighted_amount != null && item.highlighted_amount > 0) {
    highlightedHtml = `
          <div class="opp-highlighted-amount">
            ${_fmtIntValue(item.highlighted_amount)} EGP
          </div>
        `;
  }

  let actionBoxHtml = "";
  if (item.action_template_key) {
    const paramsCopy = { ...(item.action_params || {}) };
    if ("amount" in paramsCopy) {
      paramsCopy.amount = _fmtIntValue(paramsCopy.amount);
    }
    const paramsStr = JSON.stringify(paramsCopy).replace(/'/g, "&apos;").replace(/"/g, "&quot;");
    actionBoxHtml = `
          <div class="opp-action-box">
            <span data-i18n-key="${item.action_template_key}" data-i18n-params="${paramsStr}"></span>
          </div>
        `;
  } else if (item.impact_key) {
    actionBoxHtml = `
          <div class="opp-action-box">
            <span data-i18n="${item.impact_key}"></span>
          </div>
        `;
  }

  return `
        <div class="opp-card fade-in-up" si-modern-card>
          <div class="d-flex justify-content-between align-items-center mb-1">
            <div class="d-flex align-items-center gap-2" style="color:var(--text-primary);">
              <i class="bi ${iconClass}" style="font-size:22px; color:var(--accent-yellow);"></i>
              <h6 style="margin:0; font-weight:700; font-size:16px; color:var(--text-primary);" data-i18n="${item.title_key}"></h6>
            </div>
            <div>
              <span class="opp-badge ${badgeClass}" data-i18n="${item.severity_key}"></span>
            </div>
          </div>
          ${signalsHtml}
          ${highlightedHtml}
          ${actionBoxHtml}
        </div>
      `;
}
