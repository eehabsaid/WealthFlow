"use strict";
// Gold price cache, purity helpers, and settings dropdowns
// This file is part of the fixed_assets module. Do not edit directly.

function getGoldUnitFactor(unitValue) {
  const normalized = String(unitValue || "gram")
    .trim()
    .toLowerCase();
  const map = {
    g: 1,
    gm: 1,
    gram: 1,
    grams: 1,
    kg: 1000,
    kilogram: 1000,
    kilograms: 1000,
    oz: 31.1034768,
    ounce: 31.1034768,
    ounces: 31.1034768,
    tola: 11.6638038,
  };
  return map[normalized] || 1;
}

function normalizeGoldPurity(purityValue) {
  const text = String(purityValue || "")
    .trim()
    .toLowerCase();
  if (text.includes("24") || text.includes("999")) return "24k";
  if (text.includes("22") || text.includes("916")) return "22k";
  if (text.includes("21") || text.includes("875")) return "21k";
  if (text.includes("18") || text.includes("750")) return "18k";
  return "24k";
}

function buildDashboardAnalyticsAssets(assets) {
  const source = normalizeFixedAssetsData(assets);
  const groupedGoldMap = {};
  const nonGoldAssets = [];

  source.forEach((asset) => {
    const assetType = asset.asset_type || asset.type;
    if (!isGoldAssetType(assetType)) {
      nonGoldAssets.push(asset);
      return;
    }

    const purityKey = normalizeGoldPurity(asset?.gold_details?.purity || asset?.purity || "24k");
    if (!groupedGoldMap[purityKey]) {
      groupedGoldMap[purityKey] = {
        ...asset,
        id: `gold-group-${purityKey}`,
        name: `${t("type_gold", "Gold")} ${purityKey.toUpperCase()}`,
        asset_type: FIXED_ASSET_TYPES.GOLD,
        purchase_price: 0,
        current_market_value: 0,
        purchase_date: asset.purchase_date || null,
        renovations: [],

        // Aggregated Gold Analytics must recalculate these values
        // from the aggregated purchase/current values.
        total_acquisition_costs: 0,
        total_renovation_costs: 0,
      };

      delete groupedGoldMap[purityKey].total_investment;
      delete groupedGoldMap[purityKey].gain_loss;
      delete groupedGoldMap[purityKey].roi;
      delete groupedGoldMap[purityKey].appreciation;
      delete groupedGoldMap[purityKey].annual_return;
    }

    groupedGoldMap[purityKey].purchase_price += parseFloat(asset.purchase_price) || 0;
    groupedGoldMap[purityKey].current_market_value += parseFloat(asset.current_market_value) || 0;

    if (asset.purchase_date) {
      const currentDate = new Date(
        groupedGoldMap[purityKey].purchase_date || asset.purchase_date
      ).getTime();
      const candidateDate = new Date(asset.purchase_date).getTime();
      if (
        !Number.isNaN(candidateDate) &&
        (Number.isNaN(currentDate) || candidateDate < currentDate)
      ) {
        groupedGoldMap[purityKey].purchase_date = asset.purchase_date;
      }
    }
  });

  const groupedGoldAssets = Object.values(groupedGoldMap);
  return [...nonGoldAssets, ...groupedGoldAssets];
}

function getGoldSellPerGram(goldPayload, purityKey) {
  if (!goldPayload) return 0;
  const map = {
    "24k": parseFloat(goldPayload.carat_24k) || 0,
    "22k": parseFloat(goldPayload.carat_22k) || 0,
    "21k": parseFloat(goldPayload.carat_21k) || 0,
    "18k": parseFloat(goldPayload.carat_18k) || 0,
  };
  return map[purityKey] || map["24k"] || 0;
}

async function getLatestGoldPrice(force = false) {
  const now = Date.now();
  if (!force && latestGoldPriceCache && now - latestGoldPriceFetchedAt < 30000) {
    return latestGoldPriceCache;
  }

  const response = await fetch("/api/gold/");
  if (!response.ok) {
    throw new Error(t("error_loading_gold_prices", "Failed to load gold prices."));
  }

  const data = await response.json();
  latestGoldPriceCache = data?.gold || null;
  latestGoldPriceFetchedAt = now;
  return latestGoldPriceCache;
}

async function getGoldTypeSettings(force = false) {
  const now = Date.now();
  if (!force && goldTypeSettingsCache && now - goldTypeSettingsFetchedAt < 30000) {
    return goldTypeSettingsCache;
  }

  const response = await fetch("/api/settings/gold-types/");
  if (!response.ok) {
    throw new Error(t("error_loading_gold_types", "Failed to load gold types."));
  }

  const data = await response.json();
  goldTypeSettingsCache = data?.items || [];
  goldTypeSettingsFetchedAt = now;
  return goldTypeSettingsCache;
}

async function getGoldPuritySettings(force = false) {
  const now = Date.now();
  if (!force && goldPuritySettingsCache && now - goldPuritySettingsFetchedAt < 30000) {
    return goldPuritySettingsCache;
  }

  const response = await fetch("/api/settings/gold-purities/");
  if (!response.ok) {
    throw new Error(t("error_loading_gold_purities", "Failed to load gold purities."));
  }

  const data = await response.json();
  goldPuritySettingsCache = data?.items || [];
  goldPuritySettingsFetchedAt = now;
  return goldPuritySettingsCache;
}

async function populateGoldSettingsDropdowns(selectedGoldType = "", selectedPurity = "") {
  const goldTypeSelect = document.getElementById("gd_gold_type");
  const puritySelect = document.getElementById("gd_purity");
  if (!goldTypeSelect || !puritySelect) return;

  const fallbackType = String(selectedGoldType || "").trim();
  const fallbackPurity = String(selectedPurity || "").trim();

  try {
    const [goldTypes, goldPurities] = await Promise.all([
      getGoldTypeSettings(),
      getGoldPuritySettings(),
    ]);

    const activeGoldTypes = (goldTypes || []).filter((item) => item && item.is_active);
    const activePurities = (goldPurities || []).filter((item) => item && item.is_active);

    goldTypeSelect.innerHTML = activeGoldTypes
      .map((item) => `<option value="${item.name}">${item.name}</option>`)
      .join("");

    puritySelect.innerHTML = activePurities
      .map((item) => `<option value="${item.key}">${item.label || item.key}</option>`)
      .join("");

    if (fallbackType) {
      const hasType = activeGoldTypes.some((item) => String(item.name) === fallbackType);
      if (!hasType) {
        goldTypeSelect.insertAdjacentHTML(
          "beforeend",
          `<option value="${fallbackType}">${fallbackType}</option>`
        );
      }
      goldTypeSelect.value = fallbackType;
    } else if (goldTypeSelect.options.length) {
      goldTypeSelect.selectedIndex = 0;
    }

    if (fallbackPurity) {
      const normalizedFallbackPurity = normalizeGoldPurity(fallbackPurity);
      const hasPurity = activePurities.some(
        (item) => String(item.key || "").toLowerCase() === normalizedFallbackPurity
      );
      if (!hasPurity) {
        puritySelect.insertAdjacentHTML(
          "beforeend",
          `<option value="${normalizedFallbackPurity}">${fallbackPurity}</option>`
        );
      }
      puritySelect.value = hasPurity ? normalizedFallbackPurity : normalizedFallbackPurity;
    } else if (puritySelect.options.length) {
      puritySelect.selectedIndex = 0;
    }
  } catch (error) {
    showToast(error.message, "danger");

    if (!goldTypeSelect.options.length) {
      goldTypeSelect.innerHTML = `<option value="">${t("none_option", "--")}</option>`;
    }
    if (!puritySelect.options.length) {
      puritySelect.innerHTML = `<option value="24k">24K</option>`;
    }

    if (fallbackType) {
      goldTypeSelect.value = fallbackType;
    }
    if (fallbackPurity) {
      puritySelect.value = normalizeGoldPurity(fallbackPurity);
    }
  }
}
