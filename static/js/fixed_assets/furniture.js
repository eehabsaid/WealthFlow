"use strict";
// Furniture rows management
// This file is part of the fixed_assets module. Do not edit directly.

function addFurnitureRow(data = {}) {
  const container = document.getElementById("furnitureContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "row g-2 mb-3 furniture-row";
  row.innerHTML = `
    <div class="col-md-3"><label class="form-label small" data-i18n="asset_name">Name</label><input type="text" class="form-control furniture-name" value="${data.name || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="category">Category</label><input type="text" class="form-control furniture-category" value="${data.category || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="purchase_date">Purchase Date</label><input type="date" class="form-control furniture-purchase-date" value="${data.purchase_date || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="amount_egp">Amount</label><input type="number" step="0.01" class="form-control furniture-egp" value="${data.amount_egp || ""}" oninput="updateFurnitureUSD(this)"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="amount_usd">Amount USD</label><input type="number" step="0.01" class="form-control furniture-usd" value="${data.amount_usd || ""}" readonly></div>
    <div class="col-md-1"><label class="form-label small">&nbsp;</label><button type="button" class="btn btn-danger w-100" onclick="this.closest('.furniture-row').remove()"><i class="bi bi-trash"></i></button></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="purchase_usd_rate">USD Exchange Rate</label><input type="number" step="0.0001" class="form-control furniture-usd-rate" value="${data.usd_rate || document.getElementById("fa_purchase_usd_rate")?.value || ""}" oninput="updateFurnitureUSD(this)"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="quantity">Quantity</label><input type="number" step="1" class="form-control furniture-quantity" value="${data.quantity || 1}"></div>
    <div class="col-md-8"><label class="form-label small" data-i18n="notes">Notes</label><textarea class="form-control furniture-notes" rows="2">${data.notes || ""}</textarea></div>
  `;
  container.appendChild(row);
  applyTranslations();
  updateFurnitureUSD(row.querySelector(".furniture-egp"));
}

function updateFurnitureUSD(input) {
  const row = input.closest(".furniture-row");
  if (!row) return;
  const egp = parseFloat(row.querySelector(".furniture-egp").value) || 0;
  const rate = parseFloat(row.querySelector(".furniture-usd-rate").value) || 0;
  const usdInput = row.querySelector(".furniture-usd");
  usdInput.value = rate > 0 ? (egp / rate).toFixed(2) : "";
}

function collectFurniture() {
  const furniture = [];
  document.querySelectorAll(".furniture-row").forEach((row) => {
    const name = row.querySelector(".furniture-name").value;
    if (!name) return;
    furniture.push({
      name,
      category: row.querySelector(".furniture-category").value,
      purchase_date: row.querySelector(".furniture-purchase-date").value || null,
      amount_egp: parseFloat(row.querySelector(".furniture-egp").value) || 0,
      usd_rate: parseFloat(row.querySelector(".furniture-usd-rate").value) || 0,
      amount_usd: parseFloat(row.querySelector(".furniture-usd").value) || 0,
      quantity: parseInt(row.querySelector(".furniture-quantity").value, 10) || 1,
      notes: row.querySelector(".furniture-notes").value,
    });
  });
  return furniture;
}

