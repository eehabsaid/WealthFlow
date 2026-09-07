"use strict";
// Create/update fixed asset form submission handler.
// Part of the fixed_assets module (split from the former monolithic
// validation.js, 200-line rule). Do not edit directly.

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
        ? uiUsdRate > 0
          ? uiUsdRate
          : 1
        : uiUsdRate > 0
          ? 1 / uiUsdRate
          : 1;

  const payload = {
    name: document.getElementById("fa_name").value,
    asset_type: assetType,
    purchase_date: document.getElementById("fa_purchase_date").value,
    purchase_price: purchasePrice,
    purchase_usd_rate: backendUsdRate,
    purchase_price_usd: parseFloat(document.getElementById("fa_purchase_price_usd").value) || 0,
    purchase_currency_id:
      parseInt(document.getElementById("fa_purchase_currency").value, 10) || null,
    current_market_value: parseFloat(document.getElementById("fa_current_value").value) || 0,
    valuation_source: document.getElementById("fa_val_source").value,
    last_valuation_date: document.getElementById("fa_last_valuation_date").value || null,
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
      latitude: parseFloat(document.getElementById("re_latitude").value) || null,
      longitude: parseFloat(document.getElementById("re_longitude").value) || null,
      apartment_area: parseFloat(document.getElementById("re_area").value) || 0,
      land_share_sqm: parseFloat(document.getElementById("re_land_area").value) || 0,
      rooms: parseInt(document.getElementById("re_rooms").value) || 0,
      bathrooms: parseInt(document.getElementById("re_bathrooms").value) || 0,
      floor: parseInt(document.getElementById("re_floor").value) || 0,
      building_floors: parseInt(document.getElementById("re_b_floors").value) || 0,
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
  payload.valuation_history = isRealEstate || isVehicle || isOther ? collectValuationHistory() : [];

  const moneyMovementGroups = [
    { label: t("acquisition_costs", "Acquisition Costs"), rows: payload.acquisition_costs || [] },
    { label: t("renovation", "Renovation"), rows: payload.renovations || [] },
    { label: t("furniture", "Furniture"), rows: payload.furniture || [] },
    {
      label: t("rental", "Rental"),
      rows:
        payload.rental_details && payload.rental_details.monthly_rent > 0
          ? [payload.rental_details]
          : [],
    },
  ];
  for (const group of moneyMovementGroups) {
    for (const row of group.rows) {
      if (shouldRequireBankForMethod(row.payment_method || row.receive_method) && !row.bank_id) {
        hideLoading();
        throw new Error(
          `${group.label}: ${t("bank_account_required", "Bank account is required for this payment method")}`
        );
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

        const uploadResponse = await fetch(`/api/fixed-assets/${savedAsset.id}/photos/`, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCsrfToken(),
          },
          body: formData,
        });

        if (!uploadResponse.ok) throw new Error("Failed to upload property photo.");

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
      "success"
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

