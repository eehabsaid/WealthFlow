"use strict";
// Asset save, delete, sale, sync, CSRF and field toggle
// This file is part of the fixed_assets module. Do not edit directly.

async function loadFixedAssetSyncDropdownData() {
  if (!fixedAssetSyncCurrencies.length || !fixedAssetSyncBanks.length) {
    const [currRes, bankRes] = await Promise.all([
      fetch("/api/currencies/"),
      fetch("/api/banks/"),
    ]);

    if (!currRes.ok) {
      throw new Error(t("error_loading_currencies", "Error loading currencies"));
    }
    if (!bankRes.ok) {
      throw new Error(t("error_loading_banks", "Error loading banks"));
    }

    const currData = await currRes.json();
    const bankData = await bankRes.json();

    fixedAssetSyncCurrencies = Array.isArray(currData.currencies) ? currData.currencies : [];
    fixedAssetSyncBanks = Array.isArray(bankData.banks) ? bankData.banks.filter((b) => b?.is_active !== false) : [];
  }

  if (!fixedAssetBanksWithBalance.length) {
    const withBalanceRes = await fetch("/api/banks/with-balance/");
    if (withBalanceRes.ok) {
      const withBalanceData = await withBalanceRes.json();
      fixedAssetBanksWithBalance = Array.isArray(withBalanceData.banks) ? withBalanceData.banks : [];
    }
  }

  const saleCurrency = document.getElementById("fa_deposit_currency");
  if (saleCurrency) {
    saleCurrency.innerHTML = renderMonetaryCurrencyOptions();
  }

  const purchaseCurrency = document.getElementById("fa_purchase_currency");
  if (purchaseCurrency) {
    purchaseCurrency.innerHTML = renderMonetaryCurrencyOptions();
    purchaseCurrency.value = String(getDefaultPurchaseCurrencyId() || "");
  }

  const saleMethod = document.getElementById("fa_deposit_method");
  if (saleMethod) {
    saleMethod.innerHTML = renderPaymentMethodOptions("Cash");
  }

  const saleBank = document.getElementById("fa_deposit_bank");
  if (saleBank) {
    saleBank.innerHTML = renderBankOptions();
  }
}

async function fillCurrentUsdRate() {
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  try {
    const response = await fetch("/api/rates/");
    if (!response.ok) {
      throw new Error(t("error_loading_rates", "Error loading exchange rates."));
    }
    const payload = await response.json();
    const rates = Array.isArray(payload?.rates) ? payload.rates : [];
    applyPurchaseUsdRateByCurrency(rates);
  } catch (error) {
    showToast(error.message, "danger");
  }
}

function collectSalePayload() {
  return {
    sale_date: document.getElementById("fa_sale_date").value,
    sale_price: parseFloat(document.getElementById("fa_sale_price").value) || 0,
    selling_expenses:
      parseFloat(document.getElementById("fa_selling_expenses").value) || 0,
    net_sale_amount:
      parseFloat(document.getElementById("fa_net_sale_amount").value) || 0,
    deposit_currency_id:
      parseInt(document.getElementById("fa_deposit_currency").value, 10) || null,
    deposit_method:
      document.getElementById("fa_deposit_method").value || "Cash",
    deposit_bank_id:
      parseInt(document.getElementById("fa_deposit_bank").value, 10) || null,
    notes: document.getElementById("fa_sale_notes").value,
  };
}

function validateSaleForm() {
  const saleDate = document.getElementById("fa_sale_date").value;
  const salePrice = parseFloat(document.getElementById("fa_sale_price").value) || 0;

  if (!saleDate) {
    throw new Error(t("sale_date_required", "Sale date is required"));
  }

  if (salePrice <= 0) {
    throw new Error(t("sale_price_required", "Sale price must be greater than zero"));
  }

  const depositCurrencyId = parseInt(document.getElementById("fa_deposit_currency")?.value, 10) || null;
  const depositMethod = document.getElementById("fa_deposit_method")?.value || "Cash";
  const depositBankId = parseInt(document.getElementById("fa_deposit_bank")?.value, 10) || null;

  if (!depositCurrencyId) {
    throw new Error(t("currency_required", "Currency is required."));
  }
  if (shouldRequireBankForMethod(depositMethod) && !depositBankId) {
    throw new Error(t("bank_account_required", "Bank account is required for this payment method"));
  }
}

async function syncAssetSale(assetId, status) {
  if (status === "Sold") {
    validateSaleForm();

    const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(collectSalePayload()),
    });

    if (!response.ok) {
      let message = t("error_saving_sale", "Error saving sale information");
      try {
        const payload = await response.json();
        if (payload?.error_key) {
          message = t(payload.error_key, payload.error || message);
        } else if (payload?.error) {
          message = payload.error;
        }
      } catch (_) {
        // Keep fallback message.
      }
      throw new Error(message);
    }

    return;
  }

  const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
  });

  if (!response.ok && response.status !== 404) {
    let message = t("error_removing_sale", "Error removing sale information");
    try {
      const payload = await response.json();
      if (payload?.error_key) {
        message = t(payload.error_key, payload.error || message);
      } else if (payload?.error) {
        message = payload.error;
      }
    } catch (_) {
      // Keep fallback message.
    }
    throw new Error(message);
  }
}

async function refreshFinancialViewsAfterAssetChange() {
  const route = window.location.hash.replace("#", "");
  if (route === "balance" && typeof renderBalance === "function") {
    await renderBalance();
    return;
  }
  if (route === "dashboard" && typeof renderDashboard === "function") {
    await renderDashboard();
    return;
  }
  if (route === "reports" && typeof renderReports === "function") {
    await renderReports();
    return;
  }
  if (route === "financial-advisor" && typeof renderFinancialAdvisor === "function") {
    await renderFinancialAdvisor();
  }
}

async function saveFixedAsset(assetId = null) {
  const isEdit = assetId !== null;
  const url = isEdit ? `/api/fixed-assets/${assetId}/` : "/api/fixed-assets/";
  const method = isEdit ? "PUT" : "POST";

  const assetType = document.getElementById("fa_type").value;
  const assetStatus = document.getElementById("fa_status").value;
  const isRealEstate = isRealEstateAssetType(assetType);
  const isVehicle = isVehicleAssetType(assetType);
  const isGold = isGoldAssetType(assetType);
  const isOther = isOtherAssetType(assetType);
  const purchasePrice = parseFloat(document.getElementById("fa_purchase_price").value) || 0;

  let purchasePayments = [];
  try {
    purchasePayments = validatePurchasePayments(purchasePrice);
  } catch (validationError) {
    showToast(validationError.message, "danger");
    return;
  }

  const purchaseCurrencyCode = getSelectedPurchaseCurrencyCode();
  const uiUsdRate = parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0;
  const backendUsdRate =
    purchaseCurrencyCode === "USD"
      ? 1
      : purchaseCurrencyCode === "EGP"
        ? (uiUsdRate > 0 ? uiUsdRate : 1)
        : (uiUsdRate > 0 ? (1 / uiUsdRate) : 1);

  const payload = {
    name: document.getElementById("fa_name").value,
    asset_type: assetType,
    purchase_date: document.getElementById("fa_purchase_date").value,
    purchase_price: purchasePrice,
    purchase_usd_rate: backendUsdRate,
    purchase_price_usd:
      parseFloat(document.getElementById("fa_purchase_price_usd").value) || 0,
    purchase_currency_id:
      parseInt(document.getElementById("fa_purchase_currency").value, 10) || null,
    current_market_value:
      parseFloat(document.getElementById("fa_current_value").value) || 0,
    valuation_source: document.getElementById("fa_val_source").value,
    last_valuation_date:
      document.getElementById("fa_last_valuation_date").value || null,
    notes: document.getElementById("fa_notes").value,
    status: assetStatus,
    purchase_payments: purchasePayments,
  };

  if (isGold) {
    payload.valuation_source = "Automatic";
  }

  if (isRealEstate) {
    payload.real_estate_details = {
      country: document.getElementById("re_country").value,
      governorate: document.getElementById("re_governorate").value,
      city: document.getElementById("re_city").value,
      district: document.getElementById("re_district").value,
      address: document.getElementById("re_address").value,
      latitude:
        parseFloat(document.getElementById("re_latitude").value) || null,
      longitude:
        parseFloat(document.getElementById("re_longitude").value) || null,
      apartment_area: parseFloat(document.getElementById("re_area").value) || 0,
      land_share_sqm:
        parseFloat(document.getElementById("re_land_area").value) || 0,
      rooms: parseInt(document.getElementById("re_rooms").value) || 0,
      bathrooms: parseInt(document.getElementById("re_bathrooms").value) || 0,
      floor: parseInt(document.getElementById("re_floor").value) || 0,
      building_floors:
        parseInt(document.getElementById("re_b_floors").value) || 0,
      building_year: parseInt(document.getElementById("re_year").value) || 0,
      facades: document.getElementById("re_facades").value,
      finishing_level: document.getElementById("re_finishing").value,
      furnished_status: document.getElementById("re_furnished").value,
      electricity: document.getElementById("re_util_elec").checked,
      water: document.getElementById("re_util_water").checked,
      gas: document.getElementById("re_util_gas").checked,
      elevator: document.getElementById("re_feat_elevator").checked,
      garage: document.getElementById("re_feat_garage").checked,
      licensed: document.getElementById("re_feat_licensed").checked,
      has_land_share: document.getElementById("re_has_land_share").checked,
      land_share: document.getElementById("re_land_share").value,
      description: document.getElementById("re_description").value,
    };
    payload.mortgage_details = collectMortgagePayload();
    payload.rental_details = collectRentalPayload();
    payload.renovations = collectRenovations();
    payload.acquisition_costs = collectAcquisitionCosts();
  } else {
    payload.real_estate_details = null;
    payload.mortgage_details = null;
    payload.rental_details = null;
    payload.renovations = [];
    payload.acquisition_costs = [];
  }

  payload.vehicle_details = isVehicle ? collectVehicleDetailsPayload() : null;
  payload.gold_details = isGold ? collectGoldDetailsPayload() : null;
  payload.other_asset_details = isOther ? collectOtherAssetDetailsPayload() : null;
  payload.maintenance = isVehicle ? collectMaintenance() : [];
  payload.insurance = isVehicle ? collectInsurance() : [];

  payload.furniture = isRealEstate ? collectFurniture() : [];
  payload.valuation_history = (isRealEstate || isVehicle || isOther) ? collectValuationHistory() : [];

  const moneyMovementGroups = [
    { label: t("acquisition_costs", "Acquisition Costs"), rows: payload.acquisition_costs || [] },
    { label: t("renovation", "Renovation"), rows: payload.renovations || [] },
    { label: t("furniture", "Furniture"), rows: payload.furniture || [] },
    { label: t("rental", "Rental"), rows: payload.rental_details && (payload.rental_details.monthly_rent > 0) ? [payload.rental_details] : [] },
  ];
  for (const group of moneyMovementGroups) {
    for (const row of group.rows) {
      if (shouldRequireBankForMethod(row.payment_method || row.receive_method) && !row.bank_id) {
        hideLoading();
        throw new Error(`${group.label}: ${t("bank_account_required", "Bank account is required for this payment method")}`);
      }
    }
  }

  showLoading();
  try {
    const response = await fetch(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let message = t("error_saving_fixed_asset", "Error saving fixed asset");
      try {
        const errorPayload = await response.json();
        if (errorPayload?.error_key) {
          message = t(errorPayload.error_key, errorPayload.error || message);
        } else if (errorPayload?.error) {
          message = errorPayload.error;
        }
      } catch (_) {
        // Keep fallback message.
      }
      throw new Error(message);
    }

    const savedAsset = await response.json();

  // Only touch the sale endpoint when there's actually something to do:
  // status is "Sold" (create/update the sale record), or a sale record
  // already exists and needs to be removed because status moved away
  // from "Sold". Skips a redundant DELETE call on every ordinary save.
  if (assetStatus === "Sold" || savedAsset.sale) {
    await syncAssetSale(savedAsset.id, assetStatus);
  }

    const files = document.getElementById("propertyPhotoInput").files;

    if (files.length > 0) {
        for (const file of files) {
            const formData = new FormData();
            formData.append("photos", file);

            const uploadResponse = await fetch(
                `/api/fixed-assets/${savedAsset.id}/photos/`,
                {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: formData,
                }
            );

            if (!uploadResponse.ok)
                throw new Error("Failed to upload property photo.");

            const uploadedPhoto = await uploadResponse.json();
            if (Array.isArray(uploadedPhoto)) {
              propertyPhotos.push(...uploadedPhoto);
            } else if (uploadedPhoto) {
              propertyPhotos.push(uploadedPhoto);
            }
        }

        renderPropertyPhotoGallery();
        document.getElementById("propertyPhotoInput").value = "";
    }

    showToast(
      isEdit
        ? t("fixed_asset_updated_success", "Asset updated successfully")
        : t("fixed_asset_added_success", "Asset added successfully"),
      "success",
    );

    const returnPurity = goldPurityReturnContext;

    closeModal(); // Call global dynamic closing match
    await fetchAndRenderFixedAssets();
    await refreshFinancialViewsAfterAssetChange();

    if (returnPurity) {
      setTimeout(() => {
        showGoldPurityGroupDetails(returnPurity);
      }, 180);
    }

    document.getElementById("propertyPhotoInput").value = "";
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

async function deleteFixedAsset(assetId) {
  if (!confirm("Are you sure you want to delete this asset?")) return;
  showLoading();
  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/`, {
      method: "DELETE",
      headers: { "X-CSRFToken": getCsrfToken() },
    });
    if (!response.ok) throw new Error("Failed to delete fixed asset");
    showToast("Asset deleted successfully", "success");
    fetchAndRenderFixedAssets();
    refreshFinancialViewsAfterAssetChange();
    return true;
  } catch (err) {
    showToast(err.message, "danger");
    return false;
  } finally {
    hideLoading();
  }
}

function showSaleModal(assetId, assetName, currentMarketValue) {
  const html = `
        <div class="modal-header">
            <h5 class="modal-title"><span data-i18n="sell_asset">Sell Asset</span>: ${assetName}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="assetSaleForm">
                <div class="mb-3">
                    <label class="form-label" data-i18n="sale_date">Sale Date</label>
                    <input type="date" class="form-control" id="sale_date" required>
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="sale_price">Sale Price</label>
                    <input type="number" step="0.01" class="form-control" id="sale_price" value="${currentMarketValue}" required>
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="selling_expenses">Selling Expenses</label>
                    <input type="number" step="0.01" class="form-control" id="selling_expenses" value="0">
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="notes">Notes</label>
                    <textarea class="form-control" id="sale_notes" rows="2"></textarea>
                </div>
            </form>
        </div>

        <!-- Information Cards -->
        <div class="container-fluid py-4">

            <div class="row g-4">

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="general_information">
                                General Information
                            </h6>

                            <div class="d-grid gap-2">
                              <div class="d-flex justify-content-between"><span data-i18n="asset_type">Asset Type</span><span id="details_asset_type" class="fw-bold"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_date">Purchase Date</span><span id="details_purchase_date"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="valuation_source">Valuation Source</span><span id="details_valuation_source"></span></div>
                            </div>

                        </div>

                    </div>

                </div>

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="financial_information">
                                Financial Information
                            </h6>

                            <div class="d-grid gap-2">
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_price_egp">Purchase Price</span><span id="details_purchase_price" class="fw-bold"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_price_usd">Purchase USD</span><span id="details_purchase_usd"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="last_valuation_date">Last Valuation</span><span id="details_last_valuation"></span></div>
                            </div>

                        </div>

                    </div>

                </div>

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="notes">
                                Notes
                            </h6>

                            <div id="details_notes"
                                style="white-space:pre-wrap;"></div>

                        </div>

                    </div>

                </div>

            </div>

        </div>

        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="submitAssetSale(${assetId})" data-i18n="confirm_sale">Confirm Sale</button>
        </div>
    `;
  showModal(html);
  applyTranslations();
}

async function submitAssetSale(assetId) {
  const salePrice =
    parseFloat(document.getElementById("sale_price").value) || 0;
  const expenses =
    parseFloat(document.getElementById("selling_expenses").value) || 0;
  const netSaleAmount = salePrice - expenses;

  const payload = {
    sale_date: document.getElementById("sale_date").value,
    sale_price: salePrice,
    selling_expenses: expenses,
    net_sale_amount: netSaleAmount,
    notes: document.getElementById("sale_notes").value,
  };

  showLoading();
  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) throw new Error("Failed to process sale");

    showToast("Asset marked as Sold successfully!", "success");
    closeModal();
    fetchAndRenderFixedAssets();
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

function toggleRealEstateFields() {
  const assetType = document.getElementById("fa_type").value;
  const reSection = document.getElementById("realEstateSection");
  const isRealEstate = isRealEstateAssetType(assetType);

  if (reSection) {
    reSection.style.display = isRealEstate ? "block" : "none";
  }
}

function getCsrfToken() {
  return (
    document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1] || ""
  );
}

