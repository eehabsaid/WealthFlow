"use strict";
// Gold price/type/purity fetchers (cached) and settings dropdown population.
// Part of the fixed_assets module (split from the former monolithic gold.js,
// 200-line rule). Do not edit directly.

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
