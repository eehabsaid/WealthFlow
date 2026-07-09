"use strict";
// Property valuation field population and refresh
// This file is part of the fixed_assets module. Do not edit directly.

function populatePropertyValuationFields(realEstate = {}) {
  const estimateField = document.getElementById("re_last_estimated_market_price");
  const dateField = document.getElementById("re_last_valuation_date");
  const providerField = document.getElementById("re_valuation_provider");

  if (estimateField) {
    const value = realEstate?.last_estimated_market_price;
    estimateField.value = value !== null && value !== undefined && value !== "" ? value : "";
  }
  if (dateField) {
    dateField.value = realEstate?.last_valuation_date || "";
  }
  if (providerField) {
    providerField.value = realEstate?.valuation_provider || "";
  }
}

async function refreshPropertyValuation() {
  if (!currentEditingAssetId) {
    showToast(t("save_asset_before_valuation", "Save this asset first before refreshing valuation."), "warning");
    return;
  }

  try {
    const response = await fetch(`/api/fixed-assets/${currentEditingAssetId}/valuation/refresh/`, {
      method: "POST",
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || t("error_refreshing_property_valuation", "Failed to refresh property valuation."));
    }

    const asset = payload.asset || {};
    const realEstate = asset.real_estate || {};
    document.getElementById("fa_current_value").value = asset.current_market_value || 0;
    document.getElementById("fa_last_valuation_date").value = asset.last_valuation_date || "";
    document.getElementById("fa_val_source").value = asset.valuation_source || "Manual";
    populatePropertyValuationFields(realEstate);

    if (payload.updated) {
      showToast(t("property_valuation_refreshed", "Property valuation refreshed."), "success");
    } else {
      showToast(t("property_valuation_unavailable", "No automatic valuation was available for this property."), "warning");
    }
  } catch (error) {
    showToast(error.message || t("error_refreshing_property_valuation", "Failed to refresh property valuation."), "error");
  }
}

