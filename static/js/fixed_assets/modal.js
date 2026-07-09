"use strict";
// Gold purity context and asset window helpers
// This file is part of the fixed_assets module. Do not edit directly.

function setGoldPurityReturnContext(purityKey) {
  if (!purityKey) {
    goldPurityReturnContext = null;
    return;
  }
  goldPurityReturnContext = normalizeGoldPurity(purityKey);
}

function clearGoldPurityReturnContext() {
  goldPurityReturnContext = null;
}

function handleAssetWindowClose() {
  const returnPurity = goldPurityReturnContext;
  closeModal();
  if (returnPurity) {
    setTimeout(() => {
      showGoldPurityGroupDetails(returnPurity);
    }, 160);
  }
}

function openGoldPurchaseDetails(assetId, purityKey) {
  setGoldPurityReturnContext(purityKey);
  showFixedAssetDetails(assetId, { returnPurityKey: purityKey });
}

function openGoldPurchaseEditor(assetId, purityKey) {
  setGoldPurityReturnContext(purityKey);
  showFixedAssetModal(assetId, { returnPurityKey: purityKey });
}

async function deleteFixedAssetFromGoldGroup(assetId, purityKey) {
  setGoldPurityReturnContext(purityKey);
  const deleted = await deleteFixedAsset(assetId);
  if (deleted) {
    setTimeout(() => {
      showGoldPurityGroupDetails(purityKey);
    }, 200);
  }
}

