"use strict";
// Gold form details payload collector
// This file is part of the fixed_assets module. Do not edit directly.

function collectGoldDetailsPayload() {
  return {
    gold_type: document.getElementById("gd_gold_type")?.value || "",
    purity: document.getElementById("gd_purity")?.value || "",
    weight: parseFloat(document.getElementById("gd_weight")?.value) || 0,
    unit: document.getElementById("gd_unit")?.value || "gram",
    cashback_per_gram: parseFloat(document.getElementById("gd_cashback_per_gram")?.value) || 0,
    purchase_weight: parseFloat(document.getElementById("gd_purchase_weight")?.value) || 0,
  };
}
function updateGoldValuation() {
  if (!isGoldAssetType(document.getElementById("fa_type")?.value)) {
    return;
  }
  refreshGoldCalculatedFields();
}

