"use strict";
// Fixed asset modal — post-render wiring: field change/input listeners,
// document manager + form state reset, and property map + final data load.
// Split out of details_modal.js (200-line backlog). Bare globals; converted
// from inline code in showFixedAssetModal to standalone functions taking
// explicit params.
// ════════════════════════════════════════════════════════════════════════════

function wireFixedAssetModalFieldListeners() {
  const propertyTab = document.getElementById("property-tab");
  const statusField = document.getElementById("fa_status");
  const salePriceField = document.getElementById("fa_sale_price");
  const sellingExpensesField = document.getElementById("fa_selling_expenses");
  const currentValueField = document.getElementById("fa_current_value");
  const monthlyRentField = document.getElementById("fa_monthly_rent");
  const remainingBalanceField = document.getElementById("fa_remaining_balance");
  const assetTypeField = document.getElementById("fa_type");
  const goldPurityField = document.getElementById("gd_purity");
  const goldUnitField = document.getElementById("gd_unit");

  if (statusField) {
    statusField.addEventListener("change", toggleSaleTabVisibility);
  }

  if (salePriceField) {
    salePriceField.addEventListener("input", updateNetSaleAmount);
  }

  if (sellingExpensesField) {
    sellingExpensesField.addEventListener("input", updateNetSaleAmount);
  }

  if (currentValueField) {
    currentValueField.addEventListener("input", () => {
      updateMortgageSummary();
      updateRentalSummary();
    });
  }

  if (monthlyRentField) {
    monthlyRentField.addEventListener("input", updateRentalSummary);
  }

  if (remainingBalanceField) {
    remainingBalanceField.addEventListener("input", updateMortgageSummary);
  }

  if (assetTypeField) {
    assetTypeField.addEventListener("change", toggleRealEstateDependentTabs);
  }

  if (goldPurityField) {
    goldPurityField.addEventListener("change", updateGoldValuation);
  }

  if (goldUnitField) {
    goldUnitField.addEventListener("input", updateGoldValuation);
  }

  return propertyTab;
}

async function resetFixedAssetModalFormState(assetId) {
  if (window.DocumentManager) {
    window.DocumentManager.init({
      containerId: "fixedAssetDocumentManagerContainer",
      parentType: "fixed_asset",
      parentId: assetId,
      disabledMessage: t("documents_save_first", "Save this record first to manage documents."),
    });
  }

  await loadFixedAssetSyncDropdownData();
  currentAssetFurnitureOptions = [];
  resetPurchasePaymentsForm();
  addPurchasePaymentRow();
  propertyPhotos = [];
  renderPropertyPhotoGallery();
  [
    "acquisitionContainer",
    "renovationContainer",
    "furnitureContainer",
    "valuationContainer",
    "maintenanceContainer",
    "insuranceContainer",
  ].forEach((id) => {
    const container = document.getElementById(id);
    if (container) container.innerHTML = "";
  });
  updateAcquisitionSummary();
  if (typeof updateRenovationSummary === "function") updateRenovationSummary();
  if (typeof updateFurnitureSummary === "function") updateFurnitureSummary();
  if (typeof updateValuationSummary === "function") updateValuationSummary();
  resetSaleForm();
  toggleSaleDepositBankField();
  resetMortgageForm();
  resetRentalForm();
  toggleSaleTabVisibility();
  toggleRealEstateDependentTabs();
}

async function wireFixedAssetPropertyMapAndLoad(propertyTab, assetId, isEdit) {
  propertyTab.addEventListener("shown.bs.tab", function () {
    if (propertyMap) {
      setTimeout(() => {
        propertyMap.invalidateSize();
      }, 50);
    }
  });

  document.getElementById("btnLocateProperty").addEventListener("click", locatePropertyOnMap);
  const refreshValuationButton = document.getElementById("btnRefreshPropertyValuation");
  if (refreshValuationButton) {
    refreshValuationButton.addEventListener("click", refreshPropertyValuation);
  }
  initializePropertyMap();
  if (isEdit) {
    await loadFixedAsset(assetId);
  } else {
    maybeRefreshPurchaseUsdRateOnLoad();
  }
}
