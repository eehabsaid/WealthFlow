"use strict";
// Fixed assets API fetch and data normalization
// This file is part of the fixed_assets module. Do not edit directly.

// ════════════════════════════════════════════════════════════════════════════
// DATA FETCHING & ROUTING
// ════════════════════════════════════════════════════════════════════════════

async function fetchAndRenderFixedAssets() {
  fixedAssetsState.isLoading = true;
  renderActiveFixedAssetsTab();
  showLoading();
  try {
    const response = await fetch("/api/fixed-assets/");
    if (!response.ok) throw new Error("Failed to load fixed assets");
    const data = await response.json();
    fixedAssetsState.assets = normalizeFixedAssetsData(data);
    fixedAssetsState.portfolioSnapshot = data?.portfolio_snapshot || null;
    fixedAssetsState.isLoading = false;
    renderActiveFixedAssetsTab();
  } catch (err) {
    fixedAssetsState.isLoading = false;
    renderActiveFixedAssetsTab();
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

function normalizeFixedAssetsData(assets) {
  if (Array.isArray(assets)) {
    return assets;
  }

  if (assets && typeof assets === "object") {
    if (Array.isArray(assets.data)) return assets.data;
    if (Array.isArray(assets.results)) return assets.results;
    if (Array.isArray(assets.assets)) return assets.assets;
    if (Array.isArray(assets.fixed_assets)) return assets.fixed_assets;
  }

  return [];
}

