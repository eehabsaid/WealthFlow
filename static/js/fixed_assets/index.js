"use strict";
// Entry-point: re-exports all public symbols onto window
// This file is part of the fixed_assets module. Do not edit directly.

// index.js — re-exports all public functions onto window for HTML backward
// compatibility. Must be loaded LAST after all other module files.

window.renderFixedAssets = renderFixedAssets;
window.switchFixedAssetsTab = switchFixedAssetsTab;
window.updateFixedAssetsTabButtons = updateFixedAssetsTabButtons;
window.renderFixedAssetsHeaderAction = renderFixedAssetsHeaderAction;
window.renderActiveFixedAssetsTab = renderActiveFixedAssetsTab;
window.fetchAndRenderFixedAssets = fetchAndRenderFixedAssets;
window.normalizeFixedAssetsData = normalizeFixedAssetsData;

window.renderFixedAssetsList = renderFixedAssetsList;
window.showGoldPurityGroupDetails = showGoldPurityGroupDetails;

window.renderFixedAssetsDashboard = renderFixedAssetsDashboard;
window.renderFixedAssetsAnalytics = renderFixedAssetsAnalytics;
window.renderFixedAssetsReports = renderFixedAssetsReports;
window.toggleFixedAssetsReportScope = toggleFixedAssetsReportScope;
window.downloadFixedAssetsReport = downloadFixedAssetsReport;

window.showFixedAssetModal = showFixedAssetModal;
window.showFixedAssetDetails = showFixedAssetDetails;
window.handleAssetWindowClose = handleAssetWindowClose;
window.setGoldPurityReturnContext = setGoldPurityReturnContext;
window.clearGoldPurityReturnContext = clearGoldPurityReturnContext;
window.openGoldPurchaseDetails = openGoldPurchaseDetails;
window.openGoldPurchaseEditor = openGoldPurchaseEditor;
window.deleteFixedAssetFromGoldGroup = deleteFixedAssetFromGoldGroup;

window.saveFixedAsset = saveFixedAsset;
window.deleteFixedAsset = deleteFixedAsset;
window.showSaleModal = showSaleModal;
window.submitAssetSale = submitAssetSale;

window.openInsuranceDocumentsModal = openInsuranceDocumentsModal;
window.refreshPropertyValuation = refreshPropertyValuation;
window.toggleFixedAssetsReportScope = toggleFixedAssetsReportScope;
window.toggleRealEstateFields = toggleRealEstateFields;
window.toggleSaleDepositBankField = toggleSaleDepositBankField;
window.togglePurchasePaymentBankField = togglePurchasePaymentBankField;

window.addRenovationRow = addRenovationRow;
window.updateRenovationUSD = updateRenovationUSD;
window.addFurnitureRow = addFurnitureRow;
window.updateFurnitureUSD = updateFurnitureUSD;
window.addValuationRow = addValuationRow;
window.addMaintenanceRow = addMaintenanceRow;
window.addInsuranceRow = addInsuranceRow;
window.addPurchasePaymentRow = addPurchasePaymentRow;
window.removePurchasePaymentRow = removePurchasePaymentRow;

window.removePropertyPhoto = removePropertyPhoto;
window.updatePurchasePriceUSD = updatePurchasePriceUSD;
window.handlePurchaseCurrencyChange = handlePurchaseCurrencyChange;
window.fillCurrentUsdRate = fillCurrentUsdRate;
window.updateNetSaleAmount = updateNetSaleAmount;
window.updateMortgageSummary = updateMortgageSummary;
window.updateRentalSummary = updateRentalSummary;
window.updateGoldValuation = updateGoldValuation;
window.deleteMortgageDetails = deleteMortgageDetails;
window.deleteRentalDetails = deleteRentalDetails;

// Auto-init when navigating directly to the fixed assets hash
if (window.location.hash === "#fixed-assets") {
  renderFixedAssets();
}
