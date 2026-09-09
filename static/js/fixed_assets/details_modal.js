"use strict";
// showFixedAssetModal — orchestrator. Split into sibling files (200-line
// backlog): details_modal_nav1.js, details_modal_nav2.js,
// details_modal_html.js, details_modal_events.js. This file wires them
// together in the same order as the original inline implementation.
// ════════════════════════════════════════════════════════════════════════════

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
  const modalTitleDefault = isEdit ? "Edit Asset Details" : "Register New Fixed Asset";

  const html = buildFixedAssetModalHtml(assetId, modalTitleKey, modalTitleDefault);

  showModal(html);
  applyTranslations();
  await populateGoldSettingsDropdowns();

  const propertyTab = wireFixedAssetModalFieldListeners();

  await resetFixedAssetModalFormState(assetId);

  await wireFixedAssetPropertyMapAndLoad(propertyTab, assetId, isEdit);
}
