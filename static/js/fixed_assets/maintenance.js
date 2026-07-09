"use strict";
// Maintenance rows management
// This file is part of the fixed_assets module. Do not edit directly.

function addMaintenanceRow(data = {}) {
  const container = document.getElementById("maintenanceContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "row g-2 mb-3 maintenance-row";
  row.innerHTML = `
    <div class="col-md-3"><label class="form-label small" data-i18n="date">Date</label><input type="date" class="form-control maintenance-date" value="${data.date || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="type">Type</label><input type="text" class="form-control maintenance-type" value="${data.type || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="cost">Cost</label><input type="number" step="0.01" class="form-control maintenance-cost" value="${data.cost || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="notes">Notes</label><input type="text" class="form-control maintenance-notes" value="${data.notes || ""}"></div>
    <div class="col-md-1"><label class="form-label small">&nbsp;</label><button type="button" class="btn btn-danger w-100" onclick="this.closest('.maintenance-row').remove()"><i class="bi bi-trash"></i></button></div>
  `;
  container.appendChild(row);
  applyTranslations();
}

function collectMaintenance() {
  const items = [];
  document.querySelectorAll(".maintenance-row").forEach((row) => {
    const date = row.querySelector(".maintenance-date")?.value;
    if (!date) return;
    items.push({
      date,
      type: row.querySelector(".maintenance-type")?.value || "",
      cost: parseFloat(row.querySelector(".maintenance-cost")?.value) || 0,
      notes: row.querySelector(".maintenance-notes")?.value || "",
    });
  });
  return items;
}

