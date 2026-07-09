"use strict";
// Mortgage form helpers
// This file is part of the fixed_assets module. Do not edit directly.

function updateMortgageSummary() {
  const currentValue = parseFloat(document.getElementById("fa_current_value")?.value) || 0;
  const remainingBalance = parseFloat(document.getElementById("fa_remaining_balance")?.value) || 0;
  const netEquityField = document.getElementById("fa_net_equity");

  if (netEquityField) {
    netEquityField.value = (currentValue - remainingBalance).toFixed(2);
  }
}

function resetMortgageForm() {
  [
    "fa_loan_amount",
    "fa_remaining_balance",
    "fa_monthly_installment",
    "fa_interest_rate",
    "fa_mortgage_start_date",
    "fa_mortgage_end_date",
  ].forEach((id) => {
    const field = document.getElementById(id);
    if (field) field.value = "";
  });
  const netEquityField = document.getElementById("fa_net_equity");
  if (netEquityField) netEquityField.value = "";
}

async function deleteMortgageDetails() {
  resetMortgageForm();
  updateMortgageSummary();
  if (currentEditingAssetId !== null && currentEditingAssetId !== undefined) {
    await saveFixedAsset(currentEditingAssetId);
  }
}

function populateMortgageForm(mortgage) {
  resetMortgageForm();
  if (!mortgage) return;

  document.getElementById("fa_loan_amount").value = mortgage.loan_amount || 0;
  document.getElementById("fa_remaining_balance").value = mortgage.remaining_balance || 0;
  document.getElementById("fa_monthly_installment").value = mortgage.monthly_installment || 0;
  document.getElementById("fa_interest_rate").value = mortgage.interest_rate || 0;
  document.getElementById("fa_mortgage_start_date").value = mortgage.start_date || "";
  document.getElementById("fa_mortgage_end_date").value = mortgage.end_date || "";
  updateMortgageSummary();
}

function collectMortgagePayload() {
  return {
    loan_amount: parseFloat(document.getElementById("fa_loan_amount")?.value) || 0,
    remaining_balance: parseFloat(document.getElementById("fa_remaining_balance")?.value) || 0,
    monthly_installment: parseFloat(document.getElementById("fa_monthly_installment")?.value) || 0,
    interest_rate: parseFloat(document.getElementById("fa_interest_rate")?.value) || 0,
    start_date: document.getElementById("fa_mortgage_start_date")?.value || null,
    end_date: document.getElementById("fa_mortgage_end_date")?.value || null,
  };
}

