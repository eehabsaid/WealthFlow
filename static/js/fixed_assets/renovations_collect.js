"use strict";
// Renovations: collect + USD sync helpers
// This file is part of the fixed_assets module. Do not edit directly.

function collectRenovations() {
  const renovations = [];

  document.querySelectorAll(".renovation-row").forEach((row) => {
    renovations.push({
      id: row.dataset.renovationId ? parseInt(row.dataset.renovationId, 10) : null,

      date: row.querySelector(".renovation-date").value,

      category: row.querySelector(".renovation-category").value,

      description: row.querySelector(".renovation-description").value,

      furniture_id: parseInt(row.querySelector(".renovation-furniture")?.value, 10) || null,

      amount_egp: parseFloat(row.querySelector(".renovation-egp").value) || 0,

      usd_rate: parseFloat(row.querySelector(".renovation-usd-rate")?.value) || 0,

      amount_usd: parseFloat(row.querySelector(".renovation-usd").value) || 0,

      payment_method: row.querySelector(".renovation-payment-method")?.value || "Cash",

      bank_id: parseInt(row.querySelector(".renovation-bank")?.value, 10) || null,

      notes: row.querySelector(".renovation-notes").value,
    });
  });

  return renovations;
}

function updateRenovationUSD(input) {
  const row = input.closest(".renovation-row");

  const egp = parseFloat(row.querySelector(".renovation-egp").value) || 0;

  const rate = parseFloat(row.querySelector(".renovation-usd-rate")?.value) || 0;

  const usdInput = row.querySelector(".renovation-usd");

  if (rate > 0) {
    usdInput.value = (egp / rate).toFixed(2);
  } else {
    usdInput.value = "";
  }
}
