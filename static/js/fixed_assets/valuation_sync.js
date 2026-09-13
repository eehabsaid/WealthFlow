"use strict";
// Valuation sync + collection helpers
// This file is part of the fixed_assets module. Do not edit directly.

function updateValuationSyncButtonVisibility(row) {
  const syncBtn = row.querySelector(".valuation-sync-btn");
  if (!syncBtn) return;

  const sourceSelect = row.querySelector(".valuation-source");
  const isAutomatic = sourceSelect && sourceSelect.value === "Automatic";
  const typeField = document.getElementById("fa_type");
  const isSupportedAssetType =
    typeof isRealEstateAssetType === "function" && typeField
      ? isRealEstateAssetType(typeField.value)
      : true;
  const isSavedAsset = !!currentEditingAssetId;

  syncBtn.style.display = isAutomatic && isSupportedAssetType && isSavedAsset ? "" : "none";
}

async function syncValuationRow(buttonEl) {
  const row = buttonEl.closest(".valuation-row");
  if (!row || !currentEditingAssetId) return;

  buttonEl.disabled = true;
  const originalHTML = buttonEl.innerHTML;
  buttonEl.innerHTML = `<span>${t("syncing", "Syncing...")}</span>`;

  try {
    const response = await fetch(`/api/fixed-assets/${currentEditingAssetId}/valuation/refresh/`, {
      method: "POST",
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(
        payload.error ||
          t("error_refreshing_property_valuation", "Failed to refresh property valuation.")
      );
    }

    if (!payload.updated) {
      showToast(
        t(
          "property_valuation_unavailable",
          "No automatic valuation was available for this property."
        ),
        "warning"
      );
      return;
    }

    const asset = payload.asset || {};
    const latestEntry = (asset.valuation_history || [])[0];

    if (latestEntry) {
      row.querySelector(".valuation-date").value = latestEntry.valuation_date || "";
      row.querySelector(".valuation-market-value").value = latestEntry.market_value || 0;
      row.querySelector(".valuation-notes").value = latestEntry.notes || "";

      const fmt = (n) =>
        Number(n || 0).toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
      row.querySelector(".item-amount-preview").textContent =
        `EGP ${fmt(parseFloat(latestEntry.market_value) || 0)}`;
      row.querySelector(".item-name-preview").textContent =
        latestEntry.valuation_date || t("unnamed_item", "(Unnamed item)");
    }

    // Keep the General tab's current-value fields consistent with the sync too.
    const currentValueField = document.getElementById("fa_current_value");
    const lastValuationDateField = document.getElementById("fa_last_valuation_date");
    if (currentValueField) currentValueField.value = asset.current_market_value || 0;
    if (lastValuationDateField) lastValuationDateField.value = asset.last_valuation_date || "";

    updateValuationSummary();
    showToast(t("property_valuation_refreshed", "Property valuation refreshed."), "success");
  } catch (error) {
    showToast(
      error.message ||
        t("error_refreshing_property_valuation", "Failed to refresh property valuation."),
      "error"
    );
  } finally {
    buttonEl.disabled = false;
    buttonEl.innerHTML = originalHTML;
  }
}

function collectValuationHistory() {
  const valuationHistory = [];
  document.querySelectorAll(".valuation-row").forEach((row) => {
    const valuationDate = row.querySelector(".valuation-date").value;
    if (!valuationDate) return;
    valuationHistory.push({
      valuation_date: valuationDate,
      market_value: parseFloat(row.querySelector(".valuation-market-value").value) || 0,
      valuation_source: row.querySelector(".valuation-source").value,
      notes: row.querySelector(".valuation-notes").value,
    });
  });
  return valuationHistory;
}
