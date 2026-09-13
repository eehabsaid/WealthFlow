"use strict";
// Acquisition costs: collect + USD sync helpers
// This file is part of the fixed_assets module. Do not edit directly.

function collectAcquisitionCosts() {
  const costs = [];

  document.querySelectorAll(".acquisition-row").forEach((row) => {
    costs.push({
      id: row.dataset.acquisitionId ? parseInt(row.dataset.acquisitionId, 10) : null,
      date: row.querySelector(".acquisition-date").value,
      category: row.querySelector(".acquisition-category").value,
      description: row.querySelector(".acquisition-description").value,
      amount_egp: parseFloat(row.querySelector(".acquisition-egp").value) || 0,
      usd_rate: parseFloat(row.querySelector(".acquisition-usd-rate")?.value) || 0,
      amount_usd: parseFloat(row.querySelector(".acquisition-usd").value) || 0,
      payment_method: row.querySelector(".acquisition-payment-method")?.value || "Cash",
      bank_id: parseInt(row.querySelector(".acquisition-bank")?.value, 10) || null,
      notes: row.querySelector(".acquisition-notes").value,
    });
  });

  return costs;
}

function updateAcquisitionUSD(input) {
  const row = input.closest(".acquisition-row");
  const egp = parseFloat(row.querySelector(".acquisition-egp").value) || 0;
  const rate = parseFloat(row.querySelector(".acquisition-usd-rate")?.value) || 0;
  const usdInput = row.querySelector(".acquisition-usd");

  if (rate > 0) {
    usdInput.value = (egp / rate).toFixed(2);
  } else {
    usdInput.value = "";
  }
}
