"use strict";
// Post-save financial view refresh + asset deletion.
// Part of the fixed_assets module (split from the former monolithic
// validation.js, 200-line rule). Do not edit directly.

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

