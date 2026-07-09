"use strict";
// loadFixedAsset — populate edit form from API data
// This file is part of the fixed_assets module. Do not edit directly.

async function loadFixedAsset(assetId) {

    currentEditingAssetId = assetId;
  showLoading();
  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/`);
    if (!response.ok) throw new Error("Failed to load asset data");
    const asset = await response.json();

    document.getElementById("fa_name").value = asset.name || "";
    document.getElementById("fa_type").value = asset.asset_type || FIXED_ASSET_TYPES.REAL_ESTATE;
    document.getElementById("fa_status").value = asset.status || "Owned";
    document.getElementById("fa_purchase_date").value =
      asset.purchase_date || "";
    document.getElementById("fa_purchase_price").value =
      asset.purchase_price || 0;
    document.getElementById("fa_purchase_usd_rate").value =
      asset.purchase_usd_rate || 1;
    document.getElementById("fa_purchase_price_usd").value =
      asset.purchase_price_usd || 0;
    const existingPurchasePayments = Array.isArray(asset.purchase_payments) ? asset.purchase_payments : [];
    currentAssetHasPurchaseSync = existingPurchasePayments.length > 0;
    populatePurchasePaymentsForm(existingPurchasePayments, asset.purchase_price || 0, false);
    maybeRefreshPurchaseUsdRateOnLoad();
    document.getElementById("fa_current_value").value =
      asset.current_market_value || 0;
    document.getElementById("fa_last_valuation_date").value =
      asset.last_valuation_date || "";
    document.getElementById("fa_val_source").value =
      asset.valuation_source || "Manual";
    document.getElementById("fa_last_valuation_date").value =
      asset.last_valuation_date || "";
    document.getElementById("fa_notes").value = asset.notes || "";
    populateSaleForm(asset.sale || null);
    populateMortgageForm(asset.mortgage || null);
    populateRentalForm(asset.rental || null);
    toggleSaleTabVisibility();
    // ---------------- Property Photos ----------------

    propertyPhotos = asset.photos || [];

    renderPropertyPhotoGallery();

    toggleRealEstateDependentTabs();

    const vehicle = asset.vehicle_details || {};
    document.getElementById("vd_brand").value = vehicle.brand || "";
    document.getElementById("vd_model").value = vehicle.model || "";
    document.getElementById("vd_year").value = vehicle.year || "";
    document.getElementById("vd_vin").value = vehicle.vin || "";
    document.getElementById("vd_engine").value = vehicle.engine || "";
    document.getElementById("vd_transmission").value = vehicle.transmission || "";
    document.getElementById("vd_fuel_type").value = vehicle.fuel_type || "";
    document.getElementById("vd_mileage").value = vehicle.mileage || "";
    document.getElementById("vd_plate_number").value = vehicle.plate_number || "";
    document.getElementById("vd_license_expiry_date").value = vehicle.license_expiry_date || "";
    document.getElementById("vd_color").value = vehicle.color || "";

    const gold = asset.gold_details || {};
    await populateGoldSettingsDropdowns(gold.gold_type || "", gold.purity || "");
    document.getElementById("gd_weight").value = gold.weight || "";
    document.getElementById("gd_unit").value = gold.unit || "gram";
    document.getElementById("gd_market_price").value = gold.market_price || "";
    document.getElementById("gd_cashback_per_gram").value = gold.cashback_per_gram || 0;
    document.getElementById("gd_purchase_weight").value = gold.purchase_weight || "";

    const other = asset.other_asset_details || {};
    document.getElementById("od_category").value = other.category || "";
    document.getElementById("od_manufacturer").value = other.manufacturer || "";
    document.getElementById("od_model").value = other.model || "";
    document.getElementById("od_serial_number").value = other.serial_number || "";
    document.getElementById("od_warranty_expiry").value = other.warranty_expiry || "";
    document.getElementById("od_description").value = other.description || "";
    document.getElementById("od_notes").value = other.notes || "";

    updateGoldValuation();

    if (asset.real_estate) {
      const re = asset.real_estate;
      populatePropertyValuationFields(re);
      document.getElementById("re_country").value = re.country || "";
      document.getElementById("re_governorate").value = re.governorate || "";
      document.getElementById("re_city").value = re.city || "";
      document.getElementById("re_district").value = re.district || "";
      document.getElementById("re_address").value = re.address || "";
      document.getElementById("re_latitude").value = re.latitude || "";
      document.getElementById("re_longitude").value = re.longitude || "";
      document.getElementById("re_area").value = re.apartment_area || 0;
      document.getElementById("re_land_area").value = re.land_area || 0;
      document.getElementById("re_rooms").value = re.rooms || 0;
      document.getElementById("re_bathrooms").value = re.bathrooms || 0;
      document.getElementById("re_floor").value = re.floor || 0;
      document.getElementById("re_b_floors").value = re.building_floors || 0;
      document.getElementById("re_year").value = re.building_year || 0;
      document.getElementById("re_facades").value = re.facades || "";
      document.getElementById("re_furnished").value =
        re.furnished_status || "Unfurnished";
      document.getElementById("re_finishing").value = re.finishing_level || "";
      document.getElementById("re_util_elec").checked = Boolean(re.electricity);
      document.getElementById("re_util_water").checked = Boolean(re.water);
      document.getElementById("re_util_gas").checked = Boolean(re.gas);
      document.getElementById("re_feat_elevator").checked = Boolean(
        re.elevator,
      );
      document.getElementById("re_feat_garage").checked = Boolean(re.garage);
      document.getElementById("re_feat_licensed").checked = Boolean(
        re.licensed,
      );
      document.getElementById("re_has_land_share").checked = Boolean(
        re.has_land_share,
      );
      document.getElementById("re_land_share").value = re.land_share || "";
      document.getElementById("re_description").value = re.description || "";
      const lat = parseFloat(re.latitude);
      const lng = parseFloat(re.longitude);

      if (!isNaN(lat) && !isNaN(lng)) {
        document.getElementById("re_latitude").value = lat;
        document.getElementById("re_longitude").value = lng;

        initializePropertyMap(lat, lng);
      }
    } else {
      populatePropertyValuationFields({});
    }

    // ---------- Renovations ----------
    const renovationContainer = document.getElementById("renovationContainer");

    if (renovationContainer) {
      renovationContainer.innerHTML = "";

      if (asset.renovations && asset.renovations.length) {
        asset.renovations.forEach((r) => {
          addRenovationRow({
            date: r.date,
            category: r.category,
            description: r.description,
            amount_egp: r.amount_egp,
            usd_rate: r.usd_rate,
            amount_usd: r.amount_usd,
            notes: r.notes,
          });
        });
      }
    }

    const furnitureContainer = document.getElementById("furnitureContainer");
    if (furnitureContainer) {
      furnitureContainer.innerHTML = "";
      (asset.furniture || []).forEach((item) => addFurnitureRow(item));
    }

    const valuationContainer = document.getElementById("valuationContainer");
    if (valuationContainer) {
      valuationContainer.innerHTML = "";
      (asset.valuation_history || []).forEach((item) => addValuationRow(item));
    }

    const maintenanceContainer = document.getElementById("maintenanceContainer");
    if (maintenanceContainer) {
      maintenanceContainer.innerHTML = "";
      (asset.maintenance || []).forEach((item) => addMaintenanceRow(item));
    }

    const insuranceContainer = document.getElementById("insuranceContainer");
    if (insuranceContainer) {
      insuranceContainer.innerHTML = "";
      (asset.insurance || []).forEach((item) => addInsuranceRow(item));
    }
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

