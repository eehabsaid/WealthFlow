"use strict";
// Valuation history rows management
// This file is part of the fixed_assets module. Do not edit directly.

function addValuationRow(data = {}) {
  const container = document.getElementById("valuationContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "row g-2 mb-3 valuation-row";
  row.innerHTML = `
    <div class="col-md-3"><label class="form-label small" data-i18n="date">Date</label><input type="date" class="form-control valuation-date" value="${data.valuation_date || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="current_market_value">Market Value</label><input type="number" step="0.01" class="form-control valuation-market-value" value="${data.market_value || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="valuation_source">Valuation Source</label><select class="form-select valuation-source"><option value="Manual" data-i18n="val_manual">Manual Input</option><option value="Automatic" data-i18n="val_automatic">System Synced</option></select></div>
    <div class="col-md-2"><label class="form-label small">&nbsp;</label><button type="button" class="btn btn-danger w-100" onclick="this.closest('.valuation-row').remove()"><i class="bi bi-trash"></i></button></div>
    <div class="col-md-12"><label class="form-label small" data-i18n="notes">Notes</label><textarea class="form-control valuation-notes" rows="2">${data.notes || ""}</textarea></div>
  `;
  container.appendChild(row);
  row.querySelector(".valuation-source").value = data.valuation_source || "Manual";
  applyTranslations();
}

function collectValuationHistory() {
  const valuationHistory = [];
  document.querySelectorAll(".valuation-row").forEach((row) => {
    const valuationDate = row.querySelector(".valuation-date").value;
    if (!valuationDate) return;
    valuationHistory.push({
      valuation_date: valuationDate,
      market_value: parseFloat(row.querySelector(".valuation-market-value").value) || 0,
      valuation_source: row.querySelector(".valuation-source").value,
      notes: row.querySelector(".valuation-notes").value,
    });
  });
  return valuationHistory;
}

