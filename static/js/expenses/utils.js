'use strict';

function yearOptions(currentYear) {
  let opts = "";
  for (let y = currentYear; y >= 2020; y--) {
    opts += `<option value="${y}" ${y === currentYear ? "selected" : ""}>${y}</option>`;
  }
  return opts;
}

function getTopCategory(entries) {
  const totals = {};
  entries.forEach((e) => {
    const key = e.category_name || "Other";
    if (!totals[key])
      totals[key] = { name: key, icon: e.category_icon || "💰", total: 0 };
    totals[key].total += (e.amount_egp || 0);
  });
  const top = Object.values(totals).sort((a, b) => b.total - a.total)[0];
  return top || { name: "—", icon: "💰", total: 0 };
}

/* ── Expense Modal ──────────────────────────────────────────── */

async function refreshFinancialViewsAfterExpenseChange() {
  const route = window.location.hash.replace("#", "");
  if (route === "balance" && typeof renderBalance === "function") {
    await renderBalance();
    return;
  }
  if (route === "dashboard" && typeof renderDashboard === "function") {
    await renderDashboard();
  }
}