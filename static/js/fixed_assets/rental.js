"use strict";
// Rental form helpers
// This file is part of the fixed_assets module. Do not edit directly.

function updateRentalSummary() {
  const monthlyRent = parseFloat(document.getElementById("fa_monthly_rent")?.value) || 0;
  const annualRent = monthlyRent * 12;
  const currentValue = parseFloat(document.getElementById("fa_current_value")?.value) || 0;
  const rentalYield = currentValue > 0 ? (annualRent / currentValue) * 100 : 0;
  const annualRentField = document.getElementById("fa_annual_rent");
  const rentalYieldField = document.getElementById("fa_rental_yield");

  if (annualRentField) annualRentField.value = annualRent.toFixed(2);
  if (rentalYieldField) rentalYieldField.value = rentalYield.toFixed(2);
}

function resetRentalForm() {
  [
    "fa_monthly_rent",
    "fa_occupancy_rate",
    "fa_tenant_name",
    "fa_contract_start",
    "fa_contract_end",
    "fa_rental_notes",
  ].forEach((id) => {
    const field = document.getElementById(id);
    if (field) field.value = "";
  });
  ["fa_annual_rent", "fa_rental_yield"].forEach((id) => {
    const field = document.getElementById(id);
    if (field) field.value = "";
  });
  const methodField = document.getElementById("fa_rental_receive_method");
  if (methodField) {
    methodField.value = "Cash";
    toggleMoneyMovementBankField(methodField, "rental");
  }
  const bankField = document.getElementById("fa_rental_bank");
  if (bankField) bankField.value = "";
}

async function deleteRentalDetails() {
  resetRentalForm();
  updateRentalSummary();
  if (currentEditingAssetId !== null && currentEditingAssetId !== undefined) {
    await saveFixedAsset(currentEditingAssetId);
  }
}

function populateRentalForm(rental) {
  resetRentalForm();
  if (!rental) return;

  document.getElementById("fa_monthly_rent").value = rental.monthly_rent || 0;
  document.getElementById("fa_occupancy_rate").value = rental.occupancy_rate || 0;
  document.getElementById("fa_tenant_name").value = rental.tenant_name || "";
  document.getElementById("fa_contract_start").value = rental.contract_start || "";
  document.getElementById("fa_contract_end").value = rental.contract_end || "";
  document.getElementById("fa_rental_notes").value = rental.notes || "";

  const methodField = document.getElementById("fa_rental_receive_method");
  if (methodField) {
    methodField.value = rental.receive_method || "Cash";
    toggleMoneyMovementBankField(methodField, "rental");
  }
  const bankField = document.getElementById("fa_rental_bank");
  if (bankField) bankField.value = rental.bank_id || "";

  updateRentalSummary();
}

function collectRentalPayload() {
  return {
    monthly_rent: parseFloat(document.getElementById("fa_monthly_rent")?.value) || 0,
    occupancy_rate: parseFloat(document.getElementById("fa_occupancy_rate")?.value) || 0,
    tenant_name: document.getElementById("fa_tenant_name")?.value || "",
    contract_start: document.getElementById("fa_contract_start")?.value || null,
    contract_end: document.getElementById("fa_contract_end")?.value || null,
    receive_method: document.getElementById("fa_rental_receive_method")?.value || "Cash",
    bank_id: parseInt(document.getElementById("fa_rental_bank")?.value, 10) || null,
    notes: document.getElementById("fa_rental_notes")?.value || "",
  };
}
