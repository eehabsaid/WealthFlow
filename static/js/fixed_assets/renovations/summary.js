"use strict";
// Renovation summary strip totals (item count, EGP/USD sums).
// Part of the fixed_assets module (split from the former monolithic
// renovations.js, 200-line rule). Do not edit directly.

function updateRenovationSummary() {
  const summaryStrip = document.getElementById("renovationSummaryStrip");
  const badge = document.getElementById("renovation-count-badge");

  const rows = document.querySelectorAll(".renovation-row");
  const count = rows.length;

  if (badge) {
    badge.textContent = count > 0 ? `(${count})` : "";
  }

  let totalEGP = 0;
  let totalUSD = 0;

  rows.forEach((row) => {
    const egp = parseFloat(row.querySelector(".renovation-egp").value) || 0;
    const usd = parseFloat(row.querySelector(".renovation-usd").value) || 0;
    totalEGP += egp;
    totalUSD += usd;
  });

  const fmt = (n) =>
    Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  if (summaryStrip) {
    summaryStrip.innerHTML = `
      <div class="stat">
        <span class="stat-label" data-i18n="items">Items</span>
        <span class="stat-value">${count}</span>
      </div>
      <div class="stat">
        <span class="stat-label" data-i18n="total_egp">Total (EGP)</span>
        <span class="stat-value">${fmt(totalEGP)}</span>
      </div>
      <div class="stat">
        <span class="stat-label" data-i18n="total_usd">Total (USD)</span>
        <span class="stat-value">${fmt(totalUSD)}</span>
      </div>
    `;
    if (typeof applyTranslations === "function") {
      applyTranslations();
    }
  }
}
