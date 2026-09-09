"use strict";
// Overview tab — buildOverviewSummaryRowsHtml orchestrator. Split into
// sibling files (200-line backlog): overview_cards_kpi.js,
// overview_cards_row3.js, overview_cards_row4.js. This file assembles ROW 3,
// ROW 4, and the footer note in the same order as the original.
// ════════════════════════════════════════════════════════════════════════════

function buildOverviewSummaryRowsHtml(params) {
  const { asOf, monthName } = params;

  return `
${buildOverviewRow3Html(params)}
${buildOverviewRow4Html(params)}
    <!-- Footer Note with localized server Last Updated time -->
    <div style="font-size:11px; color:var(--text-secondary); text-align:center; padding:16px 0;">
      <div style="margin-bottom: 6px;">All data is based on your transactions and accounts. Please keep your data updated for accurate insights.</div>
      <div style="font-size:10px; opacity:0.85;">
        <span data-i18n="overview_last_updated">Last Updated</span>
        <div style="margin-top: 4px; font-weight: 700; color: var(--text-primary);">${asOf.day || ""} ${monthName} ${asOf.year || ""} &bull; ${asOf.time || ""}</div>
      </div>
    </div>
  `;
}

window.buildOverviewSummaryRowsHtml = buildOverviewSummaryRowsHtml;
