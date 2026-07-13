"use strict";
// Valuation history rows management
// This file is part of the fixed_assets module. Do not edit directly.

function updateValuationSummary() {
  const summaryStrip = document.getElementById("valuationSummaryStrip");
  const badge = document.getElementById("valuation-count-badge");

  const rows = document.querySelectorAll(".valuation-row");
  const count = rows.length;

  if (badge) {
    badge.textContent = count > 0 ? `(${count})` : "";
  }

  let latestEGP = 0;
  let latestDate = null;

  rows.forEach(row => {
    const valDate = row.querySelector(".valuation-date").value;
    const valMarket = parseFloat(row.querySelector(".valuation-market-value").value) || 0;
    if (valDate) {
      if (!latestDate || valDate > latestDate) {
        latestDate = valDate;
        latestEGP = valMarket;
      }
    }
  });

  const fmt = (n) => Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  if (summaryStrip) {
    summaryStrip.innerHTML = `
      <div class="stat">
        <span class="stat-label" data-i18n="items">Items</span>
        <span class="stat-value">${count}</span>
      </div>
      <div class="stat">
        <span class="stat-label" data-i18n="latest_value">Latest Value</span>
        <span class="stat-value">${latestDate ? 'EGP ' + fmt(latestEGP) : '-'}</span>
      </div>
    `;
    if (typeof applyTranslations === "function") {
      applyTranslations();
    }
  }
}

function addValuationRow(data = {}, expand = false) {
  const container = document.getElementById("valuationContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "valuation-row item-card card";

  const sourceVal = data.valuation_source || "Manual";
  const dateVal = data.valuation_date || "";
  const marketVal = data.market_value || "";
  const notesVal = data.notes || "";

  const fmt = (n) => Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const initialAmountPreview = marketVal ? `EGP ${fmt(parseFloat(marketVal) || 0)}` : "EGP 0.00";

  row.innerHTML = `
    <div class="item-header card-header">
      <div class="item-header-left">
        <svg class="item-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
        <span class="item-category-badge" data-i18n="val_${sourceVal.toLowerCase()}">${sourceVal}</span>
        <span class="item-name-preview">${dateVal || t("unnamed_item", "(Unnamed item)")}</span>
      </div>
      <div class="item-header-right">
        <span class="item-amount-preview">${initialAmountPreview}</span>
        <button type="button" class="item-remove-btn" title="Remove" onclick="const r = this.closest('.valuation-row'); r.remove(); updateValuationSummary();">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z"/></svg>
        </button>
      </div>
    </div>
    <div class="item-body card-body">
      <div class="field-grid">
        <div class="field">
          <label class="form-label small" data-i18n="date">Date</label>
          <input type="date" class="form-control valuation-date" value="${dateVal}">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="current_market_value">Market Value</label>
          <input type="number" step="0.01" class="form-control valuation-market-value" value="${marketVal}">
        </div>
        <div class="field span-2">
          <label class="form-label small" data-i18n="valuation_source">Valuation Source</label>
          <select class="form-select valuation-source">
            <option value="Manual" data-i18n="val_manual">Manual Input</option>
            <option value="Automatic" data-i18n="val_automatic">System Synced</option>
          </select>
        </div>
        <div class="field span-4">
          <label class="form-label small" data-i18n="notes">Notes</label>
          <textarea class="form-control valuation-notes" rows="2">${notesVal}</textarea>
        </div>
      </div>
    </div>
  `;

  if (expand) {
    container.prepend(row);
    row.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } else {
    container.appendChild(row);
  }

  row.querySelector(".valuation-source").value = sourceVal;

  // Event Listeners for Live Sync
  const dateInput = row.querySelector(".valuation-date");
  const datePreview = row.querySelector(".item-name-preview");
  dateInput.addEventListener("input", () => {
    datePreview.textContent = dateInput.value || t("unnamed_item", "(Unnamed item)");
    updateValuationSummary();
  });

  const sourceSelect = row.querySelector(".valuation-source");
  const sourceBadge = row.querySelector(".item-category-badge");
  sourceSelect.addEventListener("change", () => {
    const s = sourceSelect.value;
    sourceBadge.setAttribute("data-i18n", `val_${s.toLowerCase()}`);
    sourceBadge.textContent = s;
    if (typeof applyTranslations === "function") {
      applyTranslations();
    }
  });

  const marketInput = row.querySelector(".valuation-market-value");
  const amountPreview = row.querySelector(".item-amount-preview");
  marketInput.addEventListener("input", () => {
    amountPreview.textContent = `EGP ${fmt(parseFloat(marketInput.value) || 0)}`;
    updateValuationSummary();
  });

  // Reusable card accordion init
  initCollapsibleCard(row, "#valuationContainer");

  // Initial expansion state
  const isFirstCard = container.children.length === 1;
  const shouldExpand = expand;
  toggleCollapsibleCard(row, "#valuationContainer", shouldExpand);

  if (typeof applyTranslations === "function") {
    applyTranslations();
  }

  updateValuationSummary();
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


