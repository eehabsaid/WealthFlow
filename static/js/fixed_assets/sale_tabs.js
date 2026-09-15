"use strict";
// Sale tab: real-estate dependent tab visibility
// This file is part of the fixed_assets module. Do not edit directly.

function toggleRealEstateDependentTabs() {
  const assetType = document.getElementById("fa_type")?.value;
  const isRealEstate = isRealEstateAssetType(assetType);
  const isVehicle = isVehicleAssetType(assetType);
  const isGold = isGoldAssetType(assetType);
  const isOther = isOtherAssetType(assetType);
  const supportsValuationHistory = isRealEstate || isVehicle || isOther;
  const mortgageTabItem = document.getElementById("mortgage-tab-item");
  const rentalTabItem = document.getElementById("rental-tab-item");
  const vehicleTabItem = document.getElementById("vehicle-tab-item");
  const goldTabItem = document.getElementById("gold-tab-item");
  const otherDetailsTabItem = document.getElementById("other-details-tab-item");
  const renovationTab = document.getElementById("renovation-tab")?.closest("li");
  const furnitureTab = document.getElementById("furniture-tab")?.closest("li");
  const valuationTab = document.getElementById("valuation-tab")?.closest("li");
  const maintenanceTabItem = document.getElementById("maintenance-tab-item");
  const insuranceTabItem = document.getElementById("insurance-tab-item");
  const mortgagePane = document.getElementById("mortgage-pane");
  const rentalPane = document.getElementById("rental-pane");
  const propertyTab = document.getElementById("property-tab")?.closest("li");
  const propertyPane = document.getElementById("property-pane");
  const vehiclePane = document.getElementById("vehicle-pane");
  const goldPane = document.getElementById("gold-pane");
  const otherDetailsPane = document.getElementById("other-details-pane");
  const renovationPane = document.getElementById("renovation-pane");
  const furniturePane = document.getElementById("furniture-pane");
  const valuationPane = document.getElementById("valuation-pane");
  const maintenancePane = document.getElementById("maintenance-pane");
  const insurancePane = document.getElementById("insurance-pane");
  const generalTabButton = document.getElementById("general-tab");

  [
    propertyTab,
    propertyPane,
    mortgageTabItem,
    rentalTabItem,
    mortgagePane,
    rentalPane,
    renovationTab,
    renovationPane,
    furnitureTab,
    furniturePane,
    vehicleTabItem,
    vehiclePane,
    maintenanceTabItem,
    maintenancePane,
    insuranceTabItem,
    insurancePane,
    goldTabItem,
    goldPane,
    otherDetailsTabItem,
    otherDetailsPane,
    valuationTab,
    valuationPane,
  ].forEach((element) => {
    if (element) {
      element.classList.add("d-none");
    }
  });

  [
    propertyTab,
    propertyPane,
    renovationTab,
    renovationPane,
    furnitureTab,
    furniturePane,
    valuationTab,
    valuationPane,
    mortgageTabItem,
    mortgagePane,
    rentalTabItem,
    rentalPane,
  ].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !isRealEstate);
    }
  });

  [
    vehicleTabItem,
    vehiclePane,
    maintenanceTabItem,
    maintenancePane,
    insuranceTabItem,
    insurancePane,
  ].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !isVehicle);
    }
  });

  [goldTabItem, goldPane].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !isGold);
    }
  });

  [valuationTab, valuationPane].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !supportsValuationHistory);
    }
  });

  [otherDetailsTabItem, otherDetailsPane].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !isOther);
    }
  });

  applyGoldReadOnlyState(isGold);

  if (isGold) {
    refreshGoldCalculatedFields();
  }

  [
    "mortgage-tab",
    "rental-tab",
    "property-tab",
    "renovation-tab",
    "furniture-tab",
    "valuation-tab",
    "vehicle-tab",
    "maintenance-tab",
    "insurance-tab",
    "gold-tab",
    "other-details-tab",
  ].forEach((tabId) => {
    const tab = document.getElementById(tabId);
    const hiddenParent = tab?.closest("li")?.classList.contains("d-none");
    if (hiddenParent && tab?.classList.contains("active") && generalTabButton) {
      bootstrap.Tab.getOrCreateInstance(generalTabButton).show();
    }
  });

  toggleRealEstateFields();
}
