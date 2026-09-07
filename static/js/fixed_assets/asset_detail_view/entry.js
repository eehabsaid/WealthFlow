"use strict";
// showFixedAssetDetails — read-only asset detail modal
// This file is part of the fixed_assets module. Do not edit directly.
//
// Split from the former monolithic asset_detail_view.js (200-line rule)
// using the phase-function + context-object pattern (this was previously
// one 959-line function). Sibling files under asset_detail_view/:
// - non_real_estate_core_tab.js              Vehicle/gold/other core tab HTML
// - non_real_estate_modal.js                 Builds + shows the simple modal
// - general_property_tabs.js                 Real-estate general/property tabs
// - photos_renovation_acquisition_tabs.js    Real-estate photos/reno/acq tabs
// - furniture_valuation_mortgage_rental_sale_tabs.js  Remaining real-estate tabs
// - modal_shell.js                           Assembles the full real-estate modal
//
// All builder functions take a single `ctx` object carrying the asset data
// computed once below, and return HTML strings — zero logic changes from
// the original inline code.

async function showFixedAssetDetails(assetId, options = {}) {
  if (options?.returnPurityKey) {
    setGoldPurityReturnContext(options.returnPurityKey);
  } else {
    clearGoldPurityReturnContext();
  }

  showLoading();

  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/`);

    if (!response.ok) throw new Error("Failed to load asset");

    const asset = await response.json();

    const photos = asset.photos || [];
    const renovations = asset.renovations || [];
    const furniture = asset.furniture || [];
    const valuationHistory = asset.valuation_history || [];
    const maintenance = asset.maintenance || [];
    const insurance = asset.insurance || [];
    const vehicleDetails = asset.vehicle_details || {};
    const goldDetails = asset.gold_details || {};
    const otherDetails = asset.other_asset_details || {};
    const sale = asset.sale || null;
    const mortgage = asset.mortgage || null;
    const rental = asset.rental || null;
    const realEstate = asset.real_estate || {};
    const utilitiesBadges = [
      realEstate.electricity
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-plug-fill me-1"></i><span data-i18n="electricity">Electricity</span></span>'
        : "",
      realEstate.water
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-droplet-fill me-1"></i><span data-i18n="water">Water</span></span>'
        : "",
      realEstate.gas
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-fire me-1"></i><span data-i18n="gas">Gas</span></span>'
        : "",
    ]
      .filter(Boolean)
      .join("");
    const featuresBadges = [
      realEstate.elevator
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-building me-1"></i><span data-i18n="elevator">Elevator</span></span>'
        : "",
      realEstate.garage
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-car-front-fill me-1"></i><span data-i18n="garage">Garage</span></span>'
        : "",
      realEstate.has_land_share
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-tree-fill me-1"></i><span data-i18n="has_land_share">Land Share</span></span>'
        : "",
      realEstate.licensed
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-shield-lock-fill me-1"></i><span data-i18n="licensed">Licensed</span></span>'
        : "",
    ]
      .filter(Boolean)
      .join("");
    const gainValue =
      asset.gain_loss !== undefined
        ? asset.gain_loss
        : (asset.current_market_value || 0) - (asset.purchase_price || 0);
    const gainClass = gainValue >= 0 ? "text-success" : "text-danger";
    let assetViewMap = null;

    const ctx = {
      asset, photos, renovations, furniture, valuationHistory, maintenance,
      insurance, vehicleDetails, goldDetails, otherDetails, sale, mortgage,
      rental, realEstate, utilitiesBadges, featuresBadges, gainValue, gainClass,
    };

    if (!isRealEstateAssetType(asset.asset_type)) {
      buildAndShowNonRealEstateModal(ctx);
      return;
    }

    const html = buildRealEstateModalHtml(ctx);

    showModal(html);

    applyTranslations();

    const mainPhoto = document.getElementById("assetMainPhoto");
    const photoOverlay = document.getElementById("assetPhotoOverlay");
    const fullscreenImage = document.getElementById("assetFullscreenImage");

    if (mainPhoto) {
      mainPhoto.addEventListener("click", () => {
        fullscreenImage.src = mainPhoto.src;
        photoOverlay.classList.remove("d-none");
      });
    }

    photoOverlay?.addEventListener("click", () => {
      photoOverlay.classList.add("d-none");
      fullscreenImage.src = "";
    });

    const assetPhotoThumbnails = document.querySelectorAll(".asset-photo-thumbnail");
    assetPhotoThumbnails.forEach((thumb, index) => {
      thumb.addEventListener("click", (e) => {
        const url = e.currentTarget.dataset.url;
        const mainImg = document.getElementById("assetMainPhoto");
        if (mainImg) mainImg.src = url;
        assetPhotoThumbnails.forEach((item) => item.classList.remove("active"));
        e.currentTarget.classList.add("active");
      });
    });

    const propertyLatitude = parseFloat(asset.real_estate?.latitude);
    const propertyLongitude = parseFloat(asset.real_estate?.longitude);

    if (!Number.isNaN(propertyLatitude) && !Number.isNaN(propertyLongitude)) {
      assetViewMap = L.map("assetPropertyMap", {
        dragging: false,
        touchZoom: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        zoomControl: false,
        tap: false,
      }).setView([propertyLatitude, propertyLongitude], 14);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(assetViewMap);

      L.marker([propertyLatitude, propertyLongitude], { interactive: false }).addTo(assetViewMap);
      setTimeout(() => assetViewMap.invalidateSize(), 200);
    }

    const assetPropertyTab = document.getElementById("asset-property-tab");
    if (assetPropertyTab && assetViewMap) {
      assetPropertyTab.addEventListener("shown.bs.tab", () => {
        setTimeout(() => assetViewMap.invalidateSize(), 50);
      });
    }

    document.querySelectorAll("#assetDetailsTabsContent .card").forEach((card) => {
      card.style.background = "var(--bg-secondary)";
      card.style.color = "var(--text-primary)";
    });

    document.querySelectorAll("#assetDetailsTabsContent").forEach((el) => {
      el.style.color = "var(--text-secondary)";
    });
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}
