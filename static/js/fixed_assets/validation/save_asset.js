"use strict";
// Create/update fixed asset form submission handler (orchestrator).
// Payload building, submission, and photo upload split into
// validation/save_asset/build_payload.js, submit.js, and photos.js
// (200-line rule). Part of the fixed_assets module. Do not edit directly.

async function saveFixedAsset(assetId = null) {
  const isEdit = assetId !== null;
  const url = isEdit ? `/api/fixed-assets/${assetId}/` : "/api/fixed-assets/";
  const method = isEdit ? "PUT" : "POST";

  // NOTE: buildFixedAssetPayload() runs outside the try block below,
  // matching the original saveFixedAsset. If its bank-account validation
  // loop throws, that error is NOT caught here — it propagates uncaught,
  // exactly as in the original monolithic function.
  const payload = buildFixedAssetPayload();
  if (payload === null) return;

  showLoading();
  try {
    const savedAsset = await submitFixedAssetPayload(url, method, payload);

    // Only touch the sale endpoint when there's actually something to do:
    // status is "Sold" (create/update the sale record), or a sale record
    // already exists and needs to be removed because status moved away
    // from "Sold". Skips a redundant DELETE call on every ordinary save.
    if (payload.status === "Sold" || savedAsset.sale) {
      await syncAssetSale(savedAsset.id, payload.status);
    }

    await uploadPendingFixedAssetPhotos(savedAsset.id);

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
