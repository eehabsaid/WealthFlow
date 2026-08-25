"use strict";
// Global state, constants, and asset-type helpers
// This file is part of the fixed_assets module. Do not edit directly.

"use strict";

let propertyMap = null;
let propertyMarker = null;
let propertyPhotos = [];
let currentEditingAssetId = null;
let currentAssetHasPurchaseSync = false;
let fixedAssetSyncCurrencies = [];
let fixedAssetSyncBanks = [];
let fixedAssetBanksWithBalance = [];
let currentAssetFurnitureOptions = [];
const FIXED_ASSET_PAYMENT_METHODS = ["Cash", "Card", "Bank", "Bank Transfer"];
let goldPurityReturnContext = null;
let fixedAssetsState = {
  activeTab: "assets",
  assets: [],
  isLoading: false,
  portfolioSnapshot: null,
  portfolioSnapshotLoading: false,
};

let latestGoldPriceCache = null;
let latestGoldPriceFetchedAt = 0;
let goldTypeSettingsCache = null;
let goldTypeSettingsFetchedAt = 0;
let goldPuritySettingsCache = null;
let goldPuritySettingsFetchedAt = 0;

const FIXED_ASSET_TYPES = {
  REAL_ESTATE: "Real Estate",
  VEHICLES: "Vehicles",
  GOLD: "Gold",
  OTHER: "Other Assets",
};

function fixedAssetTypeToI18nKey(value) {
  return `type_${String(value || "other")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")}`;
}

function isRealEstateAssetType(value) {
  return value === FIXED_ASSET_TYPES.REAL_ESTATE;
}

function isVehicleAssetType(value) {
  return value === FIXED_ASSET_TYPES.VEHICLES;
}

function isGoldAssetType(value) {
  return value === FIXED_ASSET_TYPES.GOLD;
}

function isOtherAssetType(value) {
  return value === FIXED_ASSET_TYPES.OTHER;
}

