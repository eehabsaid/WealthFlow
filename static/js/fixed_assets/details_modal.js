"use strict";
// showFixedAssetModal — full asset form modal builder

async function showFixedAssetModal(assetId = null, options = {}) {
  if (options?.returnPurityKey) {
    setGoldPurityReturnContext(options.returnPurityKey);
  } else {
    clearGoldPurityReturnContext();
  }

  const isEdit = assetId !== null;
  currentEditingAssetId = isEdit ? assetId : null;
  currentAssetHasPurchaseSync = false;
  const modalTitleKey = isEdit ? "edit_fixed_asset" : "add_fixed_asset";
  const modalTitleDefault = isEdit
    ? "Edit Asset Details"
    : "Register New Fixed Asset";

  const html = `
        <div class="modal-header">
            <h5 class="modal-title fixed-assets-heading" data-i18n="${modalTitleKey}">${modalTitleDefault}</h5>
            <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
        </div>
        <div class="modal-body" style="max-height: 75vh; overflow-y: auto; overflow-x: hidden; padding: 1.5rem;">
          <form id="fixedAssetForm">

              <ul class="nav nav-tabs mb-4" id="fixedAssetTabs" role="tablist">
                  <li class="nav-item" role="presentation">
                      <button class="nav-link active"
                              id="general-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#general-pane"
                              type="button"
                              role="tab"
                              aria-controls="general-pane"
                              aria-selected="true"
                              data-i18n="general">
                          General
                      </button>
                  </li>

                  <li class="nav-item" role="presentation">
                      <button class="nav-link"
                              id="property-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#property-pane"
                              type="button"
                              role="tab"
                              aria-controls="property-pane"
                              aria-selected="false"
                              data-i18n="property">
                          Property
                      </button>
                  </li>

                    <li class="nav-item d-none" role="presentation" id="vehicle-tab-item">
                      <button class="nav-link"
                          id="vehicle-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#vehicle-pane"
                          type="button"
                          role="tab"
                          aria-controls="vehicle-pane"
                          aria-selected="false"
                          data-i18n="vehicle">
                        Vehicle
                      </button>
                    </li>

                    <li class="nav-item d-none" role="presentation" id="gold-tab-item">
                      <button class="nav-link"
                          id="gold-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#gold-pane"
                          type="button"
                          role="tab"
                          aria-controls="gold-pane"
                          aria-selected="false"
                          data-i18n="gold_details">
                        Gold Details
                      </button>
                    </li>

                    <li class="nav-item d-none" role="presentation" id="other-details-tab-item">
                      <button class="nav-link"
                          id="other-details-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#other-details-pane"
                          type="button"
                          role="tab"
                          aria-controls="other-details-pane"
                          aria-selected="false"
                          data-i18n="details">
                        Details
                      </button>
                    </li>

                    <li class="nav-item" role="presentation">
                      <button class="nav-link"
                          id="photos-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#photos-pane"
                          type="button"
                          role="tab"
                          aria-controls="photos-pane"
                          aria-selected="false"
                          data-i18n="photos">
                        Photos
                      </button>
                    </li>

                  <li class="nav-item" role="presentation">
                      <button class="nav-link"
                              id="renovation-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#renovation-pane"
                              type="button"
                              role="tab"
                              aria-controls="renovation-pane"
                              aria-selected="false"
                              data-i18n="renovations">
                          Renovations
                      </button>
                  </li>

                        <li class="nav-item d-none" role="presentation" id="maintenance-tab-item">
                          <button class="nav-link"
                              id="maintenance-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#maintenance-pane"
                              type="button"
                              role="tab"
                              aria-controls="maintenance-pane"
                              aria-selected="false"
                              data-i18n="maintenance">
                            Maintenance
                          </button>
                        </li>

                        <li class="nav-item d-none" role="presentation" id="insurance-tab-item">
                          <button class="nav-link"
                              id="insurance-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#insurance-pane"
                              type="button"
                              role="tab"
                              aria-controls="insurance-pane"
                              aria-selected="false"
                              data-i18n="insurance">
                            Insurance
                          </button>
                        </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="furniture-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#furniture-pane"
                                type="button"
                                role="tab"
                                aria-controls="furniture-pane"
                                aria-selected="false"
                                data-i18n="furniture">
                              Furniture
                            </button>
                          </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="valuation-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#valuation-pane"
                                type="button"
                                role="tab"
                                aria-controls="valuation-pane"
                                aria-selected="false"
                                data-i18n="valuation_history">
                              Valuation History
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="mortgage-tab-item">
                            <button class="nav-link"
                                id="mortgage-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#mortgage-pane"
                                type="button"
                                role="tab"
                                aria-controls="mortgage-pane"
                                aria-selected="false"
                                data-i18n="mortgage">
                              Mortgage
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="rental-tab-item">
                            <button class="nav-link"
                                id="rental-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#rental-pane"
                                type="button"
                                role="tab"
                                aria-controls="rental-pane"
                                aria-selected="false"
                                data-i18n="rental">
                              Rental
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="sale-tab-item">
                            <button class="nav-link"
                                id="sale-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#sale-pane"
                                type="button"
                                role="tab"
                                aria-controls="sale-pane"
                                aria-selected="false"
                                data-i18n="sale">
                              Sale
                            </button>
                          </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="documents-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#documents-pane"
                                type="button"
                                role="tab"
                                aria-controls="documents-pane"
                                aria-selected="false"
                                data-i18n="documents_title">
                              Documents
                            </button>
                          </li>
              </ul>

              <div class="tab-content" id="fixedAssetTabsContent">

                  ${renderGeneralTab()}

                  ${renderPropertyTab()}

                  ${renderVehicleTab()}

                  ${renderGoldTab()}

                  ${renderOtherDetailsTab()}

                  ${renderPhotosTab()}

                  ${renderRenovationTab()}

                    ${renderFurnitureTab()}

                    ${renderValuationTab()}

                    ${renderMaintenanceTab()}

                    ${renderInsuranceTab()}

                    ${renderMortgageTab()}

                    ${renderRentalTab()}

                    ${renderSaleTab()}

                    ${renderDocumentsTab()}

              </div> <!-- End Tab Content -->

          </form>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="saveFixedAsset(${assetId})" data-i18n="save">Save</button>
        </div>
    `;

  showModal(html);
  applyTranslations();
  await populateGoldSettingsDropdowns();
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
  ["acquisitionContainer", "renovationContainer", "furnitureContainer", "valuationContainer", "maintenanceContainer", "insuranceContainer"].forEach((id) => {
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

  propertyTab.addEventListener("shown.bs.tab", function () {
    if (propertyMap) {
      setTimeout(() => {
        propertyMap.invalidateSize();
      }, 50);
    }
  });

  document
    .getElementById("btnLocateProperty")
    .addEventListener("click", locatePropertyOnMap);
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
