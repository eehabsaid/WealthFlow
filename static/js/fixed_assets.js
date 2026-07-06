"use strict";

let propertyMap = null;
let propertyMarker = null;
let propertyPhotos = [];
let currentEditingAssetId = null;
let currentAssetHasPurchaseSync = false;
let fixedAssetSyncCurrencies = [];
let fixedAssetSyncBanks = [];
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

function getGoldUnitFactor(unitValue) {
  const normalized = String(unitValue || "gram").trim().toLowerCase();
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
  const text = String(purityValue || "").trim().toLowerCase();
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
      };
    }

    groupedGoldMap[purityKey].purchase_price += parseFloat(asset.purchase_price) || 0;
    groupedGoldMap[purityKey].current_market_value += parseFloat(asset.current_market_value) || 0;

    if (asset.purchase_date) {
      const currentDate = new Date(groupedGoldMap[purityKey].purchase_date || asset.purchase_date).getTime();
      const candidateDate = new Date(asset.purchase_date).getTime();
      if (!Number.isNaN(candidateDate) && (Number.isNaN(currentDate) || candidateDate < currentDate)) {
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
        goldTypeSelect.insertAdjacentHTML("beforeend", `<option value="${fallbackType}">${fallbackType}</option>`);
      }
      goldTypeSelect.value = fallbackType;
    } else if (goldTypeSelect.options.length) {
      goldTypeSelect.selectedIndex = 0;
    }

    if (fallbackPurity) {
      const normalizedFallbackPurity = normalizeGoldPurity(fallbackPurity);
      const hasPurity = activePurities.some((item) => String(item.key || "").toLowerCase() === normalizedFallbackPurity);
      if (!hasPurity) {
        puritySelect.insertAdjacentHTML("beforeend", `<option value="${normalizedFallbackPurity}">${fallbackPurity}</option>`);
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

function renderFixedAssets(activeTab = "assets") {
  fixedAssetsState.activeTab = activeTab;
  const target = document.getElementById("main-content");
  if (!target) return;

  target.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3 pb-2" style="border-bottom: 1px solid var(--border-color); gap: 1rem;">
            <h3 class="m-0 font-weight-bold fixed-assets-heading" data-i18n="fixed_assets">Fixed Assets</h3>
            <div id="fixedAssetsHeaderAction"></div>
        </div>
        <div class="settings-tabs-container" style="border-bottom:1px solid var(--border-color);margin-bottom:20px;display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap;">
            <button class="settings-tab ${fixedAssetsState.activeTab === "assets" ? "active" : ""}" onclick="switchFixedAssetsTab('assets')">
                <span class="fixed-assets-tab-title" data-i18n="fixed_assets_tab_assets">Assets</span>
            </button>
            <button class="settings-tab ${fixedAssetsState.activeTab === "dashboard" ? "active" : ""}" onclick="switchFixedAssetsTab('dashboard')">
                <span class="fixed-assets-tab-title" data-i18n="dashboard">Dashboard</span>
            </button>
            <button class="settings-tab ${fixedAssetsState.activeTab === "analytics" ? "active" : ""}" onclick="switchFixedAssetsTab('analytics')">
                <span class="fixed-assets-tab-title" data-i18n="fixed_assets_tab_analytics">Analytics</span>
            </button>
            <button class="settings-tab ${fixedAssetsState.activeTab === "reports" ? "active" : ""}" onclick="switchFixedAssetsTab('reports')">
                <span class="fixed-assets-tab-title" data-i18n="nav_reports">Reports</span>
            </button>
        </div>
        <div id="fixedAssetsContainer"></div>
    `;

  renderFixedAssetsHeaderAction();
  renderActiveFixedAssetsTab();
  applyTranslations();

  setTimeout(() => {
    fetchAndRenderFixedAssets();
  }, 0);
}

function switchFixedAssetsTab(tab) {
  fixedAssetsState.activeTab = tab;
  renderFixedAssetsHeaderAction();
  updateFixedAssetsTabButtons();
  renderActiveFixedAssetsTab();
  applyTranslations();
}

function updateFixedAssetsTabButtons() {
  document.querySelectorAll(".settings-tabs-container .settings-tab").forEach((button) => {
    button.classList.toggle(
      "active",
      button.getAttribute("onclick") === `switchFixedAssetsTab('${fixedAssetsState.activeTab}')`,
    );
  });
}

function renderFixedAssetsHeaderAction() {
  const actionContainer = document.getElementById("fixedAssetsHeaderAction");
  if (!actionContainer) return;

  if (fixedAssetsState.activeTab === "assets") {
    actionContainer.innerHTML = `
      <button class="btn-primary-custom" onclick="showFixedAssetModal()">
          <i class="bi bi-plus-lg"></i> <span data-i18n="add_new_asset">Add Asset</span>
      </button>
    `;
  } else {
    actionContainer.innerHTML = "";
  }
}

function renderActiveFixedAssetsTab() {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  if (fixedAssetsState.isLoading) {
    container.innerHTML = `
      <div style="display:flex;justify-content:center;padding:60px;">
        <div class="spinner-border" style="color:var(--accent-primary)"></div>
      </div>
    `;
    return;
  }

  if (fixedAssetsState.activeTab === "assets") {
    renderFixedAssetsList(fixedAssetsState.assets);
    return;
  }

  if (fixedAssetsState.activeTab === "dashboard") {
    renderFixedAssetsDashboard(fixedAssetsState.assets);
    return;
  }

  if (fixedAssetsState.activeTab === "analytics") {
    renderFixedAssetsAnalytics(fixedAssetsState.assets);
    return;
  }

  renderFixedAssetsReports(fixedAssetsState.assets);
}

// ════════════════════════════════════════════════════════════════════════════
// LIST RENDERING (CARD VIEW)
// ════════════════════════════════════════════════════════════════════════════

function renderFixedAssetsList(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = normalizeFixedAssetsData(assets);
  const goldAssets = assetsArray.filter((asset) => isGoldAssetType(asset.asset_type || asset.type));
  const nonGoldAssets = assetsArray.filter((asset) => !isGoldAssetType(asset.asset_type || asset.type));

  if (!assetsArray || assetsArray.length === 0) {
    container.innerHTML = `
            <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
                <div class="display-5 mb-3">🏢</div>
                <h4 class="mt-2 fixed-assets-empty-title" data-i18n="no_fixed_assets">No Fixed Assets Registered</h4>
                <p class="small mb-4 fixed-assets-muted" data-i18n="no_fixed_assets_desc">You haven't added any fixed assets or properties to your tracker portfolio yet.</p>
                <button class="btn btn-sm btn-primary-custom" onclick="showFixedAssetModal()">
                    <i class="bi bi-plus-lg"></i> <span data-i18n="add_first_asset">Register Your First Asset</span>
                </button>
            </div>
        `;
    if (typeof applyTranslations === "function") applyTranslations();
    return;
  }

  const groupedGoldMap = {};
  goldAssets.forEach((asset) => {
    const purityKey = normalizeGoldPurity(asset?.gold_details?.purity || asset?.purity || "24k");
    const weight = parseFloat(asset?.gold_details?.weight) || 0;
    const unit = asset?.gold_details?.unit || "gram";
    const weightInGrams = weight * getGoldUnitFactor(unit);

    if (!groupedGoldMap[purityKey]) {
      groupedGoldMap[purityKey] = {
        purity_key: purityKey,
        purity_label: purityKey.toUpperCase(),
        total_weight_grams: 0,
        total_purchase_value: 0,
        total_current_market_value: 0,
        purchases_count: 0,
      };
    }

    groupedGoldMap[purityKey].total_weight_grams += weightInGrams;
    groupedGoldMap[purityKey].total_purchase_value += parseFloat(asset.purchase_price) || 0;
    groupedGoldMap[purityKey].total_current_market_value += parseFloat(asset.current_market_value) || 0;
    groupedGoldMap[purityKey].purchases_count += 1;
  });

  const groupedGoldRows = Object.values(groupedGoldMap).sort((a, b) => {
    const rank = { "24k": 1, "22k": 2, "21k": 3, "18k": 4 };
    return (rank[a.purity_key] || 99) - (rank[b.purity_key] || 99);
  });

  let html = `
    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden;">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th data-i18n="asset_name">Asset Name</th>
              <th data-i18n="asset_type">Asset Type</th>
              <th data-i18n="purity">Purity</th>
              <th class="text-end" data-i18n="total_weight">Total Weight</th>
              <th class="text-end" data-i18n="total_purchase_value">Total Purchase Value</th>
              <th class="text-end" data-i18n="current_market_value">Current Market Value</th>
              <th class="text-end" data-i18n="number_of_purchases">Number of Purchases</th>
              <th data-i18n="actions">Actions</th>
            </tr>
          </thead>
          <tbody>
  `;

  groupedGoldRows.forEach((grouped) => {
    html += `
            <tr>
              <td class="fixed-assets-card-title">${t("type_gold", "Gold")}</td>
              <td>
                <span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;" data-i18n="type_gold">${t("type_gold", "Gold")}</span>
              </td>
              <td>${grouped.purity_label}</td>
              <td class="text-end">${fmt(grouped.total_weight_grams)}</td>
              <td class="text-end">${fmt(grouped.total_purchase_value)}</td>
              <td class="text-end">
                <span style="color:#17a34a;font-weight:700">${fmt(grouped.total_current_market_value)}</span>
              </td>
              <td class="text-end">${fmtInt(grouped.purchases_count)}</td>
              <td class="d-flex gap-2">
                <button class="btn-icon" title="${t("view", "View")}" onclick="showGoldPurityGroupDetails('${grouped.purity_key}')"><i class="bi bi-eye"></i></button>
              </td>
            </tr>
    `;
  });

  nonGoldAssets.forEach((asset) => {
    const assetType = asset.asset_type || asset.type || FIXED_ASSET_TYPES.OTHER;
    const typeKey = fixedAssetTypeToI18nKey(assetType);

    html += `
            <tr>
              <td class="fixed-assets-card-title">${asset.name || "—"}</td>
              <td>
                <span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;" data-i18n="${typeKey}">${assetType}</span>
              </td>
              <td>—</td>
              <td class="text-end">—</td>
              <td class="text-end">${fmt(asset.purchase_price)}</td>
              <td class="text-end">
                <span style="color:#17a34a;font-weight:700">${fmt(asset.current_market_value)}</span>
              </td>
              <td class="text-end">1</td>
              <td class="d-flex gap-2">
                <button class="btn-icon" title="View" onclick="showFixedAssetDetails(${asset.id})"><i class="bi bi-eye"></i></button>
                <button class="btn-icon" title="Edit" onclick="showFixedAssetModal(${asset.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" title="Delete" onclick="deleteFixedAsset(${asset.id})"><i class="bi bi-trash"></i></button>
              </td>
            </tr>
    `;
  });

  html += `
          </tbody>
        </table>
      </div>
    </div>
  `;

  container.innerHTML = html;
  applyTranslations();
}

function showGoldPurityGroupDetails(purityKey) {
  const normalizedPurity = normalizeGoldPurity(purityKey || "24k");
  setGoldPurityReturnContext(normalizedPurity);
  const purchases = normalizeFixedAssetsData(fixedAssetsState.assets).filter((asset) => {
    if (!isGoldAssetType(asset.asset_type || asset.type)) return false;
    const assetPurity = normalizeGoldPurity(asset?.gold_details?.purity || asset?.purity || "24k");
    return assetPurity === normalizedPurity;
  });

  if (!purchases.length) {
    showToast(t("no_gold_purchases_for_purity", "No gold purchases found for this purity."), "warning");
    return;
  }

  const rows = purchases
    .sort((a, b) => (String(b.purchase_date || "")).localeCompare(String(a.purchase_date || "")))
    .map((asset) => {
      const weight = parseFloat(asset?.gold_details?.weight) || 0;
      const unit = asset?.gold_details?.unit || "gram";
      return `
        <tr>
          <td>${asset.name || "—"}</td>
          <td>${asset.purchase_date || "—"}</td>
          <td>${fmt(weight)} ${unit}</td>
          <td class="text-end">${fmt(asset.purchase_price)}</td>
          <td class="text-end">${fmt(asset.current_market_value)}</td>
          <td class="d-flex gap-2">
            <button class="btn-icon" title="${t("view", "View")}" onclick="openGoldPurchaseDetails(${asset.id}, '${normalizedPurity}')"><i class="bi bi-eye"></i></button>
            <button class="btn-icon" title="${t("edit", "Edit")}" onclick="openGoldPurchaseEditor(${asset.id}, '${normalizedPurity}')"><i class="bi bi-pencil"></i></button>
            <button class="btn-icon del" title="${t("delete", "Delete")}" onclick="deleteFixedAssetFromGoldGroup(${asset.id}, '${normalizedPurity}')"><i class="bi bi-trash"></i></button>
          </td>
        </tr>
      `;
    })
    .join("");

  const html = `
    <div class="modal-header">
      <h5 class="modal-title" data-i18n="gold_purity_group_details">${t("gold_purity_group_details", "Gold Purity Details")}: ${normalizedPurity.toUpperCase()}</h5>
      <button type="button" class="btn-close btn-close-white" onclick="clearGoldPurityReturnContext(); closeModal()"></button>
    </div>
    <div class="modal-body">
      <div style="margin-bottom:12px;font-weight:600;color:var(--text-secondary);">
        <span data-i18n="number_of_purchases">${t("number_of_purchases", "Number of Purchases")}</span>: ${fmtInt(purchases.length)}
      </div>
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th data-i18n="asset_name">${t("asset_name", "Asset Name")}</th>
              <th data-i18n="purchase_date">${t("purchase_date", "Purchase Date")}</th>
              <th data-i18n="weight">${t("weight", "Weight")}</th>
              <th class="text-end" data-i18n="purchase_price_egp">${t("purchase_price_egp", "Purchase Price")}</th>
              <th class="text-end" data-i18n="current_market_value">${t("current_market_value", "Current Market Value")}</th>
              <th data-i18n="actions">${t("actions", "Actions")}</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    </div>
  `;

  showModal(html);
  applyTranslations();
}

function renderFixedAssetsDashboard(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = buildDashboardAnalyticsAssets(assets);

  if (!assetsArray.length) {
    container.innerHTML = `
      <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
          <div class="display-5 mb-3">📈</div>
          <h4 class="mt-2 fixed-assets-empty-title" data-i18n="fixed_assets_dashboard_empty">No Dashboard Data</h4>
          <p class="small mb-0 fixed-assets-muted" data-i18n="fixed_assets_dashboard_empty_desc">Add fixed assets to see your dashboard analytics.</p>
      </div>
    `;
    applyTranslations();
    return;
  }

  const metrics = getFixedAssetsDashboardMetrics(assetsArray);
  const gainColor = metrics.totalGain >= 0 ? "#17a34a" : "#ef4444";

  container.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px;">
      ${renderFixedAssetsKpi("bi bi-building", "total_assets", fmtInt(metrics.totalAssets))}
      ${renderFixedAssetsKpi("bi bi-cash-stack", "total_purchase_value", fmt(metrics.totalPurchaseValue))}
      ${renderFixedAssetsKpi("bi bi-graph-up-arrow", "current_market_value", fmt(metrics.currentMarketValue))}
      ${renderFixedAssetsKpi("bi bi-plus-slash-minus", "total_gain", `<span style="color:${gainColor}">${fmt(metrics.totalGain)}</span>`)}
      ${renderFixedAssetsKpi("bi bi-percent", "average_appreciation_percent", `${fmtpresent(metrics.averageAppreciation)}%`)}
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;">
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-weight:700;margin-bottom:14px;" data-i18n="asset_allocation"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsAllocationChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-weight:700;margin-bottom:14px;" data-i18n="asset_type_distribution"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsTypeChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-weight:700;margin-bottom:14px;" data-i18n="portfolio_distribution"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsPortfolioChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-weight:700;margin-bottom:14px;" data-i18n="value_growth_over_time"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsGrowthChart"></canvas></div>
      </div>
    </div>
  `;

  applyTranslations();
  drawFixedAssetsDashboardCharts(metrics);
}

function renderFixedAssetsAnalytics(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = buildDashboardAnalyticsAssets(assets);

  if (!assetsArray.length) {
    container.innerHTML = `
      <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
          <div class="display-5 mb-3">📊</div>
          <h4 class="mt-2 fixed-assets-empty-title" data-i18n="fixed_assets_analytics_empty">No Analytics Data</h4>
          <p class="small mb-0 fixed-assets-muted" data-i18n="fixed_assets_analytics_empty_desc">Add fixed assets to calculate analytics.</p>
      </div>
    `;
    applyTranslations();
    return;
  }

  const metrics = getFixedAssetsAnalyticsMetrics(assetsArray);

  const portfolioCards = renderFixedAssetsPortfolioCards(metrics, fixedAssetsState.portfolioSnapshot);
  const tableRows = metrics.assetRows.length
    ? metrics.assetRows.map((row) => `
      <tr>
        <td class="fixed-assets-card-title">${row.name}</td>
        <td data-i18n="${fixedAssetTypeToI18nKey(row.type)}">${row.type}</td>
        <td class="text-end">${fmtpresent(row.roi)}%</td>
        <td class="text-end">${fmtpresent(row.appreciation)}%</td>
        <td class="text-end">${fmtpresent(row.annualReturn)}%</td>
        <td class="text-end">${row.holdingPeriodLabel}</td>
        <td class="text-end">${fmtpresent(row.renovationCostPercent)}%</td>
        <td class="text-end ${row.gainAmount >= 0 ? "text-success" : "text-danger"}">${fmt(row.gainAmount)}</td>
      </tr>
    `).join("")
    : _noDataFixedAssets(8);

  container.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:20px;">
      ${portfolioCards}
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;margin-bottom:20px;">
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px;" data-i18n="liquid_vs_fixed_assets"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsLiquidVsFixedChart"></canvas></div>
      </div>
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px;" data-i18n="asset_performance"></div>
        <div style="position:relative;height:280px;"><canvas id="fixedAssetsPerformanceChart"></canvas></div>
      </div>
    </div>

    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:hidden;">
      <div class="fixed-assets-section-title" style="padding:14px 20px;font-weight:700;border-bottom:1px solid var(--border-color);" data-i18n="per_asset_analytics"></div>
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th data-i18n="asset_name">Asset Name</th>
              <th data-i18n="asset_type">Asset Type</th>
              <th class="text-end" data-i18n="roi">ROI</th>
              <th class="text-end" data-i18n="appreciation_percent">Appreciation %</th>
              <th class="text-end" data-i18n="annual_return">Annual Return</th>
              <th class="text-end" data-i18n="holding_period">Holding Period</th>
              <th class="text-end" data-i18n="renovation_cost_percent">Renovation Cost %</th>
              <th class="text-end" data-i18n="gain_amount">Gain Amount</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>
      </div>
    </div>
  `;

  applyTranslations();
  drawFixedAssetsAnalyticsCharts(metrics, fixedAssetsState.portfolioSnapshot);
}

function renderFixedAssetsReports(assets) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  const assetsArray = normalizeFixedAssetsData(assets);

  if (!assetsArray.length) {
    container.innerHTML = `
      <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
          <div class="display-5 mb-3">🗂️</div>
          <h4 class="mt-2 fixed-assets-empty-title" data-i18n="fixed_assets_reports_empty">No Reports Data</h4>
          <p class="small mb-0 fixed-assets-muted" data-i18n="fixed_assets_reports_empty_desc">Add fixed assets to generate reports.</p>
      </div>
    `;
    applyTranslations();
    return;
  }

  const options = assetsArray
    .map((asset) => `<option value="${asset.id}">${asset.name || "—"}</option>`)
    .join("");

  container.innerHTML = `
    <div style="display:grid;grid-template-columns:minmax(0,1.4fr) minmax(320px,1fr);gap:16px;align-items:start;">
      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div class="fixed-assets-section-title" style="font-size:18px;font-weight:700;margin-bottom:8px;" data-i18n="fixed_assets_reports_title"></div>
        <div class="fixed-assets-section-note" style="font-size:13px;margin-bottom:18px;" data-i18n="fixed_assets_reports_subtitle"></div>

        <div class="row g-3 mb-3">
          <div class="col-md-6">
            <label class="form-label text-light" data-i18n="report_scope"></label>
            <select class="form-select" id="fixedAssetsReportScope" onchange="toggleFixedAssetsReportScope()">
              <option value="single" data-i18n="single_asset">Single Asset</option>
              <option value="portfolio" data-i18n="entire_portfolio">Entire Portfolio</option>
            </select>
          </div>
          <div class="col-md-6" id="fixedAssetsReportAssetWrap">
            <label class="form-label text-light" data-i18n="select_asset"></label>
            <select class="form-select" id="fixedAssetsReportAsset">
              ${options}
            </select>
          </div>
        </div>

        <div class="d-flex flex-wrap gap-2">
          <button class="btn-primary-custom" onclick="downloadFixedAssetsReport('pdf')">
            <i class="bi bi-file-earmark-pdf"></i> <span data-i18n="generate_pdf">Generate PDF</span>
          </button>
          <button class="btn-secondary-custom" onclick="downloadFixedAssetsReport('excel')">
            <i class="bi bi-file-earmark-excel"></i> <span data-i18n="download_excel">Download Excel Workbook</span>
          </button>
        </div>
      </div>

      <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;">
        <div style="font-size:16px;font-weight:700;color:var(--text-primary);margin-bottom:12px;" data-i18n="report_contents"></div>
        <div style="display:grid;gap:10px;">
          <div style="padding:12px;border:1px solid var(--border-color);border-radius:10px;color:var(--text-secondary);" data-i18n="report_includes_general_property"></div>
          <div style="padding:12px;border:1px solid var(--border-color);border-radius:10px;color:var(--text-secondary);" data-i18n="report_includes_photos_renovations"></div>
          <div style="padding:12px;border:1px solid var(--border-color);border-radius:10px;color:var(--text-secondary);" data-i18n="report_includes_furniture_valuations"></div>
          <div style="padding:12px;border:1px solid var(--border-color);border-radius:10px;color:var(--text-secondary);" data-i18n="report_includes_sale_info"></div>
        </div>
      </div>
    </div>
  `;

  const scopeField = document.getElementById("fixedAssetsReportScope");
  if (scopeField) {
    scopeField.value = "single";
  }

  applyTranslations();
  toggleFixedAssetsReportScope();
}

function toggleFixedAssetsReportScope() {
  const scopeField = document.getElementById("fixedAssetsReportScope");
  const assetWrap = document.getElementById("fixedAssetsReportAssetWrap");
  const isSingle = scopeField?.value !== "portfolio";

  if (assetWrap) {
    assetWrap.style.display = isSingle ? "block" : "none";
  }
}

async function downloadFixedAssetsReport(format) {
  const scope = document.getElementById("fixedAssetsReportScope")?.value || "single";
  const assetId = document.getElementById("fixedAssetsReportAsset")?.value || "";

  if (scope === "single" && !assetId) {
    showToast(t("report_asset_required", "Please select an asset first."), "warning");
    return;
  }

  const btn = event?.currentTarget || event?.target;
  const loadingText = t("generating", "Generating...");
  const originalHtml = btn?.innerHTML;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner-border spinner-border-sm"></div> ${loadingText}`;
  }

  try {
    const params = new URLSearchParams({
      scope,
      lang: currentLang(),
    });

    if (scope === "single") {
      params.set("asset_id", assetId);
    }

    const endpoint =
      format === "pdf"
        ? "/api/fixed-assets/reports/pdf/"
        : "/api/fixed-assets/reports/excel/";

    const response = await fetch(`${endpoint}?${params.toString()}`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || t("download_report_failed", "Failed to download report."));
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const disposition = response.headers.get("Content-Disposition") || "";
    const fileNameMatch = disposition.match(/filename="(.+)"/);

    anchor.href = url;
    anchor.download =
      fileNameMatch?.[1] || `fixed_assets_report.${format === "pdf" ? "pdf" : "xlsx"}`;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

function renderFixedAssetsPortfolioCards(metrics, snapshot) {
  const fixedValueCard = renderFixedAssetsKpi(
    "bi bi-bank2",
    "total_fixed_assets_value",
    fmt(metrics.totalFixedAssetsValue),
  );

  if (!snapshot) {
    return `
      ${fixedValueCard}
      ${renderFixedAssetsKpi("bi bi-pie-chart", "net_worth_contribution", "...")}
      ${renderFixedAssetsKpi("bi bi-arrows-collapse", "liquid_vs_fixed_assets", "...")}
      ${renderFixedAssetsKpi("bi bi-diagram-3", "diversification", `${fmtpresent(metrics.diversificationScore)}%`)}
    `;
  }

  const liquidVsFixedLabel = `${fmtpresent(snapshot.liquidAssetsRatio)}% / ${fmtpresent(snapshot.fixedAssetsRatio)}%`;

  return `
    ${fixedValueCard}
    ${renderFixedAssetsKpi("bi bi-pie-chart", "net_worth_contribution", `${fmtpresent(snapshot.netWorthContribution)}%`)}
    ${renderFixedAssetsKpi("bi bi-arrows-collapse", "liquid_vs_fixed_assets", liquidVsFixedLabel)}
    ${renderFixedAssetsKpi("bi bi-diagram-3", "diversification", `${fmtpresent(metrics.diversificationScore)}%`)}
  `;
}

function getFixedAssetsAnalyticsMetrics(assets) {
  const now = new Date();
  const assetRows = assets.map((asset) => {
    const purchasePrice = parseFloat(asset.purchase_price) || 0;
    const currentValue = parseFloat(asset.current_market_value) || 0;
    const gainAmount = currentValue - purchasePrice;
    const renovationCost = (asset.renovations || []).reduce(
      (sum, item) => sum + (parseFloat(item.amount_egp) || 0),
      0,
    );
    const investmentBase = purchasePrice + renovationCost;
    const roi = investmentBase > 0 ? ((currentValue - investmentBase) / investmentBase) * 100 : 0;
    const appreciation = purchasePrice > 0 ? (gainAmount / purchasePrice) * 100 : 0;

    const purchaseDate = asset.purchase_date ? new Date(asset.purchase_date) : null;
    const holdingYearsRaw = purchaseDate ? (now - purchaseDate) / (1000 * 60 * 60 * 24 * 365.25) : 0;
    const holdingYears = holdingYearsRaw > 0 ? holdingYearsRaw : 0;
    const annualReturn = purchasePrice > 0 && holdingYears > 0
      ? (Math.pow(currentValue / purchasePrice, 1 / holdingYears) - 1) * 100
      : 0;
    const holdingMonths = purchaseDate
      ? Math.max(0, Math.round((now - purchaseDate) / (1000 * 60 * 60 * 24 * 30.4375)))
      : 0;
    const renovationCostPercent = purchasePrice > 0 ? (renovationCost / purchasePrice) * 100 : 0;

    return {
      name: asset.name || "—",
      type: asset.asset_type || t("type_other", "Other"),
      roi,
      appreciation,
      annualReturn: Number.isFinite(annualReturn) ? annualReturn : 0,
      holdingPeriodMonths: holdingMonths,
      holdingPeriodLabel: formatHoldingPeriod(holdingMonths),
      renovationCostPercent,
      gainAmount,
      currentValue,
    };
  });

  const totalFixedAssetsValue = assetRows.reduce((sum, row) => sum + row.currentValue, 0);
  const shares = assetRows
    .map((row) => (totalFixedAssetsValue > 0 ? row.currentValue / totalFixedAssetsValue : 0))
    .filter((share) => share > 0);
  const concentration = shares.reduce((sum, share) => sum + share * share, 0);
  const diversificationScore = shares.length > 1
    ? Math.max(0, ((1 - concentration) / (1 - 1 / shares.length)) * 100)
    : shares.length === 1 ? 0 : 100;

  return {
    totalFixedAssetsValue,
    diversificationScore,
    assetRows,
  };
}

function formatHoldingPeriod(months) {
  if (!months) {
    return `0 ${t("months", "Months")}`;
  }

  if (months < 12) {
    return `${months} ${t("months", "Months")}`;
  }

  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;

  if (!remainingMonths) {
    return `${years} ${t("years", "Years")}`;
  }

  return `${years} ${t("years", "Years")} ${remainingMonths} ${t("months", "Months")}`;
}

async function loadFixedAssetsPortfolioSnapshot() {
  fixedAssetsState.portfolioSnapshotLoading = true;

  try {
    const response = await fetch("/api/fixed-assets/");
    if (!response.ok) throw new Error("Failed to load analytics snapshot");

    const data = await response.json();
    fixedAssetsState.portfolioSnapshot = data?.portfolio_snapshot || null;
  } catch (err) {
    fixedAssetsState.portfolioSnapshot = null;
    console.error(err);
  } finally {
    fixedAssetsState.portfolioSnapshotLoading = false;
    if (fixedAssetsState.activeTab === "analytics") {
      renderActiveFixedAssetsTab();
    }
  }
}

function drawFixedAssetsAnalyticsCharts(metrics, snapshot) {
  const liquidValue = snapshot?.liquidAssetsValue || 0;
  const fixedValue = snapshot?.fixedAssetsValue || metrics.totalFixedAssetsValue;

  drawFixedAssetsDoughnutChart(
    "fixedAssetsLiquidVsFixedChart",
    [t("liquid_assets", "Liquid Assets"), t("fixed_assets", "Fixed Assets")],
    [liquidValue, fixedValue],
  );

  const performanceRows = [...metrics.assetRows]
    .sort((a, b) => b.roi - a.roi)
    .slice(0, 8);

  drawFixedAssetsBarChart(
    "fixedAssetsPerformanceChart",
    performanceRows.map((row) => row.name),
    [
      {
        label: t("roi", "ROI"),
        data: performanceRows.map((row) => row.roi),
        color: "#1a6ef5",
      },
      {
        label: t("annual_return", "Annual Return"),
        data: performanceRows.map((row) => row.annualReturn),
        color: "#10b981",
      },
    ],
  );
}

function renderFixedAssetsKpi(iconClass, labelKey, value) {
  return `
    <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:18px 20px;">
      <div style="font-size:20px;margin-bottom:6px;color:var(--accent-primary);"><i class="${iconClass}"></i></div>
      <div style="font-size:11px;font-weight:700;letter-spacing:.05em;color:var(--text-secondary);text-transform:uppercase;margin-bottom:6px;" data-i18n="${labelKey}"></div>
      <div style="font-size:22px;font-weight:800;color:var(--text-primary);">${value}</div>
    </div>
  `;
}

function renderFixedAssetsPlaceholder(titleKey, descKey) {
  const container = document.getElementById("fixedAssetsContainer");
  if (!container) return;

  container.innerHTML = `
    <div class="text-center p-5 rounded-3" style="background: var(--bg-secondary); border: 1px dashed var(--border-color); margin-top: 2rem;">
        <div class="display-5 mb-3">🧭</div>
        <h4 class="mt-2 fixed-assets-empty-title" data-i18n="${titleKey}"></h4>
        <p class="small mb-0" style="color:var(--text-secondary);" data-i18n="${descKey}"></p>
    </div>
  `;
  applyTranslations();
}

function getFixedAssetsDashboardMetrics(assets) {
  const totalAssets = assets.length;
  const totalPurchaseValue = assets.reduce(
    (sum, asset) => sum + (parseFloat(asset.purchase_price) || 0),
    0,
  );
  const currentMarketValue = assets.reduce(
    (sum, asset) => sum + (parseFloat(asset.current_market_value) || 0),
    0,
  );
  const totalGain = currentMarketValue - totalPurchaseValue;

  const appreciationValues = assets
    .filter((asset) => (parseFloat(asset.purchase_price) || 0) > 0)
    .map((asset) => {
      const purchase = parseFloat(asset.purchase_price) || 0;
      const current = parseFloat(asset.current_market_value) || 0;
      return ((current - purchase) / purchase) * 100;
    });

  const averageAppreciation = appreciationValues.length
    ? appreciationValues.reduce((sum, value) => sum + value, 0) /
      appreciationValues.length
    : 0;

  const allocation = assets
    .map((asset) => ({
      label: asset.name || "—",
      value: parseFloat(asset.current_market_value) || 0,
    }))
    .filter((item) => item.value > 0);

  const typeMap = new Map();
  assets.forEach((asset) => {
    const key = asset.asset_type || t("type_other");
    typeMap.set(key, (typeMap.get(key) || 0) + 1);
  });

  const portfolioStatusMap = new Map();
  assets.forEach((asset) => {
    const isSold = asset.status === "Sold";
    const label = isSold ? t("sold_assets") : t("owned_assets");
    const value = isSold
      ? parseFloat(asset.sale?.net_sale_amount) || parseFloat(asset.sale?.sale_price) || 0
      : parseFloat(asset.current_market_value) || 0;
    portfolioStatusMap.set(label, (portfolioStatusMap.get(label) || 0) + value);
  });

  const growthSeries = buildFixedAssetsGrowthSeries(assets);

  return {
    totalAssets,
    totalPurchaseValue,
    currentMarketValue,
    totalGain,
    averageAppreciation,
    allocation,
    typeDistribution: Array.from(typeMap.entries()).map(([label, value]) => ({
      label,
      value,
    })),
    portfolioDistribution: Array.from(portfolioStatusMap.entries())
      .map(([label, value]) => ({ label, value }))
      .filter((item) => item.value > 0),
    growthSeries,
  };
}

function buildFixedAssetsGrowthSeries(assets) {
  const sortedAssets = [...assets].sort((a, b) => {
    const dateA = new Date(a.purchase_date || 0).getTime();
    const dateB = new Date(b.purchase_date || 0).getTime();
    return dateA - dateB;
  });

  let cumulativePurchase = 0;
  let cumulativeCurrent = 0;

  const labels = [];
  const purchaseValues = [];
  const currentValues = [];

  sortedAssets.forEach((asset) => {
    cumulativePurchase += parseFloat(asset.purchase_price) || 0;
    cumulativeCurrent += parseFloat(asset.current_market_value) || 0;

    labels.push(asset.purchase_date || asset.name || "—");
    purchaseValues.push(cumulativePurchase);
    currentValues.push(cumulativeCurrent);
  });

  return {
    labels,
    purchaseValues,
    currentValues,
  };
}

function drawFixedAssetsDashboardCharts(metrics) {
  drawFixedAssetsDoughnutChart(
    "fixedAssetsAllocationChart",
    metrics.allocation.map((item) => item.label),
    metrics.allocation.map((item) => item.value),
  );
  drawFixedAssetsDoughnutChart(
    "fixedAssetsTypeChart",
    metrics.typeDistribution.map((item) => item.label),
    metrics.typeDistribution.map((item) => item.value),
  );
  drawFixedAssetsDoughnutChart(
    "fixedAssetsPortfolioChart",
    metrics.portfolioDistribution.map((item) => item.label),
    metrics.portfolioDistribution.map((item) => item.value),
  );
  drawFixedAssetsLineChart(
    "fixedAssetsGrowthChart",
    metrics.growthSeries.labels,
    [
      {
        label: t("total_purchase_value"),
        data: metrics.growthSeries.purchaseValues,
        color: "#1a6ef5",
      },
      {
        label: t("current_market_value"),
        data: metrics.growthSeries.currentValues,
        color: "#10b981",
      },
    ],
  );
}

function getFixedAssetsChartTheme() {
  const styles = getComputedStyle(document.documentElement);
  return {
    textPrimary: styles.getPropertyValue("--text-primary").trim() || "#e2e8f0",
    textSecondary: styles.getPropertyValue("--text-secondary").trim() || "#94a3b8",
    borderColor: styles.getPropertyValue("--border-color").trim() || "#1e293b",
  };
}

function drawFixedAssetsDoughnutChart(canvasId, labels, data) {
  setTimeout(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;
    const chartTheme = getFixedAssetsChartTheme();
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: ["#1a6ef5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"].slice(0, data.length),
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: {
              color: chartTheme.textSecondary,
              boxWidth: 12,
              padding: 12,
            },
          },
        },
      },
    });
  }, 50);
}

function drawFixedAssetsBarChart(canvasId, labels, datasets) {
  setTimeout(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;
    const chartTheme = getFixedAssetsChartTheme();
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: datasets.map((dataset) => ({
          label: dataset.label,
          data: dataset.data,
          backgroundColor: `${dataset.color}cc`,
          borderColor: dataset.color,
          borderWidth: 1,
          borderRadius: 4,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: chartTheme.textSecondary,
              boxWidth: 12,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: chartTheme.textSecondary },
            grid: { color: chartTheme.borderColor },
          },
          y: {
            ticks: { color: chartTheme.textSecondary },
            grid: { color: chartTheme.borderColor },
          },
        },
      },
    });
  }, 50);
}

function drawFixedAssetsLineChart(canvasId, labels, datasets) {
  setTimeout(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;
    const chartTheme = getFixedAssetsChartTheme();
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: datasets.map((dataset) => ({
          label: dataset.label,
          data: dataset.data,
          borderColor: dataset.color,
          backgroundColor: `${dataset.color}33`,
          borderWidth: 2,
          fill: false,
          tension: 0.25,
          pointRadius: 3,
          pointBackgroundColor: dataset.color,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: chartTheme.textSecondary,
              boxWidth: 12,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: chartTheme.textSecondary },
            grid: { color: chartTheme.borderColor },
          },
          y: {
            ticks: { color: chartTheme.textSecondary },
            grid: { color: chartTheme.borderColor },
          },
        },
      },
    });
  }, 50);
}

function _noDataFixedAssets(cols) {
  return `<tr><td colspan="${cols}" style="text-align:center;padding:28px;color:var(--text-secondary)" data-i18n="no_data">${t("no_data", "No data available")}</td></tr>`;
}

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

// ════════════════════════════════════════════════════════════════════════════
// MODALS & ACTIONS
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
  const modalTitleDefault = isEdit
    ? "Edit Asset Details"
    : "Register New Fixed Asset";

  const html = `
        <div class="modal-header">
            <h5 class="modal-title fixed-assets-heading" data-i18n="${modalTitleKey}">${modalTitleDefault}</h5>
            <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
        </div>
        <div class="modal-body" style="max-height: 75vh; overflow-y: auto; overflow-x: hidden; padding: 1.5rem;">
          <form id="fixedAssetForm">

              <ul class="nav nav-tabs mb-4" id="fixedAssetTabs" role="tablist">
                  <li class="nav-item" role="presentation">
                      <button class="nav-link active"
                              id="general-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#general-pane"
                              type="button"
                              role="tab"
                              aria-controls="general-pane"
                              aria-selected="true"
                              data-i18n="general">
                          General
                      </button>
                  </li>

                  <li class="nav-item" role="presentation">
                      <button class="nav-link"
                              id="property-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#property-pane"
                              type="button"
                              role="tab"
                              aria-controls="property-pane"
                              aria-selected="false"
                              data-i18n="property">
                          Property
                      </button>
                  </li>

                    <li class="nav-item d-none" role="presentation" id="vehicle-tab-item">
                      <button class="nav-link"
                          id="vehicle-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#vehicle-pane"
                          type="button"
                          role="tab"
                          aria-controls="vehicle-pane"
                          aria-selected="false"
                          data-i18n="vehicle">
                        Vehicle
                      </button>
                    </li>

                    <li class="nav-item d-none" role="presentation" id="gold-tab-item">
                      <button class="nav-link"
                          id="gold-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#gold-pane"
                          type="button"
                          role="tab"
                          aria-controls="gold-pane"
                          aria-selected="false"
                          data-i18n="gold_details">
                        Gold Details
                      </button>
                    </li>

                    <li class="nav-item d-none" role="presentation" id="other-details-tab-item">
                      <button class="nav-link"
                          id="other-details-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#other-details-pane"
                          type="button"
                          role="tab"
                          aria-controls="other-details-pane"
                          aria-selected="false"
                          data-i18n="details">
                        Details
                      </button>
                    </li>

                    <li class="nav-item" role="presentation">
                      <button class="nav-link"
                          id="photos-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#photos-pane"
                          type="button"
                          role="tab"
                          aria-controls="photos-pane"
                          aria-selected="false"
                          data-i18n="photos">
                        Photos
                      </button>
                    </li>

                  <li class="nav-item" role="presentation">
                      <button class="nav-link"
                              id="renovation-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#renovation-pane"
                              type="button"
                              role="tab"
                              aria-controls="renovation-pane"
                              aria-selected="false"
                              data-i18n="renovations">
                          Renovations
                      </button>
                  </li>

                        <li class="nav-item d-none" role="presentation" id="maintenance-tab-item">
                          <button class="nav-link"
                              id="maintenance-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#maintenance-pane"
                              type="button"
                              role="tab"
                              aria-controls="maintenance-pane"
                              aria-selected="false"
                              data-i18n="maintenance">
                            Maintenance
                          </button>
                        </li>

                        <li class="nav-item d-none" role="presentation" id="insurance-tab-item">
                          <button class="nav-link"
                              id="insurance-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#insurance-pane"
                              type="button"
                              role="tab"
                              aria-controls="insurance-pane"
                              aria-selected="false"
                              data-i18n="insurance">
                            Insurance
                          </button>
                        </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="furniture-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#furniture-pane"
                                type="button"
                                role="tab"
                                aria-controls="furniture-pane"
                                aria-selected="false"
                                data-i18n="furniture">
                              Furniture
                            </button>
                          </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="valuation-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#valuation-pane"
                                type="button"
                                role="tab"
                                aria-controls="valuation-pane"
                                aria-selected="false"
                                data-i18n="valuation_history">
                              Valuation History
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="mortgage-tab-item">
                            <button class="nav-link"
                                id="mortgage-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#mortgage-pane"
                                type="button"
                                role="tab"
                                aria-controls="mortgage-pane"
                                aria-selected="false"
                                data-i18n="mortgage">
                              Mortgage
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="rental-tab-item">
                            <button class="nav-link"
                                id="rental-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#rental-pane"
                                type="button"
                                role="tab"
                                aria-controls="rental-pane"
                                aria-selected="false"
                                data-i18n="rental">
                              Rental
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="sale-tab-item">
                            <button class="nav-link"
                                id="sale-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#sale-pane"
                                type="button"
                                role="tab"
                                aria-controls="sale-pane"
                                aria-selected="false"
                                data-i18n="sale">
                              Sale
                            </button>
                          </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="documents-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#documents-pane"
                                type="button"
                                role="tab"
                                aria-controls="documents-pane"
                                aria-selected="false"
                                data-i18n="documents_title">
                              Documents
                            </button>
                          </li>
              </ul>

              <div class="tab-content" id="fixedAssetTabsContent">

                  <!-- 1. GENERAL TAB PANE -->
                  <div class="tab-pane fade show active"
                      id="general-pane"
                      role="tabpanel"
                      aria-labelledby="general-tab">

                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                              <label class="form-label fixed-assets-section-title" data-i18n="asset_type">Asset Type</label>
                              <select class="form-select" id="fa_type" onchange="toggleRealEstateFields()" required>
                                  <option value="Real Estate" data-i18n="type_real_estate">Real Estate</option>
                                  <option value="Vehicles" data-i18n="type_vehicles">Vehicles</option>
                                  <option value="Gold" data-i18n="type_gold">Gold</option>
                                  <option value="Other Assets" data-i18n="type_other_assets">Other Assets</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                              <label class="form-label fixed-assets-section-title" data-i18n="asset_name">Asset Name</label>
                              <input type="text" class="form-control" id="fa_name" required>
                            </div>
                        </div>

                            <div class="row g-3 mb-3">
                              <div class="col-md-6">
                                <label class="form-label text-light" data-i18n="asset_status">Asset Status</label>
                                <select class="form-select" id="fa_status" required>
                                  <option value="Owned" data-i18n="owned">Owned</option>
                                  <option value="Sold" data-i18n="sold">Sold</option>
                                </select>
                              </div>
                            </div>

                        <div class="row g-3 mb-3">
                          <div class="col-md-3">
                            <label class="form-label text-light" data-i18n="purchase_currency">Purchase Currency</label>
                            <select class="form-select" id="fa_purchase_currency" onchange="handlePurchaseCurrencyChange()" required></select>
                          </div>
                          <div class="col-md-3">
                            <label class="form-label text-light" data-i18n="purchase_price_egp">Purchase Price</label>
                                <input type="number" step="0.01" class="form-control" oninput="updatePurchasePriceUSD()" id="fa_purchase_price" required>
                            </div>
                          <div class="col-md-3">
                                <label class="form-label text-light" data-i18n="purchase_usd_rate">USD Exchange Rate</label>
                            <div class="input-group">
                              <input type="number" step="0.00001" class="form-control" oninput="updatePurchasePriceUSD()" id="fa_purchase_usd_rate" required>
                              <button type="button" class="btn btn-outline-secondary" onclick="fillCurrentUsdRate()" data-i18n="current_rate_btn">Now</button>
                            </div>
                            </div>
                          <div class="col-md-3">
                                <label class="form-label text-light" data-i18n="purchase_price_usd">Purchase Price (USD)</label>
                                <input type="number" step="0.01" class="form-control" id="fa_purchase_price_usd" readonly>
                            </div>
                        </div>

                        <div class="row g-3 mb-3">
                            <div class="col-md-4">
                                <label class="form-label text-light" data-i18n="purchase_date">Purchase Date</label>
                                <input type="date" class="form-control" id="fa_purchase_date" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-light" data-i18n="current_market_value">Current Market Value</label>
                                <input type="number" step="0.01" class="form-control" id="fa_current_value" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-light" data-i18n="last_valuation_date">Last Valuation Date</label>
                                <input type="date" class="form-control" id="fa_last_valuation_date" required>
                            </div>
                        </div>

                        <div class="card border-0 shadow-sm bg-transparent mb-3">
                          <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                            <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="payment_information">Payment Information</h6>
                            <button type="button" class="btn btn-outline-primary btn-sm" onclick="addPurchasePaymentRow()" data-i18n="add_payment_source">+ Add Payment Source</button>
                          </div>
                          <div class="card-body px-0 pt-2">
                            <div id="purchasePaymentsContainer" class="w-100"></div>
                            <div class="small text-light mt-2" style="opacity:0.8;" data-i18n="purchase_payment_total_hint">Total payment sources must equal Purchase Price.</div>
                          </div>
                        </div>

                        <div class="row g-3 mb-3" id="valuation-source-row">
                            <div class="col-md-12">
                                <label class="form-label text-light" data-i18n="valuation_source">Valuation Source</label>
                                <select class="form-select" id="fa_val_source">
                                    <option value="Manual" data-i18n="val_manual">Manual Input</option>
                                    <option value="Automatic" data-i18n="val_automatic">System Synced</option>
                                </select>
                            </div>
                        </div>

                        <!-- FIXED: Notes is now nested exclusively here at the bottom of the General Tab -->
                        <div class="col-md-12">
                            <label class="form-label text-light" data-i18n="notes">Internal Notes</label>
                            <textarea class="form-control" id="fa_notes" rows="2"></textarea>
                        </div>

                  </div> <!-- End General Tab -->

                  <!-- 2. PROPERTY TAB PANE -->
                  <div class="tab-pane fade"
                      id="property-pane"
                      role="tabpanel"
                      aria-labelledby="property-tab">

                        <div id="realEstateSection">
                            <h6 class="mb-3 font-weight-bold fixed-assets-section-title" style="font-size: 0.95rem;" data-i18n="real_estate_details">Real Estate Technical Specifications</h6>
                            
                            <div class="row g-3 mb-3">
                                <div class="col-sm-6 col-md-3"><input type="text" class="form-control" id="re_country" placeholder="Egypt" data-i18n-placeholder="country"></div>
                                <div class="col-sm-6 col-md-3"><input type="text" class="form-control" id="re_governorate" placeholder="Governorate" data-i18n-placeholder="governorate"></div>
                                <div class="col-sm-6 col-md-3"><input type="text" class="form-control" id="re_city" placeholder="City" data-i18n-placeholder="city"></div>
                                <div class="col-sm-6 col-md-3"><input type="text" class="form-control" id="re_district" placeholder="District" data-i18n-placeholder="district"></div>
                            </div>

                            <div class="row g-3 mb-3 align-items-end">
                                <div class="col-md-9">
                                    <input type="text" class="form-control" id="re_address" placeholder="Address Details" data-i18n-placeholder="address">
                                </div>
                                <div class="col-md-3">
                                    <button type="button" class="btn btn-primary w-100" id="btnLocateProperty" data-i18n="locate_on_map">Locate on Map</button>
                                </div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label small text-light" data-i18n="latitude">Latitude</label>
                                    <input type="number" step="0.000001" class="form-control" id="re_latitude" readonly>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small text-light" data-i18n="longitude">Longitude</label>
                                    <input type="number" step="0.000001" class="form-control" id="re_longitude" readonly>
                                </div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-12">
                                    <label class="form-label small text-light" data-i18n="property_location">Property Location</label>
                                    <div id="propertyMap" class="w-100" style="height:300px; border:1px solid var(--border-color); border-radius:8px;"></div>
                                    <small class="form-text text-light" style="opacity: 0.65;" data-i18n="map_click_instruction">Click anywhere on the map to select the property location.</small>
                                </div>
                            </div>

                            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
                              <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                                <div>
                                  <div style="font-weight:600;color:var(--text-secondary);" data-i18n="property_valuation">Property Valuation</div>
                                  <div style="font-size:12px;color:var(--text-muted);" data-i18n="property_valuation_desc">Automatic estimate is applied only when a configured provider can value this property.</div>
                                </div>
                                <button type="button" class="btn-primary-custom" id="btnRefreshPropertyValuation" data-i18n="refresh_property_valuation">Refresh Valuation</button>
                              </div>
                              <div class="row g-3">
                                <div class="col-md-4">
                                  <label class="form-label small text-light" data-i18n="last_estimated_market_price">Last Estimated Market Price</label>
                                  <input type="number" step="0.01" class="form-control" id="re_last_estimated_market_price" readonly>
                                </div>
                                <div class="col-md-4">
                                  <label class="form-label small text-light" data-i18n="last_valuation_date">Last Valuation Date</label>
                                  <input type="date" class="form-control" id="re_last_valuation_date" readonly>
                                </div>
                                <div class="col-md-4">
                                  <label class="form-label small text-light" data-i18n="valuation_provider">Valuation Provider</label>
                                  <input type="text" class="form-control" id="re_valuation_provider" readonly>
                                </div>
                              </div>
                            </div>

                            <hr class="my-4">
                            <div class="row g-3 mb-3">
                                <div class="col-sm-6 col-md-4"><label class="form-label small text-light" data-i18n="apt_area">Property Area (Sqm)</label><input type="number" class="form-control" id="re_area"></div>
                                <div class="col-sm-6 col-md-4"><label class="form-label small text-light" data-i18n="land_area">Land Plot Footprint (Sqm)</label><input type="number" class="form-control" id="re_land_area"></div>
                                <div class="col-6 col-md-2"><label class="form-label small text-light" data-i18n="rooms">Bedrooms</label><input type="number" class="form-control" id="re_rooms"></div>
                                <div class="col-6 col-md-2"><label class="form-label small text-light" data-i18n="bathrooms">Bathrooms</label><input type="number" class="form-control" id="re_bathrooms"></div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-6 col-md-3"><label class="form-label small text-light" data-i18n="floor">Floor Number</label><input type="number" class="form-control" id="re_floor"></div>
                                <div class="col-6 col-md-3"><label class="form-label small text-light" data-i18n="building_floors">Total Building Stories</label><input type="number" class="form-control" id="re_b_floors"></div>
                                <div class="col-6 col-md-3"><label class="form-label small text-light" data-i18n="building_year">Construction Year</label><input type="number" class="form-control" id="re_year"></div>
                                <div class="col-6 col-md-3"><label class="form-label small text-light" data-i18n="facades">Facade Orientation</label><input type="text" class="form-control" id="re_facades"></div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label small text-light" data-i18n="furnished_status">Furnished Status</label>
                                    <select class="form-select" id="re_furnished">
                                        <option value="Unfurnished" data-i18n="unfurnished">Unfurnished</option>
                                        <option value="Semi Furnished" data-i18n="semi_furnished">Semi Furnished</option>
                                        <option value="Fully Furnished" data-i18n="fully_furnished">Fully Furnished</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small text-light" data-i18n="finishing_level">Finishing Level Type</label>
                                    <select class="form-select" id="re_finishing">
                                        <option value="Shell & Core" data-i18n="shell_core">Shell & Core</option>
                                        <option value="Semi Finished" data-i18n="semi_finished">Semi Finished</option>
                                        <option value="Fully Finished" data-i18n="fully_finished">Fully Finished</option>
                                        <option value="Luxury Finished" data-i18n="luxury_finished">Luxury Finished</option>
                                    </select>
                                </div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label small d-block mb-2 text-light" data-i18n="utilities">Available Utilities</label>
                                <div class="fa-chip-check-list">
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_util_elec">
                                        <label class="form-check-label small text-light" for="re_util_elec" data-i18n="electricity">Electricity Grid</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_util_water">
                                        <label class="form-check-label small text-light" for="re_util_water" data-i18n="water">Water Line</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_util_gas">
                                        <label class="form-check-label small text-light" for="re_util_gas" data-i18n="gas">Natural Gas</label>
                                    </div>
                                </div>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small d-block mb-2 text-light" data-i18n="features">Structural Amenities</label>
                                <div class="fa-chip-check-list">
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_feat_elevator">
                                        <label class="form-check-label small text-light" for="re_feat_elevator" data-i18n="elevator">Elevator</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_feat_garage">
                                        <label class="form-check-label small text-light" for="re_feat_garage" data-i18n="garage">Garage</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_has_land_share">
                                        <label class="form-check-label small text-light" for="re_has_land_share" data-i18n="has_land_share">Land Share</label>
                                    </div>
                                <div class="form-check fa-chip-check">
                                        <input class="form-check-input" type="checkbox" id="re_feat_licensed">
                                        <label class="form-check-label small text-light" for="re_feat_licensed" data-i18n="licensed">Licensed</label>
                                    </div>
                                </div>
                                </div>
                            </div>

                            <div class="row g-3">
                                <div class="col-md-4">
                                    <label class="form-label small text-light" data-i18n="land_share">Undivided Land Share (Carat)</label>
                                    <input type="text" class="form-control" id="re_land_share">
                                </div>
                                <div class="col-md-8">
                                    <label class="form-label small text-light" data-i18n="description">Property Structural Description</label>
                                    <input type="text" class="form-control" id="re_description">
                                </div>
                            </div>
                        </div>
                        
                  </div> <!-- End Property Tab -->

                  <div class="tab-pane fade"
                      id="vehicle-pane"
                      role="tabpanel"
                      aria-labelledby="vehicle-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                          <div class="card-body px-0 pt-2">
                            <div class="row g-3">
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="brand">Brand</label><input type="text" class="form-control" id="vd_brand"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="model">Model</label><input type="text" class="form-control" id="vd_model"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="year">Year</label><input type="number" class="form-control" id="vd_year"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="vin">VIN</label><input type="text" class="form-control" id="vd_vin"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="engine">Engine</label><input type="text" class="form-control" id="vd_engine"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="transmission">Transmission</label><input type="text" class="form-control" id="vd_transmission"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="fuel_type">Fuel Type</label><input type="text" class="form-control" id="vd_fuel_type"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="mileage">Mileage</label><input type="number" step="0.01" class="form-control" id="vd_mileage"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="plate_number">Plate Number</label><input type="text" class="form-control" id="vd_plate_number"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="vehicle_license_expiry">Vehicle License Expiry</label><input type="date" class="form-control" id="vd_license_expiry_date"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="color">Color</label><input type="text" class="form-control" id="vd_color"></div>
                            </div>
                          </div>
                        </div>

                  </div> <!-- End Vehicle Tab -->

                  <div class="tab-pane fade"
                      id="gold-pane"
                      role="tabpanel"
                      aria-labelledby="gold-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                          <div class="card-body px-0 pt-2">
                            <div class="row g-3">
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="gold_type">Gold Type</label><select class="form-select" id="gd_gold_type"></select></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="purity">Purity</label><select class="form-select" id="gd_purity"></select></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="weight">Weight</label><input type="number" step="0.0001" class="form-control" id="gd_weight" oninput="updateGoldValuation()"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="unit">Unit</label><input type="text" class="form-control" id="gd_unit" value="gram"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="market_price">Market Price</label><input type="number" step="0.0001" class="form-control" id="gd_market_price" readonly></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="cashback_per_gram">Cashback per Gram</label><input type="number" step="0.0001" class="form-control" id="gd_cashback_per_gram" value="0" readonly></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="purchase_weight">Purchase Weight</label><input type="number" step="0.0001" class="form-control" id="gd_purchase_weight"></div>
                              <div class="col-12"><small class="text-light" style="opacity:.75;" data-i18n="auto_calculated_from_gold_prices">Auto-calculated from Gold Prices module (SELL + USD/EGP).</small></div>
                            </div>
                          </div>
                        </div>

                  </div> <!-- End Gold Tab -->

                  <div class="tab-pane fade"
                      id="other-details-pane"
                      role="tabpanel"
                      aria-labelledby="other-details-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                          <div class="card-body px-0 pt-2">
                            <div class="row g-3">
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="category">Category</label><input type="text" class="form-control" id="od_category"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="manufacturer">Manufacturer</label><input type="text" class="form-control" id="od_manufacturer"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="model">Model</label><input type="text" class="form-control" id="od_model"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="serial_number">Serial Number</label><input type="text" class="form-control" id="od_serial_number"></div>
                              <div class="col-md-4"><label class="form-label text-light" data-i18n="warranty_expiry">Warranty Expiry</label><input type="date" class="form-control" id="od_warranty_expiry"></div>
                              <div class="col-md-12"><label class="form-label text-light" data-i18n="description">Description</label><textarea class="form-control" id="od_description" rows="2"></textarea></div>
                              <div class="col-md-12"><label class="form-label text-light" data-i18n="notes">Notes</label><textarea class="form-control" id="od_notes" rows="2"></textarea></div>
                            </div>
                          </div>
                        </div>

                  </div> <!-- End Other Details Tab -->

                  <div class="tab-pane fade"
                      id="photos-pane"
                      role="tabpanel"
                      aria-labelledby="photos-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                          <div class="card-body px-0 pt-2">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                              <h5 class="mb-0 fixed-assets-section-title" data-i18n="property_photos">Photo Gallery</h5>
                              <button type="button" id="btnUploadPropertyPhoto" class="btn btn-primary btn-sm">
                                <i class="bi bi-upload me-1"></i><span data-i18n="upload_photo">Upload Photo</span>
                              </button>
                            </div>
                            <input type="file" id="propertyPhotoInput" accept="image/*" multiple style="display:none;">
                            <div id="propertyPhotoGallery" class="row g-3"></div>
                          </div>
                        </div>

                  </div> <!-- End Photos Tab -->

                  <!-- 3. RENOVATION TAB PANE -->
                  <div class="tab-pane fade"
                      id="renovation-pane"
                      role="tabpanel"
                      aria-labelledby="renovation-tab">

                        <div class="card border-0 shadow-sm bg-transparent">
                            <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                                <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="renovation_history">Renovation History</h6>
                                <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#renovationCollapse">
                                    <i class="bi bi-chevron-down"></i>
                                </button>
                            </div>

                            <div class="collapse show" id="renovationCollapse">
                                <div class="card-body px-0 pt-2">
                                    <div id="renovationContainer" class="w-100"></div>
                                    <button type="button" class="btn btn-outline-primary btn-sm mt-2" onclick="addRenovationRow()" data-i18n="add_renovation">
                                        + Add Renovation
                                    </button>
                                </div>
                            </div>
                        </div>

                  </div> <!-- End Renovation Tab -->

                    <div class="tab-pane fade"
                      id="furniture-pane"
                      role="tabpanel"
                      aria-labelledby="furniture-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="furniture">Furniture</h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addFurnitureRow()" data-i18n="add_furniture">
                            + Add Furniture
                          </button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="furnitureContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Furniture Tab -->

                    <div class="tab-pane fade"
                      id="valuation-pane"
                      role="tabpanel"
                      aria-labelledby="valuation-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="valuation_history">Valuation History</h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addValuationRow()" data-i18n="add_valuation">
                            + Add Valuation
                          </button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="valuationContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Valuation Tab -->

                    <div class="tab-pane fade"
                      id="maintenance-pane"
                      role="tabpanel"
                      aria-labelledby="maintenance-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="maintenance">Maintenance</h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addMaintenanceRow()" data-i18n="add_maintenance">+ Add Maintenance</button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="maintenanceContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Maintenance Tab -->

                    <div class="tab-pane fade"
                      id="insurance-pane"
                      role="tabpanel"
                      aria-labelledby="insurance-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="insurance">Insurance</h6>
                          <button type="button" class="btn btn-outline-primary btn-sm" onclick="addInsuranceRow()" data-i18n="add_insurance">+ Add Insurance</button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div id="insuranceContainer" class="w-100"></div>
                        </div>
                      </div>

                    </div> <!-- End Insurance Tab -->

                    <div class="tab-pane fade"
                      id="mortgage-pane"
                      role="tabpanel"
                      aria-labelledby="mortgage-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="mortgage">Mortgage</h6>
                          <button type="button" class="btn btn-danger btn-sm" onclick="deleteMortgageDetails()" data-i18n="delete">Delete</button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div class="row g-3 mb-3">
                            <div class="col-md-6"><label class="form-label text-light" data-i18n="loan_amount">Loan Amount</label><input type="number" step="0.01" class="form-control" id="fa_loan_amount"></div>
                            <div class="col-md-6"><label class="form-label text-light" data-i18n="remaining_balance">Remaining Balance</label><input type="number" step="0.01" class="form-control" id="fa_remaining_balance" oninput="updateMortgageSummary()"></div>
                          </div>
                          <div class="row g-3 mb-3">
                            <div class="col-md-4"><label class="form-label text-light" data-i18n="monthly_installment">Monthly Installment</label><input type="number" step="0.01" class="form-control" id="fa_monthly_installment"></div>
                            <div class="col-md-4"><label class="form-label text-light" data-i18n="interest_rate">Interest Rate</label><input type="number" step="0.0001" class="form-control" id="fa_interest_rate"></div>
                            <div class="col-md-4"><label class="form-label text-light" data-i18n="net_equity">Net Equity</label><input type="number" step="0.01" class="form-control" id="fa_net_equity" readonly></div>
                          </div>
                          <div class="row g-3">
                            <div class="col-md-6"><label class="form-label text-light" data-i18n="start_date">Start Date</label><input type="date" class="form-control" id="fa_mortgage_start_date"></div>
                            <div class="col-md-6"><label class="form-label text-light" data-i18n="end_date">End Date</label><input type="date" class="form-control" id="fa_mortgage_end_date"></div>
                          </div>
                        </div>
                      </div>

                    </div> <!-- End Mortgage Tab -->

                    <div class="tab-pane fade"
                      id="rental-pane"
                      role="tabpanel"
                      aria-labelledby="rental-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-header d-flex justify-content-between align-items-center px-0 bg-transparent border-0">
                          <h6 class="mb-0 font-weight-bold fixed-assets-section-title" data-i18n="rental">Rental</h6>
                          <button type="button" class="btn btn-danger btn-sm" onclick="deleteRentalDetails()" data-i18n="delete">Delete</button>
                        </div>
                        <div class="card-body px-0 pt-2">
                          <div class="row g-3 mb-3">
                            <div class="col-md-4"><label class="form-label text-light" data-i18n="monthly_rent">Monthly Rent</label><input type="number" step="0.01" class="form-control" id="fa_monthly_rent" oninput="updateRentalSummary()"></div>
                            <div class="col-md-4"><label class="form-label text-light" data-i18n="annual_rent">Annual Rent</label><input type="number" step="0.01" class="form-control" id="fa_annual_rent" readonly></div>
                            <div class="col-md-4"><label class="form-label text-light" data-i18n="rental_yield">Rental Yield</label><input type="number" step="0.01" class="form-control" id="fa_rental_yield" readonly></div>
                          </div>
                          <div class="row g-3 mb-3">
                            <div class="col-md-4"><label class="form-label text-light" data-i18n="occupancy_rate">Occupancy Rate</label><input type="number" step="0.01" class="form-control" id="fa_occupancy_rate"></div>
                            <div class="col-md-4"><label class="form-label text-light" data-i18n="tenant_name_optional">Tenant Name (Optional)</label><input type="text" class="form-control" id="fa_tenant_name"></div>
                          </div>
                          <div class="row g-3 mb-3">
                            <div class="col-md-6"><label class="form-label text-light" data-i18n="contract_start">Contract Start</label><input type="date" class="form-control" id="fa_contract_start"></div>
                            <div class="col-md-6"><label class="form-label text-light" data-i18n="contract_end">Contract End</label><input type="date" class="form-control" id="fa_contract_end"></div>
                          </div>
                          <div class="row g-3">
                            <div class="col-md-12"><label class="form-label text-light" data-i18n="rental_notes">Rental Notes</label><textarea class="form-control" id="fa_rental_notes" rows="3"></textarea></div>
                          </div>
                        </div>
                      </div>

                    </div> <!-- End Rental Tab -->

                    <div class="tab-pane fade"
                      id="sale-pane"
                      role="tabpanel"
                      aria-labelledby="sale-tab">

                      <div class="card border-0 shadow-sm bg-transparent">
                        <div class="card-body px-0 pt-2">
                          <div class="row g-3 mb-3">
                            <div class="col-md-6">
                              <label class="form-label text-light" data-i18n="sale_date">Sale Date</label>
                              <input type="date" class="form-control" id="fa_sale_date">
                            </div>
                            <div class="col-md-6">
                              <label class="form-label text-light" data-i18n="sale_price_egp">Sale Price (EGP)</label>
                              <input type="number" step="0.01" class="form-control" id="fa_sale_price">
                            </div>
                          </div>

                          <div class="row g-3 mb-3">
                            <div class="col-md-6">
                              <label class="form-label text-light" data-i18n="selling_expenses_egp">Selling Expenses (EGP)</label>
                              <input type="number" step="0.01" class="form-control" id="fa_selling_expenses">
                            </div>
                            <div class="col-md-6">
                              <label class="form-label text-light" data-i18n="net_sale_amount">Net Sale Amount</label>
                              <input type="number" step="0.01" class="form-control" id="fa_net_sale_amount" readonly>
                            </div>
                          </div>

                          <div class="row g-3 mb-3">
                            <div class="col-md-4">
                              <label class="form-label text-light" data-i18n="currency">Currency</label>
                              <select class="form-select" id="fa_deposit_currency"></select>
                            </div>
                            <div class="col-md-4">
                              <label class="form-label text-light" data-i18n="deposit_method">Deposit Method</label>
                              <select class="form-select" id="fa_deposit_method" onchange="toggleSaleDepositBankField()"></select>
                            </div>
                            <div class="col-md-4" id="faDepositBankWrap">
                              <label class="form-label text-light" data-i18n="bank">Bank</label>
                              <select class="form-select" id="fa_deposit_bank"></select>
                            </div>
                          </div>

                          <div class="row g-3">
                            <div class="col-md-12">
                              <label class="form-label text-light" data-i18n="sale_notes">Sale Notes</label>
                              <textarea class="form-control" id="fa_sale_notes" rows="3"></textarea>
                            </div>
                          </div>
                        </div>
                      </div>

                    </div> <!-- End Sale Tab -->

                    <div class="tab-pane fade"
                      id="documents-pane"
                      role="tabpanel"
                      aria-labelledby="documents-tab">

                      <div id="fixedAssetDocumentManagerContainer"></div>

                    </div> <!-- End Documents Tab -->

              </div> <!-- End Tab Content -->

          </form>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="saveFixedAsset(${assetId})" data-i18n="save">Save</button>
        </div>
    `;

  showModal(html);
  applyTranslations();
  await populateGoldSettingsDropdowns();
  const propertyTab = document.getElementById("property-tab");
  const statusField = document.getElementById("fa_status");
  const salePriceField = document.getElementById("fa_sale_price");
  const sellingExpensesField = document.getElementById("fa_selling_expenses");
  const currentValueField = document.getElementById("fa_current_value");
  const monthlyRentField = document.getElementById("fa_monthly_rent");
  const remainingBalanceField = document.getElementById("fa_remaining_balance");
  const assetTypeField = document.getElementById("fa_type");
  const goldPurityField = document.getElementById("gd_purity");
  const goldUnitField = document.getElementById("gd_unit");

  if (statusField) {
    statusField.addEventListener("change", toggleSaleTabVisibility);
  }

  if (salePriceField) {
    salePriceField.addEventListener("input", updateNetSaleAmount);
  }

  if (sellingExpensesField) {
    sellingExpensesField.addEventListener("input", updateNetSaleAmount);
  }

  if (currentValueField) {
    currentValueField.addEventListener("input", () => {
      updateMortgageSummary();
      updateRentalSummary();
    });
  }

  if (monthlyRentField) {
    monthlyRentField.addEventListener("input", updateRentalSummary);
  }

  if (remainingBalanceField) {
    remainingBalanceField.addEventListener("input", updateMortgageSummary);
  }

  if (assetTypeField) {
    assetTypeField.addEventListener("change", toggleRealEstateDependentTabs);
  }

  if (goldPurityField) {
    goldPurityField.addEventListener("change", updateGoldValuation);
  }

  if (goldUnitField) {
    goldUnitField.addEventListener("input", updateGoldValuation);
  }

  if (window.DocumentManager) {
    window.DocumentManager.init({
      containerId: "fixedAssetDocumentManagerContainer",
      parentType: "fixed_asset",
      parentId: assetId,
      disabledMessage: t("documents_save_first", "Save this record first to manage documents."),
    });
  }

  await loadFixedAssetSyncDropdownData();
  resetPurchasePaymentsForm();
  addPurchasePaymentRow();
  propertyPhotos = [];
  renderPropertyPhotoGallery();
  ["renovationContainer", "furnitureContainer", "valuationContainer", "maintenanceContainer", "insuranceContainer"].forEach((id) => {
    const container = document.getElementById(id);
    if (container) container.innerHTML = "";
  });
  resetSaleForm();
  toggleSaleDepositBankField();
  resetMortgageForm();
  resetRentalForm();
  toggleSaleTabVisibility();
  toggleRealEstateDependentTabs();

  propertyTab.addEventListener("shown.bs.tab", function () {
    if (propertyMap) {
      setTimeout(() => {
        propertyMap.invalidateSize();
      }, 50);
    }
  });

  document
    .getElementById("btnLocateProperty")
    .addEventListener("click", locatePropertyOnMap);
  const refreshValuationButton = document.getElementById("btnRefreshPropertyValuation");
  if (refreshValuationButton) {
    refreshValuationButton.addEventListener("click", refreshPropertyValuation);
  }
  initializePropertyMap();
  if (isEdit) {
    await loadFixedAsset(assetId);
  } else {
    maybeRefreshPurchaseUsdRateOnLoad();
  }
}

function populatePropertyValuationFields(realEstate = {}) {
  const estimateField = document.getElementById("re_last_estimated_market_price");
  const dateField = document.getElementById("re_last_valuation_date");
  const providerField = document.getElementById("re_valuation_provider");

  if (estimateField) {
    const value = realEstate?.last_estimated_market_price;
    estimateField.value = value !== null && value !== undefined && value !== "" ? value : "";
  }
  if (dateField) {
    dateField.value = realEstate?.last_valuation_date || "";
  }
  if (providerField) {
    providerField.value = realEstate?.valuation_provider || "";
  }
}

async function refreshPropertyValuation() {
  if (!currentEditingAssetId) {
    showToast(t("save_asset_before_valuation", "Save this asset first before refreshing valuation."), "warning");
    return;
  }

  try {
    const response = await fetch(`/api/fixed-assets/${currentEditingAssetId}/valuation/refresh/`, {
      method: "POST",
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || t("error_refreshing_property_valuation", "Failed to refresh property valuation."));
    }

    const asset = payload.asset || {};
    const realEstate = asset.real_estate || {};
    document.getElementById("fa_current_value").value = asset.current_market_value || 0;
    document.getElementById("fa_last_valuation_date").value = asset.last_valuation_date || "";
    document.getElementById("fa_val_source").value = asset.valuation_source || "Manual";
    populatePropertyValuationFields(realEstate);

    if (payload.updated) {
      showToast(t("property_valuation_refreshed", "Property valuation refreshed."), "success");
    } else {
      showToast(t("property_valuation_unavailable", "No automatic valuation was available for this property."), "warning");
    }
  } catch (error) {
    showToast(error.message || t("error_refreshing_property_valuation", "Failed to refresh property valuation."), "error");
  }
}

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
        : '',
      realEstate.water
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-droplet-fill me-1"></i><span data-i18n="water">Water</span></span>'
        : '',
      realEstate.gas
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-fire me-1"></i><span data-i18n="gas">Gas</span></span>'
        : '',
    ].filter(Boolean).join('');
    const featuresBadges = [
      realEstate.elevator
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-building me-1"></i><span data-i18n="elevator">Elevator</span></span>'
        : '',
      realEstate.garage
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-car-front-fill me-1"></i><span data-i18n="garage">Garage</span></span>'
        : '',
      realEstate.has_land_share
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-tree-fill me-1"></i><span data-i18n="has_land_share">Land Share</span></span>'
        : '',
      realEstate.licensed
        ? '<span class="badge rounded-pill asset-info-pill"><i class="bi bi-shield-lock-fill me-1"></i><span data-i18n="licensed">Licensed</span></span>'
        : '',
    ].filter(Boolean).join('');
    const gainValue = (asset.current_market_value || 0) - (asset.purchase_price || 0);
    const gainClass = gainValue >= 0 ? 'text-success' : 'text-danger';
    let assetViewMap = null;

    if (!isRealEstateAssetType(asset.asset_type)) {
      const coreTabLabel = isVehicleAssetType(asset.asset_type)
        ? t("vehicle", "Vehicle")
        : isGoldAssetType(asset.asset_type)
          ? t("gold_details", "Gold Details")
          : t("details", "Details");

      const coreTabPane = isVehicleAssetType(asset.asset_type)
        ? `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="brand">Brand</span><span class="value">${vehicleDetails.brand || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="model">Model</span><span class="value">${vehicleDetails.model || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="year">Year</span><span class="value">${vehicleDetails.year || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="vin">VIN</span><span class="value">${vehicleDetails.vin || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="engine">Engine</span><span class="value">${vehicleDetails.engine || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="transmission">Transmission</span><span class="value">${vehicleDetails.transmission || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="fuel_type">Fuel Type</span><span class="value">${vehicleDetails.fuel_type || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="mileage">Mileage</span><span class="value">${vehicleDetails.mileage || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="plate_number">Plate Number</span><span class="value">${vehicleDetails.plate_number || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="color">Color</span><span class="value">${vehicleDetails.color || '-'}</span></div></div>
              </div>
            </div>
          </div>
        `
        : isGoldAssetType(asset.asset_type)
          ? `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="gold_type">Gold Type</span><span class="value">${goldDetails.gold_type || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="purity">Purity</span><span class="value">${goldDetails.purity || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="weight">Weight</span><span class="value">${goldDetails.weight || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="unit">Unit</span><span class="value">${goldDetails.unit || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="market_price">Market Price</span><span class="value">${fmt(goldDetails.market_price)}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_weight">Purchase Weight</span><span class="value">${goldDetails.purchase_weight || '-'}</span></div></div>
              </div>
            </div>
          </div>
        `
          : `
          <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
            <div class="card-body p-4">
              <div class="row row-cols-1 row-cols-md-2 g-3">
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="category">Category</span><span class="value">${otherDetails.category || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="manufacturer">Manufacturer</span><span class="value">${otherDetails.manufacturer || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="model">Model</span><span class="value">${otherDetails.model || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="serial_number">Serial Number</span><span class="value">${otherDetails.serial_number || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="warranty_expiry">Warranty Expiry</span><span class="value">${otherDetails.warranty_expiry || '-'}</span></div></div>
                <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${otherDetails.notes || '-'}</span></div></div>
                <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="description">Description</span><span class="value">${otherDetails.description || '-'}</span></div></div>
              </div>
            </div>
          </div>
        `;

      const extraVehicleTabs = isVehicleAssetType(asset.asset_type)
        ? `
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-maintenance-tab" data-bs-toggle="tab" data-bs-target="#asset-maintenance-pane" type="button" role="tab" data-i18n="maintenance">Maintenance</button>
          </li>
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-insurance-tab" data-bs-toggle="tab" data-bs-target="#asset-insurance-pane" type="button" role="tab" data-i18n="insurance">Insurance</button>
          </li>
        `
        : "";

      const extraVehiclePanes = isVehicleAssetType(asset.asset_type)
        ? `
          <div class="tab-pane fade" id="asset-maintenance-pane" role="tabpanel" aria-labelledby="asset-maintenance-tab">
            <div class="row g-3">
              ${(maintenance.length ? maintenance : [{ date: "-", type: "-", cost: 0, notes: "-" }]).map((item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="date">Date</div><div>${item.date || '-'}</div></div><div><div class="small" data-i18n="type">Type</div><div>${item.type || '-'}</div></div><div><div class="small" data-i18n="cost">Cost</div><div>${fmt(item.cost)}</div></div><div><div class="small" data-i18n="notes">Notes</div><div>${item.notes || '-'}</div></div></div></div></div>
              `).join("")}
            </div>
          </div>
          <div class="tab-pane fade" id="asset-insurance-pane" role="tabpanel" aria-labelledby="asset-insurance-tab">
            <div class="row g-3">
              ${(insurance.length ? insurance : [{ company: "-", policy_number: "-", expiry_date: "-", premium: 0 }]).map((item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="company">Company</div><div>${item.company || '-'}</div></div><div><div class="small" data-i18n="policy_number">Policy Number</div><div>${item.policy_number || '-'}</div></div><div><div class="small" data-i18n="expiry_date">Expiry Date</div><div>${item.expiry_date || '-'}</div></div><div><div class="small" data-i18n="premium">Premium</div><div>${fmt(item.premium)}</div></div></div></div></div>
              `).join("")}
            </div>
          </div>
        `
        : "";

      const extraValuationTab = !isGoldAssetType(asset.asset_type)
        ? `
          <li class="nav-item" role="presentation">
            <button class="nav-link" id="asset-valuation-tab" data-bs-toggle="tab" data-bs-target="#asset-valuation-pane" type="button" role="tab" data-i18n="valuation_history">Valuation History</button>
          </li>
        `
        : "";

      const extraValuationPane = !isGoldAssetType(asset.asset_type)
        ? `
          <div class="tab-pane fade" id="asset-valuation-pane" role="tabpanel" aria-labelledby="asset-valuation-tab">
            <div class="row g-3">
              ${(valuationHistory.length ? valuationHistory : [{ valuation_date: "-", market_value: 0, valuation_source: "-", notes: "-" }]).map((item) => `
                <div class="col-12"><div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-3 d-flex flex-wrap gap-3 justify-content-between"><div><div class="small" data-i18n="date">Date</div><div>${item.valuation_date || '-'}</div></div><div><div class="small" data-i18n="current_market_value">Market Value</div><div>${fmt(item.market_value)}</div></div><div><div class="small" data-i18n="valuation_source">Valuation Source</div><div>${item.valuation_source || '-'}</div></div><div><div class="small" data-i18n="notes">Notes</div><div>${item.notes || '-'}</div></div></div></div></div>
              `).join("")}
            </div>
          </div>
        `
        : "";

      const html = `
      <div class="modal-header border-0 pb-0">
          <h5 class="modal-title fixed-assets-heading" data-i18n="asset_details">Asset Details</h5>
          <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
      </div>
      <div class="modal-body asset-modal-body p-0">
        <div class="p-4">
          <div class="asset-detail-header mb-4">
            <h3 class="asset-title mb-1 fixed-assets-heading">${asset.name || '-'}</h3>
            <span class="badge rounded-pill asset-type-badge" data-i18n="${fixedAssetTypeToI18nKey(asset.asset_type)}">${asset.asset_type || '-'}</span>
          </div>
          <ul class="nav nav-pills nav-fill mb-4 asset-detail-tabs" role="tablist">
            <li class="nav-item" role="presentation"><button class="nav-link active" id="asset-general-tab" data-bs-toggle="tab" data-bs-target="#asset-general-pane" type="button" role="tab" data-i18n="general">General</button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-core-tab" data-bs-toggle="tab" data-bs-target="#asset-core-pane" type="button" role="tab">${coreTabLabel}</button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-photos-tab" data-bs-toggle="tab" data-bs-target="#asset-photos-pane" type="button" role="tab" data-i18n="photos">Photos</button></li>
            ${extraVehicleTabs}
            ${extraValuationTab}
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-sale-tab" data-bs-toggle="tab" data-bs-target="#asset-sale-pane" type="button" role="tab" data-i18n="sale">Sale</button></li>
          </ul>
          <div class="tab-content" id="assetDetailsTabsContent">
            <div class="tab-pane fade show active" id="asset-general-pane" role="tabpanel" aria-labelledby="asset-general-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                <div class="row g-3">
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_price_egp">Purchase Price</span><span class="value">${fmt(asset.purchase_price)}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="current_market_value">Current Market Value</span><span class="value ${gainClass}">${fmt(asset.current_market_value)}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_date">Purchase Date</span><span class="value">${asset.purchase_date || '-'}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="gain_loss">Gain / Loss</span><span class="value ${gainClass}">${fmt(gainValue)}</span></div></div>
                  <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${asset.notes || '-'}</span></div></div>
                </div>
              </div></div>
            </div>
            <div class="tab-pane fade" id="asset-core-pane" role="tabpanel" aria-labelledby="asset-core-tab">${coreTabPane}</div>
            <div class="tab-pane fade" id="asset-photos-pane" role="tabpanel" aria-labelledby="asset-photos-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                <div id="assetMainPhotoContainer" class="asset-main-photo-container mb-3">
                  ${photos.length ? `<img id="assetMainPhoto" src="${photos[0].url}" alt="Asset photo" class="img-fluid" style="max-height:100%;max-width:100%;cursor:pointer;" />` : `<div class="text-center" data-i18n="no_property_photos">No photos available</div>`}
                </div>
                <div class="asset-photo-grid">${photos.length ? photos.slice(1).map((photo, index) => `<button type="button" class="btn btn-sm asset-photo-thumbnail p-0" data-url="${photo.url}" aria-label="Photo ${index + 2}"><img src="${photo.url}" alt="Thumbnail ${index + 2}" /></button>`).join("") : ""}</div>
              </div></div>
            </div>
            ${extraVehiclePanes}
            ${extraValuationPane}
            <div class="tab-pane fade" id="asset-sale-pane" role="tabpanel" aria-labelledby="asset-sale-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                ${sale ? `<div class="row g-3"><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="sale_date">Sale Date</span><span class="value">${sale.sale_date || '-'}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="sale_price_egp">Sale Price</span><span class="value">${fmt(sale.sale_price)}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="selling_expenses_egp">Selling Expenses</span><span class="value">${fmt(sale.selling_expenses)}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="net_sale_amount">Net Sale Amount</span><span class="value">${fmt(sale.net_sale_amount)}</span></div></div><div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${sale.notes || '-'}</span></div></div></div>` : `<div class="text-center" data-i18n="no_data">No data available</div>`}
              </div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer"><button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="close">Close</button></div>
      <div id="assetPhotoOverlay" class="position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-90 d-none" style="z-index:2000;"><div class="d-flex h-100 align-items-center justify-content-center"><img id="assetFullscreenImage" src="" alt="Fullscreen asset photo" class="img-fluid rounded" style="max-height:90%; max-width:90%;" /></div></div>
      `;

      showModal(html);
      applyTranslations();

      const mainPhoto = document.getElementById("assetMainPhoto");
      const photoOverlay = document.getElementById("assetPhotoOverlay");
      const fullscreenImage = document.getElementById("assetFullscreenImage");
      if (mainPhoto) {
        mainPhoto.addEventListener("click", () => {
          fullscreenImage.src = mainPhoto.src;
          photoOverlay?.classList.remove("d-none");
        });
      }
      photoOverlay?.addEventListener("click", () => {
        photoOverlay.classList.add("d-none");
        fullscreenImage.src = "";
      });

      const assetPhotoThumbnails = document.querySelectorAll(".asset-photo-thumbnail");
      assetPhotoThumbnails.forEach((thumb) => {
        thumb.addEventListener("click", (e) => {
          const url = e.currentTarget.dataset.url;
          const mainImg = document.getElementById("assetMainPhoto");
          if (mainImg) mainImg.src = url;
          assetPhotoThumbnails.forEach((item) => item.classList.remove("active"));
          e.currentTarget.classList.add("active");
        });
      });
      hideLoading();
      return;
    }

    const html = `
    <div class="modal-header border-0 pb-0">
        <h5 class="modal-title fixed-assets-heading" data-i18n="asset_details">Asset Details</h5>
        <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
    </div>

    <div class="modal-body asset-modal-body p-0">
        <div class="p-4">
            <div class="asset-detail-header mb-4">
                <div class="d-flex flex-column flex-lg-row gap-3 align-items-start">
                    <div class="asset-header-icon d-flex align-items-center justify-content-center">
                        <i class="bi bi-building"></i>
                    </div>
                    <div class="flex-fill">
                        <div class="d-flex flex-column flex-sm-row justify-content-between gap-3 align-items-start align-items-sm-center">
                            <div>
                                <h3 class="asset-title mb-1 fixed-assets-heading">${asset.name || '-'}</h3>
                                <span class="badge rounded-pill asset-type-badge" data-i18n="${fixedAssetTypeToI18nKey(asset.asset_type)}">${asset.asset_type || '-'}</span>
                            </div>
                            <div class="text-sm-end">
                                <div class="small asset-label" data-i18n="current_market_value">Current Market Value</div>
                                <div class="asset-value-large ${gainClass}">${fmt(asset.current_market_value)}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-4 g-3 mb-4">
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="purchase_price_egp">Purchase Price</div>
                        <div class="asset-summary-value">${fmt(asset.purchase_price)}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="purchase_date">Purchase Date</div>
                        <div class="asset-summary-value">${asset.purchase_date || '-'}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="gain_loss">Gain / Loss</div>
                        <div class="asset-summary-value ${gainClass}">${fmt(gainValue)}</div>
                    </div>
                </div>
                <div class="col">
                    <div class="asset-summary-card h-100">
                        <div class="asset-summary-label" data-i18n="last_valuation_date">Last Valuation Date</div>
                        <div class="asset-summary-value">${asset.last_valuation_date || '-'}</div>
                    </div>
                </div>
                ${mortgage ? `
                <div class="col">
                  <div class="asset-summary-card h-100">
                    <div class="asset-summary-label" data-i18n="net_equity">Net Equity</div>
                    <div class="asset-summary-value">${fmt(mortgage.net_equity)}</div>
                  </div>
                </div>
                ` : ''}
                ${rental ? `
                <div class="col">
                  <div class="asset-summary-card h-100">
                    <div class="asset-summary-label" data-i18n="rental_yield">Rental Yield</div>
                    <div class="asset-summary-value">${fmtpresent(rental.rental_yield)}%</div>
                  </div>
                </div>
                ` : ''}
            </div>

            <ul class="nav nav-pills nav-fill mb-4 asset-detail-tabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="asset-general-tab" data-bs-toggle="tab" data-bs-target="#asset-general-pane" type="button" role="tab" aria-controls="asset-general-pane" aria-selected="true" data-i18n="general">General</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-property-tab" data-bs-toggle="tab" data-bs-target="#asset-property-pane" type="button" role="tab" aria-controls="asset-property-pane" aria-selected="false" data-i18n="property">Property</button>
                </li>
              <li class="nav-item" role="presentation">
                <button class="nav-link" id="asset-photos-tab" data-bs-toggle="tab" data-bs-target="#asset-photos-pane" type="button" role="tab" aria-controls="asset-photos-pane" aria-selected="false" data-i18n="photos">Photos</button>
              </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="asset-renovation-tab" data-bs-toggle="tab" data-bs-target="#asset-renovation-pane" type="button" role="tab" aria-controls="asset-renovation-pane" aria-selected="false" data-i18n="renovations">Renovations</button>
                </li>
                ${furniture.length ? `
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-furniture-tab" data-bs-toggle="tab" data-bs-target="#asset-furniture-pane" type="button" role="tab" aria-controls="asset-furniture-pane" aria-selected="false" data-i18n="furniture">Furniture</button>
                </li>
                ` : ''}
                ${valuationHistory.length ? `
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-valuation-tab" data-bs-toggle="tab" data-bs-target="#asset-valuation-pane" type="button" role="tab" aria-controls="asset-valuation-pane" aria-selected="false" data-i18n="valuation_history">Valuation History</button>
                </li>
                ` : ''}
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-mortgage-tab" data-bs-toggle="tab" data-bs-target="#asset-mortgage-pane" type="button" role="tab" aria-controls="asset-mortgage-pane" aria-selected="false" data-i18n="mortgage">Mortgage</button>
                </li>
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-rental-tab" data-bs-toggle="tab" data-bs-target="#asset-rental-pane" type="button" role="tab" aria-controls="asset-rental-pane" aria-selected="false" data-i18n="rental">Rental</button>
                </li>
                <li class="nav-item" role="presentation">
                  <button class="nav-link" id="asset-sale-tab" data-bs-toggle="tab" data-bs-target="#asset-sale-pane" type="button" role="tab" aria-controls="asset-sale-pane" aria-selected="false" data-i18n="sale">Sale</button>
                </li>
            </ul>

            <div class="tab-content" id="assetDetailsTabsContent">
                <div class="tab-pane fade show active" id="asset-general-pane" role="tabpanel" aria-labelledby="asset-general-tab">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="general_information">General Information</h6>
                                                          
                                    <div class="row mb-2"><div class="col-5 fixed-assets-section-title" data-i18n="asset_type">Asset Type</div><div class="col-7">${asset.asset_type || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5 fixed-assets-section-title" data-i18n="asset_name">Asset Name</div><div class="col-7">${asset.name || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_date">Purchase Date</div><div class="col-7">${asset.purchase_date || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="valuation_source">Valuation Source</div><div class="col-7">${asset.valuation_source || '-'}</div></div>
                                    <div class="row"><div class="col-5" data-i18n="notes">Notes</div><div class="col-7">${asset.notes || '-'}</div></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="valuation_summary">Valuation Summary</h6>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_price_egp">Purchase Price</div><div class="col-7 fw-bold">${fmt(asset.purchase_price)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="purchase_price_usd">Purchase Price (USD)</div><div class="col-7 fw-bold">${fmt(asset.purchase_price_usd)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="current_market_value">Current Market Value</div><div class="col-7 fw-bold">${fmt(asset.current_market_value)}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="last_valuation_date">Last Valuation Date</div><div class="col-7">${asset.last_valuation_date || '-'}</div></div>
                                    <div class="row mb-2"><div class="col-5" data-i18n="gain_loss">Gain (EGP)</div><div class="col-7 fw-bold ${gainClass}">${fmt(gainValue)}</div></div>
                                    <div class="row"><div class="col-5" data-i18n="gain_percent">Gain (%)</div><div class="col-7 fw-bold ${gainClass}">${asset.purchase_price ? fmtpresent((gainValue / asset.purchase_price) * 100) + '%' : '-'}</div></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="asset-property-pane" role="tabpanel" aria-labelledby="asset-property-tab">
                    <div class="row g-3">
                        <div class="col-xl-7">
                            <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                <div class="card-body p-4">
                                    <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="property_details">Property Details</h6>
                                    <div class="row row-cols-1 row-cols-sm-2 row-cols-xl-3 g-3">
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="country">Country</span><span class="value">${asset.real_estate?.country || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="governorate">Governorate</span><span class="value">${asset.real_estate?.governorate || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="city">City</span><span class="value">${asset.real_estate?.city || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="district">District</span><span class="value">${asset.real_estate?.district || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="address">Address</span><span class="value">${asset.real_estate?.address || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="apt_area">Property Area</span><span class="value">${asset.real_estate?.apartment_area || '-'} m²</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="land_area">Land Area</span><span class="value">${asset.real_estate?.land_area || '-'} m²</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="rooms">Bedrooms</span><span class="value">${asset.real_estate?.rooms || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="bathrooms">Bathrooms</span><span class="value">${asset.real_estate?.bathrooms || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="floor">Floor Number</span><span class="value">${asset.real_estate?.floor || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="building_floors">Total Building Floors</span><span class="value">${asset.real_estate?.building_floors || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="building_year">Construction Year</span><span class="value">${asset.real_estate?.building_year || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="facades">Facade</span><span class="value">${asset.real_estate?.facades || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="furnished_status">Furnished Status</span><span class="value">${asset.real_estate?.furnished_status || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="finishing_level">Finishing Level</span><span class="value">${asset.real_estate?.finishing_level || '-'}</span></div></div>
                                        <div class="col"><div class="asset-attribute-row"><span class="label" data-i18n="land_share">Land Share</span><span class="value">${asset.real_estate?.land_share || '-'}</span></div></div>
                                    </div>
                                    <div class="asset-attribute-row mt-3"><span class="label" data-i18n="description">Description</span><span class="value">${asset.real_estate?.description || '-'}</span></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-xl-5">
                            <div class="row g-3">
                                <div class="col-12">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="location">Location</h6>
                                            <div id="assetPropertyMap" class="asset-main-photo-container" style="height:280px;"></div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="utilities">Utilities</h6>
                                            <div class="d-flex flex-wrap gap-2">
                                              ${utilitiesBadges || `<span class="small" style="color:var(--text-secondary);" data-i18n="no_data">No data available</span>`}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                                        <div class="card-body p-4">
                                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="features">Features</h6>
                                            <div class="d-flex flex-wrap gap-2">
                                              ${featuresBadges || `<span class="small" style="color:var(--text-secondary);" data-i18n="no_data">No data available</span>`}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="asset-photos-pane" role="tabpanel" aria-labelledby="asset-photos-tab">
                  <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                    <div class="card-body p-4">
                      <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="property_photos">Photo Gallery</h6>
                      <div id="assetMainPhotoContainer" class="asset-main-photo-container mb-3" style="justify-content:center;">
                        ${photos.length ? `<img id="assetMainPhoto" src="${photos[0].url}" alt="Asset photo" class="img-fluid" style="max-height:100%;max-width:100%;cursor:pointer;" />` : `<div class="text-center" data-i18n="no_property_photos">No photos available</div>`}
                      </div>
                      <div class="asset-photo-grid">
                        ${photos.length ? photos.slice(1).map((photo, index) => `
                          <button type="button" class="btn btn-sm asset-photo-thumbnail p-0" data-url="${photo.url}" aria-label="Photo ${index + 2}">
                            <img src="${photo.url}" alt="Thumbnail ${index + 2}" />
                          </button>
                        `).join('') : ''}
                      </div>
                    </div>
                  </div>
                </div>
                <div class="tab-pane fade" id="asset-renovation-pane" role="tabpanel" aria-labelledby="asset-renovation-tab">
                    <div class="row g-3">
                        ${renovations.length ? renovations.map((r) => `
                            <div class="col-12">
                                <div class="asset-renovation-card">
                                    <div class="d-flex flex-column flex-md-row justify-content-between gap-3">
                                        <div>
                                            <div class="small mb-2" data-i18n="date">Date</div>
                                            <div class="fw-semibold">${r.date || '-'}</div>
                                            <div class="small mt-2" data-i18n="category">Category</div>
                                            <div>${r.category || '-'}</div>
                                        </div>
                                        <div class="text-md-end">
                                            <div class="small mb-2" data-i18n="amount_usd">Amount USD</div>
                                            <div class="fw-semibold">${fmt(r.amount_usd)}</div>
                                            <div class="small mt-3" data-i18n="amount_egp">Amount</div>
                                            <div class="fw-semibold">${fmt(r.amount_egp)}</div>
                                        </div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="description">Description</div>
                                        <div>${r.description || '-'}</div>
                                    </div>
                                    <div class="mt-3">
                                        <div class="small mb-1" data-i18n="notes">Notes</div>
                                        <div>${r.notes || '-'}</div>
                                    </div>
                                </div>
                            </div>
                        `).join('') : `
                            <div class="col-12">
                                <div class="text-center py-5" data-i18n="no_renovations">No renovations registered.</div>
                            </div>
                        `}
                        ${renovations.length ? `
                        <div class="col-12">
                            <div class="asset-renovation-card asset-renovation-summary" style="padding: 16px;">
                                <div class="d-flex flex-column gap-2" style="width: 100%;">
                                    
                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="total_renovation_cost_usd">Total Renovation Cost USD</div>
                                        <div class="text-end fw-semibold">
                                            $${fmt(renovations.reduce((sum, r) => sum + (parseFloat(r.amount_usd) || 0), 0))}
                                        </div>
                                    </div>

                                    <div class="d-flex justify-content-between align-items-center w-100">
                                        <div class="fw-semibold" data-i18n="amount_egp">Amount</div>
                                        <div class="text-end fw-semibold">
                                            ${fmt(renovations.reduce((sum, r) => sum + (parseFloat(r.amount_egp) || 0), 0))} <span data-i18n="EGP">EGP</span>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                  ${furniture.length ? `
                  <div class="tab-pane fade" id="asset-furniture-pane" role="tabpanel" aria-labelledby="asset-furniture-tab">
                    <div class="row g-3">
                      ${furniture.map((item) => `
                        <div class="col-md-6">
                          <div class="asset-renovation-card">
                            <div class="d-flex justify-content-between gap-3">
                              <div>
                                <div class="small mb-1" data-i18n="asset_name">Name</div>
                                <div class="fw-semibold">${item.name || '-'}</div>
                              </div>
                              <div class="text-end">
                                <div class="small mb-1" data-i18n="amount_egp">Amount</div>
                                <div class="fw-semibold">${fmt(item.amount_egp)}</div>
                              </div>
                            </div>
                            <div class="mt-3 d-flex justify-content-between gap-3">
                              <div><span class="small" data-i18n="category">Category</span><div>${item.category || '-'}</div></div>
                              <div><span class="small" data-i18n="quantity">Quantity</span><div>${item.quantity || '-'}</div></div>
                              <div><span class="small" data-i18n="purchase_date">Purchase Date</span><div>${item.purchase_date || '-'}</div></div>
                            </div>
                            <div class="mt-3"><div class="small mb-1" data-i18n="notes">Notes</div><div>${item.notes || '-'}</div></div>
                          </div>
                        </div>
                      `).join('')}
                    </div>
                  </div>
                  ` : ''}
                  ${valuationHistory.length ? `
                  <div class="tab-pane fade" id="asset-valuation-pane" role="tabpanel" aria-labelledby="asset-valuation-tab">
                    <div class="row g-3">
                      ${valuationHistory.map((item) => `
                        <div class="col-12">
                          <div class="asset-renovation-card">
                            <div class="d-flex flex-column flex-md-row justify-content-between gap-3">
                              <div>
                                <div class="small mb-1" data-i18n="date">Date</div>
                                <div class="fw-semibold">${item.valuation_date || '-'}</div>
                              </div>
                              <div>
                                <div class="small mb-1" data-i18n="valuation_source">Valuation Source</div>
                                <div>${item.valuation_source || '-'}</div>
                              </div>
                              <div class="text-md-end">
                                <div class="small mb-1" data-i18n="current_market_value">Current Market Value</div>
                                <div class="fw-semibold">${fmt(item.market_value)}</div>
                              </div>
                            </div>
                            <div class="mt-3"><div class="small mb-1" data-i18n="notes">Notes</div><div>${item.notes || '-'}</div></div>
                          </div>
                        </div>
                      `).join('')}
                    </div>
                  </div>
                  ` : ''}
                  <div class="tab-pane fade" id="asset-mortgage-pane" role="tabpanel" aria-labelledby="asset-mortgage-tab">
                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                      <div class="card-body p-4">
                        ${mortgage ? `
                          <div class="row g-3">
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="loan_amount">Loan Amount</span><span class="value">${fmt(mortgage.loan_amount)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="remaining_balance">Remaining Balance</span><span class="value">${fmt(mortgage.remaining_balance)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="monthly_installment">Monthly Installment</span><span class="value">${fmt(mortgage.monthly_installment)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="interest_rate">Interest Rate</span><span class="value">${fmtpresent(mortgage.interest_rate)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="start_date">Start Date</span><span class="value">${mortgage.start_date || '-'}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="end_date">End Date</span><span class="value">${mortgage.end_date || '-'}</span></div></div>
                            <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="net_equity">Net Equity</span><span class="value">${fmt(mortgage.net_equity)}</span></div></div>
                          </div>
                        ` : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`}
                      </div>
                    </div>
                  </div>

                  <div class="tab-pane fade" id="asset-rental-pane" role="tabpanel" aria-labelledby="asset-rental-tab">
                    <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                      <div class="card-body p-4">
                        ${rental ? `
                          <div class="row g-3">
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="monthly_rent">Monthly Rent</span><span class="value">${fmt(rental.monthly_rent)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="annual_rent">Annual Rent</span><span class="value">${fmt(rental.annual_rent)}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="occupancy_rate">Occupancy Rate</span><span class="value">${fmtpresent(rental.occupancy_rate)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="rental_yield">Rental Yield</span><span class="value">${fmtpresent(rental.rental_yield)}%</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="tenant_name_optional">Tenant Name</span><span class="value">${rental.tenant_name || '-'}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="contract_start">Contract Start</span><span class="value">${rental.contract_start || '-'}</span></div></div>
                            <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="contract_end">Contract End</span><span class="value">${rental.contract_end || '-'}</span></div></div>
                            <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${rental.notes || '-'}</span></div></div>
                          </div>
                        ` : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`}
                      </div>
                    </div>
                  </div>

                  <div class="tab-pane fade" id="asset-sale-pane" role="tabpanel" aria-labelledby="asset-sale-tab">
                    <div class="row g-3">
                      <div class="col-md-6">
                        <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                          <div class="card-body p-4">
                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="sale_information">Sale Information</h6>
                            ${sale ? `
                              <div class="row mb-2"><div class="col-5" data-i18n="sale_date">Sale Date</div><div class="col-7">${sale.sale_date || '-'}</div></div>
                              <div class="row mb-2"><div class="col-5" data-i18n="sale_price_egp">Sale Price</div><div class="col-7 fw-bold">${fmt(sale.sale_price)}</div></div>
                              <div class="row mb-2"><div class="col-5" data-i18n="selling_expenses_egp">Selling Expenses</div><div class="col-7">${fmt(sale.selling_expenses)}</div></div>
                              <div class="row"><div class="col-5" data-i18n="net_sale_amount">Net Sale Amount</div><div class="col-7 fw-bold">${fmt(sale.net_sale_amount)}</div></div>
                            ` : `<div class="text-center py-4" style="color:var(--text-secondary);" data-i18n="no_data">No data available</div>`}
                          </div>
                        </div>
                      </div>
                      <div class="col-md-6">
                        <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);">
                          <div class="card-body p-4">
                            <h6 class="mb-3 fw-bold fixed-assets-section-title" data-i18n="notes">Notes</h6>
                            <div>${sale?.notes || '-'}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
            </div>
            <div id="assetPhotoOverlay" class="position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-90 d-none" style="z-index:2000;">
                <div class="d-flex h-100 align-items-center justify-content-center">
                    <img id="assetFullscreenImage" src="" alt="Fullscreen asset photo" class="img-fluid rounded" style="max-height:90%; max-width:90%;" />
                </div>
            </div>
        </div>
    </div>

    <div class="modal-footer">
        <button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="close">Close</button>
    </div>
`;

    showModal(html);

    applyTranslations();

    const mainPhoto = document.getElementById('assetMainPhoto');
    const photoOverlay = document.getElementById('assetPhotoOverlay');
    const fullscreenImage = document.getElementById('assetFullscreenImage');

    if (mainPhoto) {
      mainPhoto.addEventListener('click', () => {
        fullscreenImage.src = mainPhoto.src;
        photoOverlay.classList.remove('d-none');
      });
    }

    photoOverlay?.addEventListener('click', () => {
      photoOverlay.classList.add('d-none');
      fullscreenImage.src = '';
    });

    const assetPhotoThumbnails = document.querySelectorAll('.asset-photo-thumbnail');
    assetPhotoThumbnails.forEach((thumb, index) => {
      thumb.addEventListener('click', (e) => {
        const url = e.currentTarget.dataset.url;
        const mainImg = document.getElementById('assetMainPhoto');
        if (mainImg) mainImg.src = url;
        assetPhotoThumbnails.forEach((item) => item.classList.remove('active'));
        e.currentTarget.classList.add('active');
      });
    });

    const propertyLatitude = parseFloat(asset.real_estate?.latitude);
    const propertyLongitude = parseFloat(asset.real_estate?.longitude);

    if (!Number.isNaN(propertyLatitude) && !Number.isNaN(propertyLongitude)) {
      assetViewMap = L.map('assetPropertyMap', {
        dragging: false,
        touchZoom: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        zoomControl: false,
        tap: false,
      }).setView([propertyLatitude, propertyLongitude], 14);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(assetViewMap);

      L.marker([propertyLatitude, propertyLongitude], { interactive: false }).addTo(assetViewMap);
      setTimeout(() => assetViewMap.invalidateSize(), 200);
    }

    const assetPropertyTab = document.getElementById('asset-property-tab');
    if (assetPropertyTab && assetViewMap) {
      assetPropertyTab.addEventListener('shown.bs.tab', () => {
        setTimeout(() => assetViewMap.invalidateSize(), 50);
      });
    }

    document.querySelectorAll('#assetDetailsTabsContent .card').forEach((card) => {
      card.style.background = 'var(--bg-secondary)';
      card.style.color = 'var(--text-primary)';
    });

    document.querySelectorAll('#assetDetailsTabsContent').forEach((el) => {
      el.style.color = 'var(--text-secondary)';
    });
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

async function loadFixedAsset(assetId) {

    currentEditingAssetId = assetId;
  showLoading();
  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/`);
    if (!response.ok) throw new Error("Failed to load asset data");
    const asset = await response.json();

    document.getElementById("fa_name").value = asset.name || "";
    document.getElementById("fa_type").value = asset.asset_type || FIXED_ASSET_TYPES.REAL_ESTATE;
    document.getElementById("fa_status").value = asset.status || "Owned";
    document.getElementById("fa_purchase_date").value =
      asset.purchase_date || "";
    document.getElementById("fa_purchase_price").value =
      asset.purchase_price || 0;
    document.getElementById("fa_purchase_usd_rate").value =
      asset.purchase_usd_rate || 1;
    document.getElementById("fa_purchase_price_usd").value =
      asset.purchase_price_usd || 0;
    const existingPurchasePayments = Array.isArray(asset.purchase_payments) ? asset.purchase_payments : [];
    currentAssetHasPurchaseSync = existingPurchasePayments.length > 0;
    populatePurchasePaymentsForm(existingPurchasePayments, asset.purchase_price || 0, false);
    maybeRefreshPurchaseUsdRateOnLoad();
    document.getElementById("fa_current_value").value =
      asset.current_market_value || 0;
    document.getElementById("fa_last_valuation_date").value =
      asset.last_valuation_date || "";
    document.getElementById("fa_val_source").value =
      asset.valuation_source || "Manual";
    document.getElementById("fa_last_valuation_date").value =
      asset.last_valuation_date || "";
    document.getElementById("fa_notes").value = asset.notes || "";
    populateSaleForm(asset.sale || null);
    populateMortgageForm(asset.mortgage || null);
    populateRentalForm(asset.rental || null);
    toggleSaleTabVisibility();
    // ---------------- Property Photos ----------------

    propertyPhotos = asset.photos || [];

    renderPropertyPhotoGallery();

    toggleRealEstateDependentTabs();

    const vehicle = asset.vehicle_details || {};
    document.getElementById("vd_brand").value = vehicle.brand || "";
    document.getElementById("vd_model").value = vehicle.model || "";
    document.getElementById("vd_year").value = vehicle.year || "";
    document.getElementById("vd_vin").value = vehicle.vin || "";
    document.getElementById("vd_engine").value = vehicle.engine || "";
    document.getElementById("vd_transmission").value = vehicle.transmission || "";
    document.getElementById("vd_fuel_type").value = vehicle.fuel_type || "";
    document.getElementById("vd_mileage").value = vehicle.mileage || "";
    document.getElementById("vd_plate_number").value = vehicle.plate_number || "";
    document.getElementById("vd_license_expiry_date").value = vehicle.license_expiry_date || "";
    document.getElementById("vd_color").value = vehicle.color || "";

    const gold = asset.gold_details || {};
    await populateGoldSettingsDropdowns(gold.gold_type || "", gold.purity || "");
    document.getElementById("gd_weight").value = gold.weight || "";
    document.getElementById("gd_unit").value = gold.unit || "gram";
    document.getElementById("gd_market_price").value = gold.market_price || "";
    document.getElementById("gd_cashback_per_gram").value = gold.cashback_per_gram || 0;
    document.getElementById("gd_purchase_weight").value = gold.purchase_weight || "";

    const other = asset.other_asset_details || {};
    document.getElementById("od_category").value = other.category || "";
    document.getElementById("od_manufacturer").value = other.manufacturer || "";
    document.getElementById("od_model").value = other.model || "";
    document.getElementById("od_serial_number").value = other.serial_number || "";
    document.getElementById("od_warranty_expiry").value = other.warranty_expiry || "";
    document.getElementById("od_description").value = other.description || "";
    document.getElementById("od_notes").value = other.notes || "";

    updateGoldValuation();

    if (asset.real_estate) {
      const re = asset.real_estate;
      populatePropertyValuationFields(re);
      document.getElementById("re_country").value = re.country || "";
      document.getElementById("re_governorate").value = re.governorate || "";
      document.getElementById("re_city").value = re.city || "";
      document.getElementById("re_district").value = re.district || "";
      document.getElementById("re_address").value = re.address || "";
      document.getElementById("re_latitude").value = re.latitude || "";
      document.getElementById("re_longitude").value = re.longitude || "";
      document.getElementById("re_area").value = re.apartment_area || 0;
      document.getElementById("re_land_area").value = re.land_area || 0;
      document.getElementById("re_rooms").value = re.rooms || 0;
      document.getElementById("re_bathrooms").value = re.bathrooms || 0;
      document.getElementById("re_floor").value = re.floor || 0;
      document.getElementById("re_b_floors").value = re.building_floors || 0;
      document.getElementById("re_year").value = re.building_year || 0;
      document.getElementById("re_facades").value = re.facades || "";
      document.getElementById("re_furnished").value =
        re.furnished_status || "Unfurnished";
      document.getElementById("re_finishing").value = re.finishing_level || "";
      document.getElementById("re_util_elec").checked = Boolean(re.electricity);
      document.getElementById("re_util_water").checked = Boolean(re.water);
      document.getElementById("re_util_gas").checked = Boolean(re.gas);
      document.getElementById("re_feat_elevator").checked = Boolean(
        re.elevator,
      );
      document.getElementById("re_feat_garage").checked = Boolean(re.garage);
      document.getElementById("re_feat_licensed").checked = Boolean(
        re.licensed,
      );
      document.getElementById("re_has_land_share").checked = Boolean(
        re.has_land_share,
      );
      document.getElementById("re_land_share").value = re.land_share || "";
      document.getElementById("re_description").value = re.description || "";
      const lat = parseFloat(re.latitude);
      const lng = parseFloat(re.longitude);

      if (!isNaN(lat) && !isNaN(lng)) {
        document.getElementById("re_latitude").value = lat;
        document.getElementById("re_longitude").value = lng;

        initializePropertyMap(lat, lng);
      }
    } else {
      populatePropertyValuationFields({});
    }

    // ---------- Renovations ----------
    const renovationContainer = document.getElementById("renovationContainer");

    if (renovationContainer) {
      renovationContainer.innerHTML = "";

      if (asset.renovations && asset.renovations.length) {
        asset.renovations.forEach((r) => {
          addRenovationRow({
            date: r.date,
            category: r.category,
            description: r.description,
            amount_egp: r.amount_egp,
            usd_rate: r.usd_rate,
            amount_usd: r.amount_usd,
            notes: r.notes,
          });
        });
      }
    }

    const furnitureContainer = document.getElementById("furnitureContainer");
    if (furnitureContainer) {
      furnitureContainer.innerHTML = "";
      (asset.furniture || []).forEach((item) => addFurnitureRow(item));
    }

    const valuationContainer = document.getElementById("valuationContainer");
    if (valuationContainer) {
      valuationContainer.innerHTML = "";
      (asset.valuation_history || []).forEach((item) => addValuationRow(item));
    }

    const maintenanceContainer = document.getElementById("maintenanceContainer");
    if (maintenanceContainer) {
      maintenanceContainer.innerHTML = "";
      (asset.maintenance || []).forEach((item) => addMaintenanceRow(item));
    }

    const insuranceContainer = document.getElementById("insuranceContainer");
    if (insuranceContainer) {
      insuranceContainer.innerHTML = "";
      (asset.insurance || []).forEach((item) => addInsuranceRow(item));
    }
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

function updatePurchasePriceUSD() {
  const purchasePrice =
    parseFloat(document.getElementById("fa_purchase_price").value) || 0;
  const rate =
    parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0;
  const purchaseCurrencyCode = getSelectedPurchaseCurrencyCode();
  const usdField = document.getElementById("fa_purchase_price_usd");

  if (!usdField) return;

  if (purchaseCurrencyCode === "USD") {
    usdField.value = purchasePrice > 0 ? purchasePrice.toFixed(2) : "0.00";
    return;
  }

  if (purchaseCurrencyCode === "EGP") {
    if (rate > 0) {
      usdField.value = (purchasePrice / rate).toFixed(2);
    } else {
      usdField.value = "";
    }
    return;
  }

  if (rate > 0) {
    usdField.value = (purchasePrice * rate).toFixed(2);
  } else {
    usdField.value = "";
  }
}

function getSelectedPurchaseCurrency() {
  const selectedId = parseInt(document.getElementById("fa_purchase_currency")?.value, 10) || null;
  if (!selectedId) return null;
  return fixedAssetSyncCurrencies.find((item) => parseInt(item?.id, 10) === selectedId) || null;
}

function getSelectedPurchaseCurrencyCode() {
  return String(getSelectedPurchaseCurrency()?.code || "").toUpperCase();
}

function getRateToEgp(row) {
  return parseFloat(row?.buy_rate) || 0;
}

function applyPurchaseUsdRateByCurrency(rates) {
  const purchaseCurrencyCode = getSelectedPurchaseCurrencyCode();
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  if (purchaseCurrencyCode === "USD") {
    usdRateField.value = "1.00000";
    updatePurchasePriceUSD();
    return;
  }

  const usd = rates.find((item) => String(item?.currency_code || "").toUpperCase() === "USD");
  const usdBuyRate = getRateToEgp(usd);
  if (!usdBuyRate) {
    throw new Error(t("error_loading_rates", "Error loading exchange rates."));
  }

  if (purchaseCurrencyCode === "EGP") {
    // Base currency is not stored in exchange-rate table; use implicit buy_rate = 1.00.
    const rate = usdBuyRate;
    usdRateField.value = rate.toFixed(5);
    updatePurchasePriceUSD();
    return;
  }

  let currencyBuyRate = 1;
  if (purchaseCurrencyCode && purchaseCurrencyCode !== "EGP") {
    const selectedCurrency = rates.find((item) => String(item?.currency_code || "").toUpperCase() === purchaseCurrencyCode);
    currencyBuyRate = getRateToEgp(selectedCurrency);
    if (!currencyBuyRate) {
      throw new Error(t("error_loading_rates", "Error loading exchange rates."));
    }
  }

  const rate = currencyBuyRate / usdBuyRate;
  usdRateField.value = rate.toFixed(5);
  updatePurchasePriceUSD();
}

async function handlePurchaseCurrencyChange() {
  const purchaseCurrencyCode = getSelectedPurchaseCurrencyCode();
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  const isGold = isGoldAssetType(document.getElementById("fa_type")?.value);
  if (purchaseCurrencyCode === "USD") {
    usdRateField.value = "1.00000";
    if (!isGold) {
      usdRateField.readOnly = true;
    }
    updatePurchasePriceUSD();
    return;
  } else if (!isGold) {
    usdRateField.readOnly = false;
  }

  try {
    const response = await fetch("/api/rates/");
    if (!response.ok) {
      throw new Error(t("error_loading_rates", "Error loading exchange rates."));
    }
    const payload = await response.json();
    const rates = Array.isArray(payload?.rates) ? payload.rates : [];
    applyPurchaseUsdRateByCurrency(rates);
  } catch (error) {
    showToast(error.message, "danger");
  }
}

function applyGoldReadOnlyState(isGold) {
  const purchaseUsdRateField = document.getElementById("fa_purchase_usd_rate");
  const purchaseUsdField = document.getElementById("fa_purchase_price_usd");
  const currentMarketValueField = document.getElementById("fa_current_value");
  const goldMarketPriceField = document.getElementById("gd_market_price");
  const valuationSourceRow = document.getElementById("valuation-source-row");
  const valuationSourceField = document.getElementById("fa_val_source");

  if (purchaseUsdRateField) purchaseUsdRateField.readOnly = isGold;
  if (purchaseUsdField) purchaseUsdField.readOnly = true;
  if (currentMarketValueField) currentMarketValueField.readOnly = isGold;
  if (goldMarketPriceField) goldMarketPriceField.readOnly = true;

  if (valuationSourceRow) {
    valuationSourceRow.classList.toggle("d-none", isGold);
  }
  if (valuationSourceField && isGold) {
    valuationSourceField.value = "Automatic";
  }
}

async function refreshGoldCalculatedFields(forcePriceFetch = false) {
  if (!isGoldAssetType(document.getElementById("fa_type")?.value)) {
    return;
  }

  try {
    const gold = await getLatestGoldPrice(forcePriceFetch);
    if (!gold) return;

    // Do not overwrite existing USD rate for gold on load/edit.
    // Only populate when missing/invalid (same behavior as other asset types).
    maybeRefreshPurchaseUsdRateOnLoad();

    const purity = document.getElementById("gd_purity")?.value || "24K";
    const unit = document.getElementById("gd_unit")?.value || "gram";
    const weight = parseFloat(document.getElementById("gd_weight")?.value) || 0;

    const puritySettings = await getGoldPuritySettings(forcePriceFetch);
    const purityKey = normalizeGoldPurity(purity);
    const purityConfig = (puritySettings || []).find((item) => String(item.key || "").toLowerCase() === purityKey);
    const cashbackPerGram = parseFloat(purityConfig?.cashback_per_gram) || 0;

    const sellPerGram = getGoldSellPerGram(gold, purityKey);
    const unitFactor = getGoldUnitFactor(unit);
    const marketPricePerUnit = sellPerGram * unitFactor;
    const weightInGrams = weight * unitFactor;
    const currentMarketValue = (sellPerGram + cashbackPerGram) * weightInGrams;

    const marketPriceField = document.getElementById("gd_market_price");
    if (marketPriceField) {
      marketPriceField.value = marketPricePerUnit > 0 ? marketPricePerUnit.toFixed(4) : "";
    }

    const currentValueField = document.getElementById("fa_current_value");
    if (currentValueField) {
      currentValueField.value = currentMarketValue > 0 ? currentMarketValue.toFixed(2) : "0.00";
    }

    const cashbackField = document.getElementById("gd_cashback_per_gram");
    if (cashbackField) {
      cashbackField.value = cashbackPerGram.toFixed(4);
    }

    const valuationSourceField = document.getElementById("fa_val_source");
    if (valuationSourceField) {
      valuationSourceField.value = "Automatic";
    }
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function updateNetSaleAmount() {
  const salePrice =
    parseFloat(document.getElementById("fa_sale_price")?.value) || 0;
  const sellingExpenses =
    parseFloat(document.getElementById("fa_selling_expenses")?.value) || 0;
  const netSaleField = document.getElementById("fa_net_sale_amount");

  if (!netSaleField) return;

  netSaleField.value = (salePrice - sellingExpenses).toFixed(2);
}

function shouldRequireBankForMethod(methodValue) {
  const normalized = String(methodValue || "").trim().toLowerCase();
  return normalized !== "cash";
}

function renderPaymentMethodOptions(selected = "Cash") {
  return FIXED_ASSET_PAYMENT_METHODS
    .map((method) => {
      const key = `payment_${method.toLowerCase().replace(/\s+/g, "_")}`;
      return `<option value="${method}" ${String(selected) === method ? "selected" : ""} data-i18n="${key}">${t(key, method)}</option>`;
    })
    .join("");
}

function isMonetaryCurrency(currency) {
  const code = String(currency?.code || "").trim().toUpperCase();
  const name = String(currency?.name || "").trim().toLowerCase();
  return !["GOLD", "XAU", "CASH"].includes(code) && !name.includes("gold");
}

function getMonetaryCurrencies() {
  return fixedAssetSyncCurrencies.filter((currency) => isMonetaryCurrency(currency));
}

function renderCurrencyOptions(selectedCurrencyId = "") {
  return fixedAssetSyncCurrencies
    .map((currency) => {
      const selected = String(selectedCurrencyId) === String(currency.id) ? "selected" : "";
      return `<option value="${currency.id}" ${selected}>${currency.code}</option>`;
    })
    .join("");
}

function renderMonetaryCurrencyOptions(selectedCurrencyId = "") {
  return getMonetaryCurrencies()
    .map((currency) => {
      const selected = String(selectedCurrencyId) === String(currency.id) ? "selected" : "";
      return `<option value="${currency.id}" ${selected}>${currency.code}</option>`;
    })
    .join("");
}

function getDefaultMonetaryCurrencyId() {
  const monetaryCurrencies = getMonetaryCurrencies();
  const egp = monetaryCurrencies.find((row) => String(row.code).toUpperCase() === "EGP");
  return (egp || monetaryCurrencies[0] || {}).id || "";
}

function getDefaultPurchaseCurrencyId() {
  return getDefaultMonetaryCurrencyId();
}

function renderBankOptions(selectedBankId = "") {
  const rows = [`<option value="">${t("none_option", "--")}</option>`];
  fixedAssetSyncBanks.forEach((bank) => {
    const selected = String(selectedBankId) === String(bank.id) ? "selected" : "";
    rows.push(`<option value="${bank.id}" ${selected}>${bank.name}</option>`);
  });
  return rows.join("");
}

function addPurchasePaymentRow(initial = {}) {
  const container = document.getElementById("purchasePaymentsContainer");
  if (!container) return;

  const method = initial.payment_method || "Cash";
  const bankId = initial.bank_id || "";
  const amount = initial.amount ?? "";

  const row = document.createElement("div");
  row.className = "row g-2 align-items-end mb-2 purchase-payment-row";
  row.innerHTML = `
    <div class="col-md-4">
      <label class="form-label text-light" data-i18n="payment_method">Payment Method</label>
      <select class="form-select purchase-method" onchange="togglePurchasePaymentBankField(this)">${renderPaymentMethodOptions(method)}</select>
    </div>
    <div class="col-md-3 purchase-bank-wrap">
      <label class="form-label text-light" data-i18n="bank">Bank</label>
      <select class="form-select purchase-bank">${renderBankOptions(bankId)}</select>
    </div>
    <div class="col-md-4">
      <label class="form-label text-light" data-i18n="amount">Amount</label>
      <input type="number" step="0.01" class="form-control purchase-amount" value="${amount}">
    </div>
    <div class="col-md-1 d-grid">
      <button type="button" class="btn btn-outline-danger" onclick="removePurchasePaymentRow(this)"><i class="bi bi-trash"></i></button>
    </div>
  `;

  container.appendChild(row);
  togglePurchasePaymentBankField(row.querySelector(".purchase-method"));
  applyTranslations();
}

function removePurchasePaymentRow(button) {
  const row = button?.closest(".purchase-payment-row");
  if (!row) return;
  row.remove();
}

function togglePurchasePaymentBankField(methodSelect) {
  const row = methodSelect?.closest(".purchase-payment-row");
  if (!row) return;
  const method = methodSelect.value;
  const bankWrap = row.querySelector(".purchase-bank-wrap");
  const bankSelect = row.querySelector(".purchase-bank");
  const required = shouldRequireBankForMethod(method);

  if (bankWrap) bankWrap.classList.toggle("d-none", !required);
  if (bankSelect) {
    bankSelect.required = required;
    if (!required) bankSelect.value = "";
  }
}

function resetPurchasePaymentsForm() {
  const container = document.getElementById("purchasePaymentsContainer");
  if (!container) return;
  container.innerHTML = "";
}

function populatePurchasePaymentsForm(rows, fallbackAmount = 0, defaultIfEmpty = true) {
  resetPurchasePaymentsForm();
  const values = Array.isArray(rows) ? rows : [];
  const purchaseCurrencySelect = document.getElementById("fa_purchase_currency");

  if (purchaseCurrencySelect) {
    const fromRows = values.find((item) => item && item.currency_id)?.currency_id;
    purchaseCurrencySelect.value = String(fromRows || getDefaultPurchaseCurrencyId() || "");
  }

  if (!values.length) {
    if (defaultIfEmpty) {
      addPurchasePaymentRow({ amount: fallbackAmount || "" });
    }
    return;
  }
  values.forEach((row) => addPurchasePaymentRow(row));
}

function collectPurchasePaymentsPayload() {
  const rows = Array.from(document.querySelectorAll("#purchasePaymentsContainer .purchase-payment-row"));
  return rows.map((row) => ({
    payment_method: row.querySelector(".purchase-method")?.value || "Cash",
    bank_id: parseInt(row.querySelector(".purchase-bank")?.value, 10) || null,
    amount: parseFloat(row.querySelector(".purchase-amount")?.value) || 0,
  }));
}

function validatePurchasePayments(purchasePrice) {
  const purchaseCurrencyId = parseInt(document.getElementById("fa_purchase_currency")?.value, 10) || null;
  if (!purchaseCurrencyId) {
    throw new Error(t("currency_required", "Currency is required."));
  }

  const rows = collectPurchasePaymentsPayload();
  if (!rows.length) {
    if (currentEditingAssetId !== null && !currentAssetHasPurchaseSync) {
      return [];
    }
    throw new Error(t("purchase_payment_required", "Add at least one payment source."));
  }

  rows.forEach((row) => {
    if (shouldRequireBankForMethod(row.payment_method) && !row.bank_id) {
      throw new Error(t("bank_account_required", "Bank account is required for this payment method"));
    }
    if (!row.amount || row.amount <= 0) {
      throw new Error(t("amount_required", "Amount is required."));
    }
  });

  const total = rows.reduce((sum, row) => sum + (parseFloat(row.amount) || 0), 0);
  if (Math.abs(total - purchasePrice) > 0.01) {
    throw new Error(t("purchase_payment_total_mismatch", "Total payment sources must equal purchase price."));
  }

  return rows;
}

function resetSaleForm() {
  const saleDateField = document.getElementById("fa_sale_date");
  const salePriceField = document.getElementById("fa_sale_price");
  const sellingExpensesField = document.getElementById("fa_selling_expenses");
  const saleNotesField = document.getElementById("fa_sale_notes");
  const currencySelect = document.getElementById("fa_deposit_currency");
  const methodSelect = document.getElementById("fa_deposit_method");
  const bankSelect = document.getElementById("fa_deposit_bank");

  const defaultCurrency = getDefaultMonetaryCurrencyId();

  if (saleDateField) saleDateField.value = "";
  if (salePriceField) salePriceField.value = "";
  if (sellingExpensesField) sellingExpensesField.value = "0";
  if (saleNotesField) saleNotesField.value = "";
  if (currencySelect) currencySelect.value = String(defaultCurrency || "");
  if (methodSelect) methodSelect.value = "Cash";
  if (bankSelect) bankSelect.value = "";

  updateNetSaleAmount();
  toggleSaleDepositBankField();
}

function populateSaleForm(sale) {
  resetSaleForm();

  if (!sale) return;

  document.getElementById("fa_sale_date").value = sale.sale_date || "";
  document.getElementById("fa_sale_price").value = sale.sale_price || 0;
  document.getElementById("fa_selling_expenses").value =
    sale.selling_expenses || 0;
  document.getElementById("fa_sale_notes").value = sale.notes || "";

  if (sale.deposit_currency_id !== null && sale.deposit_currency_id !== undefined) {
    document.getElementById("fa_deposit_currency").value = String(sale.deposit_currency_id);
  }
  if (sale.deposit_method) {
    document.getElementById("fa_deposit_method").value = sale.deposit_method;
  }
  if (sale.deposit_bank_id !== null && sale.deposit_bank_id !== undefined) {
    document.getElementById("fa_deposit_bank").value = String(sale.deposit_bank_id);
  }

  updateNetSaleAmount();
  toggleSaleDepositBankField();
}

function maybeRefreshPurchaseUsdRateOnLoad() {
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  const currentValue = String(usdRateField.value ?? "").trim();
  const numericRate = parseFloat(currentValue);

  // Keep existing stored/manual value; refresh only when missing or invalid.
  if (!currentValue || !Number.isFinite(numericRate) || numericRate <= 0) {
    handlePurchaseCurrencyChange();
    return;
  }

  updatePurchasePriceUSD();
}

function toggleSaleDepositBankField() {
  const methodEl = document.getElementById("fa_deposit_method");
  const wrap = document.getElementById("faDepositBankWrap");
  const bankEl = document.getElementById("fa_deposit_bank");
  if (!methodEl || !wrap || !bankEl) return;

  const required = shouldRequireBankForMethod(methodEl.value);
  wrap.classList.toggle("d-none", !required);
  bankEl.required = required;
  if (!required) {
    bankEl.value = "";
  }
}

function toggleSaleTabVisibility() {
  const statusField = document.getElementById("fa_status");
  const saleTabItem = document.getElementById("sale-tab-item");
  const salePane = document.getElementById("sale-pane");
  const saleTabButton = document.getElementById("sale-tab");
  const generalTabButton = document.getElementById("general-tab");
  const isSold = statusField?.value === "Sold";

  if (!saleTabItem || !salePane || !saleTabButton) return;

  saleTabItem.classList.toggle("d-none", !isSold);
  salePane.classList.toggle("d-none", !isSold);

  if (!isSold && saleTabButton.classList.contains("active") && generalTabButton) {
    bootstrap.Tab.getOrCreateInstance(generalTabButton).show();
  }
}

function toggleRealEstateDependentTabs() {
  const assetType = document.getElementById("fa_type")?.value;
  const isRealEstate = isRealEstateAssetType(assetType);
  const isVehicle = isVehicleAssetType(assetType);
  const isGold = isGoldAssetType(assetType);
  const isOther = isOtherAssetType(assetType);
  const supportsValuationHistory = isRealEstate || isVehicle || isOther;
  const mortgageTabItem = document.getElementById("mortgage-tab-item");
  const rentalTabItem = document.getElementById("rental-tab-item");
  const vehicleTabItem = document.getElementById("vehicle-tab-item");
  const goldTabItem = document.getElementById("gold-tab-item");
  const otherDetailsTabItem = document.getElementById("other-details-tab-item");
  const renovationTab = document.getElementById("renovation-tab")?.closest("li");
  const furnitureTab = document.getElementById("furniture-tab")?.closest("li");
  const valuationTab = document.getElementById("valuation-tab")?.closest("li");
  const maintenanceTabItem = document.getElementById("maintenance-tab-item");
  const insuranceTabItem = document.getElementById("insurance-tab-item");
  const mortgagePane = document.getElementById("mortgage-pane");
  const rentalPane = document.getElementById("rental-pane");
  const propertyTab = document.getElementById("property-tab")?.closest("li");
  const propertyPane = document.getElementById("property-pane");
  const vehiclePane = document.getElementById("vehicle-pane");
  const goldPane = document.getElementById("gold-pane");
  const otherDetailsPane = document.getElementById("other-details-pane");
  const renovationPane = document.getElementById("renovation-pane");
  const furniturePane = document.getElementById("furniture-pane");
  const valuationPane = document.getElementById("valuation-pane");
  const maintenancePane = document.getElementById("maintenance-pane");
  const insurancePane = document.getElementById("insurance-pane");
  const generalTabButton = document.getElementById("general-tab");

  [
    propertyTab,
    propertyPane,
    mortgageTabItem,
    rentalTabItem,
    mortgagePane,
    rentalPane,
    renovationTab,
    renovationPane,
    furnitureTab,
    furniturePane,
    vehicleTabItem,
    vehiclePane,
    maintenanceTabItem,
    maintenancePane,
    insuranceTabItem,
    insurancePane,
    goldTabItem,
    goldPane,
    otherDetailsTabItem,
    otherDetailsPane,
    valuationTab,
    valuationPane,
  ].forEach((element) => {
    if (element) {
      element.classList.add("d-none");
    }
  });

  [propertyTab, propertyPane, renovationTab, renovationPane, furnitureTab, furniturePane, valuationTab, valuationPane, mortgageTabItem, mortgagePane, rentalTabItem, rentalPane].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !isRealEstate);
    }
  });

  [vehicleTabItem, vehiclePane, maintenanceTabItem, maintenancePane, insuranceTabItem, insurancePane].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !isVehicle);
    }
  });

  [goldTabItem, goldPane].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !isGold);
    }
  });

  [valuationTab, valuationPane].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !supportsValuationHistory);
    }
  });

  [otherDetailsTabItem, otherDetailsPane].forEach((element) => {
    if (element) {
      element.classList.toggle("d-none", !isOther);
    }
  });

  applyGoldReadOnlyState(isGold);

  if (isGold) {
    refreshGoldCalculatedFields();
  }

  [
    "mortgage-tab",
    "rental-tab",
    "property-tab",
    "renovation-tab",
    "furniture-tab",
    "valuation-tab",
    "vehicle-tab",
    "maintenance-tab",
    "insurance-tab",
    "gold-tab",
    "other-details-tab",
  ].forEach((tabId) => {
    const tab = document.getElementById(tabId);
    const hiddenParent = tab?.closest("li")?.classList.contains("d-none");
    if (hiddenParent && tab?.classList.contains("active") && generalTabButton) {
      bootstrap.Tab.getOrCreateInstance(generalTabButton).show();
    }
  });

  toggleRealEstateFields();
}

function updateMortgageSummary() {
  const currentValue = parseFloat(document.getElementById("fa_current_value")?.value) || 0;
  const remainingBalance = parseFloat(document.getElementById("fa_remaining_balance")?.value) || 0;
  const netEquityField = document.getElementById("fa_net_equity");

  if (netEquityField) {
    netEquityField.value = (currentValue - remainingBalance).toFixed(2);
  }
}

function resetMortgageForm() {
  [
    "fa_loan_amount",
    "fa_remaining_balance",
    "fa_monthly_installment",
    "fa_interest_rate",
    "fa_mortgage_start_date",
    "fa_mortgage_end_date",
  ].forEach((id) => {
    const field = document.getElementById(id);
    if (field) field.value = "";
  });
  const netEquityField = document.getElementById("fa_net_equity");
  if (netEquityField) netEquityField.value = "";
}

async function deleteMortgageDetails() {
  resetMortgageForm();
  updateMortgageSummary();
  if (currentEditingAssetId !== null && currentEditingAssetId !== undefined) {
    await saveFixedAsset(currentEditingAssetId);
  }
}

function populateMortgageForm(mortgage) {
  resetMortgageForm();
  if (!mortgage) return;

  document.getElementById("fa_loan_amount").value = mortgage.loan_amount || 0;
  document.getElementById("fa_remaining_balance").value = mortgage.remaining_balance || 0;
  document.getElementById("fa_monthly_installment").value = mortgage.monthly_installment || 0;
  document.getElementById("fa_interest_rate").value = mortgage.interest_rate || 0;
  document.getElementById("fa_mortgage_start_date").value = mortgage.start_date || "";
  document.getElementById("fa_mortgage_end_date").value = mortgage.end_date || "";
  updateMortgageSummary();
}

function collectMortgagePayload() {
  return {
    loan_amount: parseFloat(document.getElementById("fa_loan_amount")?.value) || 0,
    remaining_balance: parseFloat(document.getElementById("fa_remaining_balance")?.value) || 0,
    monthly_installment: parseFloat(document.getElementById("fa_monthly_installment")?.value) || 0,
    interest_rate: parseFloat(document.getElementById("fa_interest_rate")?.value) || 0,
    start_date: document.getElementById("fa_mortgage_start_date")?.value || null,
    end_date: document.getElementById("fa_mortgage_end_date")?.value || null,
  };
}

function updateRentalSummary() {
  const monthlyRent = parseFloat(document.getElementById("fa_monthly_rent")?.value) || 0;
  const annualRent = monthlyRent * 12;
  const currentValue = parseFloat(document.getElementById("fa_current_value")?.value) || 0;
  const rentalYield = currentValue > 0 ? (annualRent / currentValue) * 100 : 0;
  const annualRentField = document.getElementById("fa_annual_rent");
  const rentalYieldField = document.getElementById("fa_rental_yield");

  if (annualRentField) annualRentField.value = annualRent.toFixed(2);
  if (rentalYieldField) rentalYieldField.value = rentalYield.toFixed(2);
}

function resetRentalForm() {
  [
    "fa_monthly_rent",
    "fa_occupancy_rate",
    "fa_tenant_name",
    "fa_contract_start",
    "fa_contract_end",
    "fa_rental_notes",
  ].forEach((id) => {
    const field = document.getElementById(id);
    if (field) field.value = "";
  });
  ["fa_annual_rent", "fa_rental_yield"].forEach((id) => {
    const field = document.getElementById(id);
    if (field) field.value = "";
  });
}

async function deleteRentalDetails() {
  resetRentalForm();
  updateRentalSummary();
  if (currentEditingAssetId !== null && currentEditingAssetId !== undefined) {
    await saveFixedAsset(currentEditingAssetId);
  }
}

function populateRentalForm(rental) {
  resetRentalForm();
  if (!rental) return;

  document.getElementById("fa_monthly_rent").value = rental.monthly_rent || 0;
  document.getElementById("fa_occupancy_rate").value = rental.occupancy_rate || 0;
  document.getElementById("fa_tenant_name").value = rental.tenant_name || "";
  document.getElementById("fa_contract_start").value = rental.contract_start || "";
  document.getElementById("fa_contract_end").value = rental.contract_end || "";
  document.getElementById("fa_rental_notes").value = rental.notes || "";
  updateRentalSummary();
}

function collectRentalPayload() {
  return {
    monthly_rent: parseFloat(document.getElementById("fa_monthly_rent")?.value) || 0,
    occupancy_rate: parseFloat(document.getElementById("fa_occupancy_rate")?.value) || 0,
    tenant_name: document.getElementById("fa_tenant_name")?.value || "",
    contract_start: document.getElementById("fa_contract_start")?.value || null,
    contract_end: document.getElementById("fa_contract_end")?.value || null,
    notes: document.getElementById("fa_rental_notes")?.value || "",
  };
}

async function loadFixedAssetSyncDropdownData() {
  if (!fixedAssetSyncCurrencies.length || !fixedAssetSyncBanks.length) {
    const [currRes, bankRes] = await Promise.all([
      fetch("/api/currencies/"),
      fetch("/api/banks/"),
    ]);

    if (!currRes.ok) {
      throw new Error(t("error_loading_currencies", "Error loading currencies"));
    }
    if (!bankRes.ok) {
      throw new Error(t("error_loading_banks", "Error loading banks"));
    }

    const currData = await currRes.json();
    const bankData = await bankRes.json();

    fixedAssetSyncCurrencies = Array.isArray(currData.currencies) ? currData.currencies : [];
    fixedAssetSyncBanks = Array.isArray(bankData.banks) ? bankData.banks.filter((b) => b?.is_active !== false) : [];
  }

  const saleCurrency = document.getElementById("fa_deposit_currency");
  if (saleCurrency) {
    saleCurrency.innerHTML = renderMonetaryCurrencyOptions();
  }

  const purchaseCurrency = document.getElementById("fa_purchase_currency");
  if (purchaseCurrency) {
    purchaseCurrency.innerHTML = renderMonetaryCurrencyOptions();
    purchaseCurrency.value = String(getDefaultPurchaseCurrencyId() || "");
  }

  const saleMethod = document.getElementById("fa_deposit_method");
  if (saleMethod) {
    saleMethod.innerHTML = renderPaymentMethodOptions("Cash");
  }

  const saleBank = document.getElementById("fa_deposit_bank");
  if (saleBank) {
    saleBank.innerHTML = renderBankOptions();
  }
}

async function fillCurrentUsdRate() {
  const usdRateField = document.getElementById("fa_purchase_usd_rate");
  if (!usdRateField) return;

  try {
    const response = await fetch("/api/rates/");
    if (!response.ok) {
      throw new Error(t("error_loading_rates", "Error loading exchange rates."));
    }
    const payload = await response.json();
    const rates = Array.isArray(payload?.rates) ? payload.rates : [];
    applyPurchaseUsdRateByCurrency(rates);
  } catch (error) {
    showToast(error.message, "danger");
  }
}

function collectSalePayload() {
  return {
    sale_date: document.getElementById("fa_sale_date").value,
    sale_price: parseFloat(document.getElementById("fa_sale_price").value) || 0,
    selling_expenses:
      parseFloat(document.getElementById("fa_selling_expenses").value) || 0,
    net_sale_amount:
      parseFloat(document.getElementById("fa_net_sale_amount").value) || 0,
    deposit_currency_id:
      parseInt(document.getElementById("fa_deposit_currency").value, 10) || null,
    deposit_method:
      document.getElementById("fa_deposit_method").value || "Cash",
    deposit_bank_id:
      parseInt(document.getElementById("fa_deposit_bank").value, 10) || null,
    notes: document.getElementById("fa_sale_notes").value,
  };
}

function validateSaleForm() {
  const saleDate = document.getElementById("fa_sale_date").value;
  const salePrice = parseFloat(document.getElementById("fa_sale_price").value) || 0;

  if (!saleDate) {
    throw new Error(t("sale_date_required", "Sale date is required"));
  }

  if (salePrice <= 0) {
    throw new Error(t("sale_price_required", "Sale price must be greater than zero"));
  }

  const depositCurrencyId = parseInt(document.getElementById("fa_deposit_currency")?.value, 10) || null;
  const depositMethod = document.getElementById("fa_deposit_method")?.value || "Cash";
  const depositBankId = parseInt(document.getElementById("fa_deposit_bank")?.value, 10) || null;

  if (!depositCurrencyId) {
    throw new Error(t("currency_required", "Currency is required."));
  }
  if (shouldRequireBankForMethod(depositMethod) && !depositBankId) {
    throw new Error(t("bank_account_required", "Bank account is required for this payment method"));
  }
}

async function syncAssetSale(assetId, status) {
  if (status === "Sold") {
    validateSaleForm();

    const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(collectSalePayload()),
    });

    if (!response.ok) {
      let message = t("error_saving_sale", "Error saving sale information");
      try {
        const payload = await response.json();
        if (payload?.error_key) {
          message = t(payload.error_key, payload.error || message);
        } else if (payload?.error) {
          message = payload.error;
        }
      } catch (_) {
        // Keep fallback message.
      }
      throw new Error(message);
    }

    return;
  }

  const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
  });

  if (!response.ok && response.status !== 404) {
    let message = t("error_removing_sale", "Error removing sale information");
    try {
      const payload = await response.json();
      if (payload?.error_key) {
        message = t(payload.error_key, payload.error || message);
      } else if (payload?.error) {
        message = payload.error;
      }
    } catch (_) {
      // Keep fallback message.
    }
    throw new Error(message);
  }
}

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

async function saveFixedAsset(assetId = null) {
  const isEdit = assetId !== null;
  const url = isEdit ? `/api/fixed-assets/${assetId}/` : "/api/fixed-assets/";
  const method = isEdit ? "PUT" : "POST";

  const assetType = document.getElementById("fa_type").value;
  const assetStatus = document.getElementById("fa_status").value;
  const isRealEstate = isRealEstateAssetType(assetType);
  const isVehicle = isVehicleAssetType(assetType);
  const isGold = isGoldAssetType(assetType);
  const isOther = isOtherAssetType(assetType);
  const purchasePrice = parseFloat(document.getElementById("fa_purchase_price").value) || 0;

  let purchasePayments = [];
  try {
    purchasePayments = validatePurchasePayments(purchasePrice);
  } catch (validationError) {
    showToast(validationError.message, "danger");
    return;
  }

  const purchaseCurrencyCode = getSelectedPurchaseCurrencyCode();
  const uiUsdRate = parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0;
  const backendUsdRate =
    purchaseCurrencyCode === "USD"
      ? 1
      : purchaseCurrencyCode === "EGP"
        ? (uiUsdRate > 0 ? uiUsdRate : 1)
        : (uiUsdRate > 0 ? (1 / uiUsdRate) : 1);

  const payload = {
    name: document.getElementById("fa_name").value,
    asset_type: assetType,
    purchase_date: document.getElementById("fa_purchase_date").value,
    purchase_price: purchasePrice,
    purchase_usd_rate: backendUsdRate,
    purchase_price_usd:
      parseFloat(document.getElementById("fa_purchase_price_usd").value) || 0,
    purchase_currency_id:
      parseInt(document.getElementById("fa_purchase_currency").value, 10) || null,
    current_market_value:
      parseFloat(document.getElementById("fa_current_value").value) || 0,
    valuation_source: document.getElementById("fa_val_source").value,
    last_valuation_date:
      document.getElementById("fa_last_valuation_date").value || null,
    notes: document.getElementById("fa_notes").value,
    status: assetStatus,
    purchase_payments: purchasePayments,
  };

  if (isGold) {
    payload.valuation_source = "Automatic";
  }

  if (isRealEstate) {
    payload.real_estate_details = {
      country: document.getElementById("re_country").value,
      governorate: document.getElementById("re_governorate").value,
      city: document.getElementById("re_city").value,
      district: document.getElementById("re_district").value,
      address: document.getElementById("re_address").value,
      latitude:
        parseFloat(document.getElementById("re_latitude").value) || null,
      longitude:
        parseFloat(document.getElementById("re_longitude").value) || null,
      apartment_area: parseFloat(document.getElementById("re_area").value) || 0,
      land_share_sqm:
        parseFloat(document.getElementById("re_land_area").value) || 0,
      rooms: parseInt(document.getElementById("re_rooms").value) || 0,
      bathrooms: parseInt(document.getElementById("re_bathrooms").value) || 0,
      floor: parseInt(document.getElementById("re_floor").value) || 0,
      building_floors:
        parseInt(document.getElementById("re_b_floors").value) || 0,
      building_year: parseInt(document.getElementById("re_year").value) || 0,
      facades: document.getElementById("re_facades").value,
      finishing_level: document.getElementById("re_finishing").value,
      furnished_status: document.getElementById("re_furnished").value,
      electricity: document.getElementById("re_util_elec").checked,
      water: document.getElementById("re_util_water").checked,
      gas: document.getElementById("re_util_gas").checked,
      elevator: document.getElementById("re_feat_elevator").checked,
      garage: document.getElementById("re_feat_garage").checked,
      licensed: document.getElementById("re_feat_licensed").checked,
      has_land_share: document.getElementById("re_has_land_share").checked,
      land_share: document.getElementById("re_land_share").value,
      description: document.getElementById("re_description").value,
    };
    payload.mortgage_details = collectMortgagePayload();
    payload.rental_details = collectRentalPayload();
    payload.renovations = collectRenovations();
  } else {
    payload.real_estate_details = null;
    payload.mortgage_details = null;
    payload.rental_details = null;
    payload.renovations = [];
  }

  payload.vehicle_details = isVehicle ? collectVehicleDetailsPayload() : null;
  payload.gold_details = isGold ? collectGoldDetailsPayload() : null;
  payload.other_asset_details = isOther ? collectOtherAssetDetailsPayload() : null;
  payload.maintenance = isVehicle ? collectMaintenance() : [];
  payload.insurance = isVehicle ? collectInsurance() : [];

  payload.furniture = isRealEstate ? collectFurniture() : [];
  payload.valuation_history = (isRealEstate || isVehicle || isOther) ? collectValuationHistory() : [];

  showLoading();
  try {
    const response = await fetch(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let message = t("error_saving_fixed_asset", "Error saving fixed asset");
      try {
        const errorPayload = await response.json();
        if (errorPayload?.error_key) {
          message = t(errorPayload.error_key, errorPayload.error || message);
        } else if (errorPayload?.error) {
          message = errorPayload.error;
        }
      } catch (_) {
        // Keep fallback message.
      }
      throw new Error(message);
    }

    const savedAsset = await response.json();

  await syncAssetSale(savedAsset.id, assetStatus);

    const files = document.getElementById("propertyPhotoInput").files;

    if (files.length > 0) {
        for (const file of files) {
            const formData = new FormData();
            formData.append("photos", file);

            const uploadResponse = await fetch(
                `/api/fixed-assets/${savedAsset.id}/photos/`,
                {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: formData,
                }
            );

            if (!uploadResponse.ok)
                throw new Error("Failed to upload property photo.");

            const uploadedPhoto = await uploadResponse.json();
            if (Array.isArray(uploadedPhoto)) {
              propertyPhotos.push(...uploadedPhoto);
            } else if (uploadedPhoto) {
              propertyPhotos.push(uploadedPhoto);
            }
        }

        renderPropertyPhotoGallery();
        document.getElementById("propertyPhotoInput").value = "";
    }

    showToast(
      isEdit
        ? t("fixed_asset_updated_success", "Asset updated successfully")
        : t("fixed_asset_added_success", "Asset added successfully"),
      "success",
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

function showSaleModal(assetId, assetName, currentMarketValue) {
  const html = `
        <div class="modal-header">
            <h5 class="modal-title"><span data-i18n="sell_asset">Sell Asset</span>: ${assetName}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="assetSaleForm">
                <div class="mb-3">
                    <label class="form-label" data-i18n="sale_date">Sale Date</label>
                    <input type="date" class="form-control" id="sale_date" required>
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="sale_price">Sale Price</label>
                    <input type="number" step="0.01" class="form-control" id="sale_price" value="${currentMarketValue}" required>
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="selling_expenses">Selling Expenses</label>
                    <input type="number" step="0.01" class="form-control" id="selling_expenses" value="0">
                </div>
                <div class="mb-3">
                    <label class="form-label" data-i18n="notes">Notes</label>
                    <textarea class="form-control" id="sale_notes" rows="2"></textarea>
                </div>
            </form>
        </div>

        <!-- Information Cards -->
        <div class="container-fluid py-4">

            <div class="row g-4">

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="general_information">
                                General Information
                            </h6>

                            <div class="d-grid gap-2">
                              <div class="d-flex justify-content-between"><span data-i18n="asset_type">Asset Type</span><span id="details_asset_type" class="fw-bold"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_date">Purchase Date</span><span id="details_purchase_date"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="valuation_source">Valuation Source</span><span id="details_valuation_source"></span></div>
                            </div>

                        </div>

                    </div>

                </div>

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="financial_information">
                                Financial Information
                            </h6>

                            <div class="d-grid gap-2">
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_price_egp">Purchase Price</span><span id="details_purchase_price" class="fw-bold"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="purchase_price_usd">Purchase USD</span><span id="details_purchase_usd"></span></div>
                              <div class="d-flex justify-content-between"><span data-i18n="last_valuation_date">Last Valuation</span><span id="details_last_valuation"></span></div>
                            </div>

                        </div>

                    </div>

                </div>

                <div class="col-lg-4">

                    <div class="card h-100 border-0 shadow-sm bg-secondary-subtle">

                        <div class="card-body">

                            <h6 class="text-uppercase small mb-3"
                                data-i18n="notes">
                                Notes
                            </h6>

                            <div id="details_notes"
                                style="white-space:pre-wrap;"></div>

                        </div>

                    </div>

                </div>

            </div>

        </div>

        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="submitAssetSale(${assetId})" data-i18n="confirm_sale">Confirm Sale</button>
        </div>
    `;
  showModal(html);
  applyTranslations();
}

async function submitAssetSale(assetId) {
  const salePrice =
    parseFloat(document.getElementById("sale_price").value) || 0;
  const expenses =
    parseFloat(document.getElementById("selling_expenses").value) || 0;
  const netSaleAmount = salePrice - expenses;

  const payload = {
    sale_date: document.getElementById("sale_date").value,
    sale_price: salePrice,
    selling_expenses: expenses,
    net_sale_amount: netSaleAmount,
    notes: document.getElementById("sale_notes").value,
  };

  showLoading();
  try {
    const response = await fetch(`/api/fixed-assets/${assetId}/sale/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) throw new Error("Failed to process sale");

    showToast("Asset marked as Sold successfully!", "success");
    closeModal();
    fetchAndRenderFixedAssets();
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    hideLoading();
  }
}

function toggleRealEstateFields() {
  const assetType = document.getElementById("fa_type").value;
  const reSection = document.getElementById("realEstateSection");
  const isRealEstate = isRealEstateAssetType(assetType);

  if (reSection) {
    reSection.style.display = isRealEstate ? "block" : "none";
  }
}

function getCsrfToken() {
  return (
    document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1] || ""
  );
}

function initializePropertyMap(lat = 30.0444, lng = 31.2357) {
  if (propertyMap) {
    propertyMap.remove();
    propertyMap = null;
  }

  propertyMap = L.map("propertyMap").setView([lat, lng], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(propertyMap);

  propertyMarker = L.marker([lat, lng], {
    draggable: true,
  }).addTo(propertyMap);

  propertyMarker.on("dragend", function () {
    const p = propertyMarker.getLatLng();

    document.getElementById("re_latitude").value = p.lat.toFixed(6);
    document.getElementById("re_longitude").value = p.lng.toFixed(6);

    reverseGeocode(p.lat, p.lng);
  });

  propertyMap.on("click", function (e) {
    propertyMarker.setLatLng(e.latlng);

    document.getElementById("re_latitude").value = e.latlng.lat.toFixed(6);
    document.getElementById("re_longitude").value = e.latlng.lng.toFixed(6);

    reverseGeocode(e.latlng.lat, e.latlng.lng);
  });

    setTimeout(() => propertyMap.invalidateSize(), 200);

    const uploadBtn = document.getElementById("btnUploadPropertyPhoto");
    const uploadInput = document.getElementById("propertyPhotoInput");

    if (uploadBtn && uploadInput) {

        uploadBtn.onclick = () => uploadInput.click();

        uploadInput.onchange = function () {

        const gallery = document.getElementById("propertyPhotoGallery");

        gallery.innerHTML = "";

        Array.from(this.files).forEach(file => {

            const reader = new FileReader();

            reader.onload = function (e) {

                gallery.insertAdjacentHTML(
                    "beforeend",
                    `
                    <div class="col-md-4">

                        <div class="card border-0 shadow-sm">

                            <div class="d-flex justify-content-center align-items-center"
                                style="height:220px; background:var(--bg-secondary);">

                                <img
                                    src="${e.target.result}"
                                    class="img-fluid rounded"
                                    style="
                                        max-width:100%;
                                        max-height:200px;
                                        object-fit:contain;">

                            </div>

                            <div class="card-body p-2 text-center">

                                <div class="small text-truncate">
                                    ${file.name}
                                </div>

                            </div>

                        </div>

                    </div>
                    `
                );

            };

            reader.readAsDataURL(file);

        });

    };

    }
    
}

function renderPropertyPhotoGallery() {

    const gallery = document.getElementById("propertyPhotoGallery");

    if (!gallery) return;

    gallery.innerHTML = "";

    if (!propertyPhotos || propertyPhotos.length === 0) {

        gallery.innerHTML = `
            <div class="col-12 text-center py-4">
                <i class="bi bi-images"
                   style="font-size:40px;color:var(--text-secondary);opacity:.45;"></i>

                <div class="mt-2"
                     style="color:var(--text-secondary);"
                     data-i18n="no_property_photos">
                    No property photos uploaded
                </div>
            </div>
        `;

        applyTranslations();
        return;
    }

    propertyPhotos.forEach((photo, index) => {

        gallery.innerHTML += `
            <div class="col-md-4 col-lg-3">

                <div class="card border-0 shadow-sm h-100">

                    <img
                        src="${photo.url}"
                        class="card-img-top"
                        style="height:180px;object-fit:cover;">

                        <button
                            type="button"
                            class="btn btn-danger w-100"
                            onclick="removePropertyPhoto(${index})">
                            <i class="bi bi-trash"></i>
                        </button>

                </div>
            </div>
        `;

    });

}

async function removePropertyPhoto(index) {

    const photo = propertyPhotos[index];

    if (!photo) return;

    if (!confirm("Delete this photo?")) return;

    try {

        const response = await fetch(
            `/api/fixed-assets/${currentEditingAssetId}/photos/${photo.id}/`,
            {
                method: "DELETE",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                },
            }
        );

        if (!response.ok)
            throw new Error("Failed to delete photo.");

        propertyPhotos.splice(index, 1);

        renderPropertyPhotoGallery();

        showToast("Photo deleted successfully.", "success");

    } catch (err) {

        showToast(err.message, "danger");

    }

}

async function locatePropertyOnMap() {
  const country = document.getElementById("re_country").value.trim();
  const governorate = document.getElementById("re_governorate").value.trim();
  const city = document.getElementById("re_city").value.trim();
  const district = document.getElementById("re_district").value.trim();
  const address = document.getElementById("re_address").value.trim();

  const query = [address, district, city, governorate, country]
    .filter(Boolean)
    .join(", ");

  if (!query) {
    showToast("Please enter an address first.", "warning");
    return;
  }

  showLoading();

  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`,
    );

    const results = await response.json();

    if (!results.length) {
      showToast("Address not found.", "warning");
      return;
    }

    const lat = parseFloat(results[0].lat);
    const lng = parseFloat(results[0].lon);

    document.getElementById("re_latitude").value = lat.toFixed(6);
    document.getElementById("re_longitude").value = lng.toFixed(6);

    propertyMap.setView([lat, lng], 17);

    propertyMarker.setLatLng([lat, lng]);
  } catch (err) {
    console.error(err);
    showToast("Unable to locate address.", "danger");
  } finally {
    hideLoading();
  }
}

async function reverseGeocode(lat, lng) {
  try {
    const currentLang = localStorage.getItem("lang") || "en";

    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=${currentLang},en`,
    );

    const result = await response.json();

    if (!result.address) return;

    const a = result.address;
    document.getElementById("re_country").value = a.country || "";

    document.getElementById("re_governorate").value = a.state || a.county || "";

    document.getElementById("re_city").value =
      a.city || a.town || a.village || "";

    document.getElementById("re_district").value =
      a.suburb ||
      a.neighbourhood ||
      a.city_district ||
      a.district ||
      a.municipality ||
      a.hamlet ||
      a.quarter ||
      a.borough ||
      a.village ||
      a.town ||
      a.city ||
      "";

    document.getElementById("re_address").value = result.display_name || "";
  } catch (err) {
    console.error(err);
  }
}

function addRenovationRow(data = {}) {
  const container = document.getElementById("renovationContainer");

  const row = document.createElement("div");

  row.className = "row g-2 mb-3 renovation-row";

  row.innerHTML = `

        <div class="col-md-2">
            <label class="form-label small"
                   data-i18n="renovation_date">
                Date
            </label>

            <input
                type="date"
                class="form-control renovation-date"
                value="${data.date || ""}">
        </div>

        <div class="col-md-2">

            <label class="form-label small"
                   data-i18n="renovation_type">
                Renovation Type
            </label>

            <select class="form-select renovation-category">

                <option value="Finishing"
                    data-i18n="renovation_finishing">
                    Finishing
                </option>

                <option value="Painting"
                    data-i18n="renovation_painting">
                    Painting
                </option>

                <option value="Flooring"
                    data-i18n="renovation_flooring">
                    Flooring
                </option>

                <option value="Kitchen"
                    data-i18n="renovation_kitchen">
                    Kitchen
                </option>

                <option value="Bathroom"
                    data-i18n="renovation_bathroom">
                    Bathroom
                </option>

                <option value="Electrical"
                    data-i18n="renovation_electrical">
                    Electrical
                </option>

                <option value="Plumbing"
                    data-i18n="renovation_plumbing">
                    Plumbing
                </option>

                <option value="Doors & Windows"
                    data-i18n="renovation_doors_windows">
                    Doors & Windows
                </option>

                <option value="Furniture"
                    data-i18n="renovation_furniture">
                    Furniture
                </option>

                <option value="Landscape"
                    data-i18n="renovation_landscape">
                    Landscape
                </option>

                <option value="Maintenance"
                    data-i18n="renovation_maintenance">
                    Maintenance
                </option>

                <option value="Other"
                    data-i18n="type_other">
                    Other
                </option>

            </select>

        </div>

        <div class="col-md-3">

            <label class="form-label small"
                   data-i18n="description">
                Description
            </label>

            <input
                type="text"
                class="form-control renovation-description"
                data-i18n-placeholder="description"
                placeholder="Description"
                value="${data.description || ""}">

        </div>

        <div class="col-md-2">

            <label class="form-label small"
                   data-i18n="amount">
              Amount
            </label>

            <input
                type="number"
                step="0.01"
                class="form-control renovation-egp"
                value="${data.amount_egp || ""}"
                oninput="updateRenovationUSD(this)">

        </div>

        <div class="col-md-2">

            <label class="form-label small"
                   data-i18n="amount_usd">
                USD
            </label>

            <input
                type="number"
                step="0.01"
                class="form-control renovation-usd"
                value="${data.amount_usd || ""}"
                readonly>

        </div>



            <div class="col-md-1">

                <label class="form-label small">&nbsp;</label>

                <button
                    type="button"
                    class="btn btn-danger w-100"
                    onclick="this.closest('.renovation-row').remove()">

                    <i class="bi bi-trash"></i>

                </button>

            </div>

        <div class="col-md-12">

            <label class="form-label small"
                   data-i18n="notes">
                Notes
            </label>

            <textarea
                class="form-control renovation-notes"
                rows="2">${data.notes || ""}</textarea>

        </div>

    `;

  container.appendChild(row);

  row.querySelector(".renovation-category").value =
    data.category || "Finishing";

  applyTranslations();
  updateRenovationUSD(row.querySelector(".renovation-egp"));
}

function collectRenovations() {
  const renovations = [];

  document.querySelectorAll(".renovation-row").forEach((row) => {
    renovations.push({
      date: row.querySelector(".renovation-date").value,

      category: row.querySelector(".renovation-category").value,

      description: row.querySelector(".renovation-description").value,

      amount_egp: parseFloat(row.querySelector(".renovation-egp").value) || 0,

      usd_rate:
        parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0,

      amount_usd: parseFloat(row.querySelector(".renovation-usd").value) || 0,

      notes: row.querySelector(".renovation-notes").value,
    });
  });

  return renovations;
}

function updateRenovationUSD(input) {
  const row = input.closest(".renovation-row");

  const egp = parseFloat(row.querySelector(".renovation-egp").value) || 0;

  const rate =
    parseFloat(document.getElementById("fa_purchase_usd_rate").value) || 0;

  const usdInput = row.querySelector(".renovation-usd");

  if (rate > 0) {
    usdInput.value = (egp / rate).toFixed(2);
  } else {
    usdInput.value = "";
  }
}

function addFurnitureRow(data = {}) {
  const container = document.getElementById("furnitureContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "row g-2 mb-3 furniture-row";
  row.innerHTML = `
    <div class="col-md-3"><label class="form-label small" data-i18n="asset_name">Name</label><input type="text" class="form-control furniture-name" value="${data.name || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="category">Category</label><input type="text" class="form-control furniture-category" value="${data.category || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="purchase_date">Purchase Date</label><input type="date" class="form-control furniture-purchase-date" value="${data.purchase_date || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="amount_egp">Amount</label><input type="number" step="0.01" class="form-control furniture-egp" value="${data.amount_egp || ""}" oninput="updateFurnitureUSD(this)"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="amount_usd">Amount USD</label><input type="number" step="0.01" class="form-control furniture-usd" value="${data.amount_usd || ""}" readonly></div>
    <div class="col-md-1"><label class="form-label small">&nbsp;</label><button type="button" class="btn btn-danger w-100" onclick="this.closest('.furniture-row').remove()"><i class="bi bi-trash"></i></button></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="purchase_usd_rate">USD Exchange Rate</label><input type="number" step="0.0001" class="form-control furniture-usd-rate" value="${data.usd_rate || document.getElementById("fa_purchase_usd_rate")?.value || ""}" oninput="updateFurnitureUSD(this)"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="quantity">Quantity</label><input type="number" step="1" class="form-control furniture-quantity" value="${data.quantity || 1}"></div>
    <div class="col-md-8"><label class="form-label small" data-i18n="notes">Notes</label><textarea class="form-control furniture-notes" rows="2">${data.notes || ""}</textarea></div>
  `;
  container.appendChild(row);
  applyTranslations();
  updateFurnitureUSD(row.querySelector(".furniture-egp"));
}

function updateFurnitureUSD(input) {
  const row = input.closest(".furniture-row");
  if (!row) return;
  const egp = parseFloat(row.querySelector(".furniture-egp").value) || 0;
  const rate = parseFloat(row.querySelector(".furniture-usd-rate").value) || 0;
  const usdInput = row.querySelector(".furniture-usd");
  usdInput.value = rate > 0 ? (egp / rate).toFixed(2) : "";
}

function collectFurniture() {
  const furniture = [];
  document.querySelectorAll(".furniture-row").forEach((row) => {
    const name = row.querySelector(".furniture-name").value;
    if (!name) return;
    furniture.push({
      name,
      category: row.querySelector(".furniture-category").value,
      purchase_date: row.querySelector(".furniture-purchase-date").value || null,
      amount_egp: parseFloat(row.querySelector(".furniture-egp").value) || 0,
      usd_rate: parseFloat(row.querySelector(".furniture-usd-rate").value) || 0,
      amount_usd: parseFloat(row.querySelector(".furniture-usd").value) || 0,
      quantity: parseInt(row.querySelector(".furniture-quantity").value, 10) || 1,
      notes: row.querySelector(".furniture-notes").value,
    });
  });
  return furniture;
}

function addValuationRow(data = {}) {
  const container = document.getElementById("valuationContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "row g-2 mb-3 valuation-row";
  row.innerHTML = `
    <div class="col-md-3"><label class="form-label small" data-i18n="date">Date</label><input type="date" class="form-control valuation-date" value="${data.valuation_date || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="current_market_value">Market Value</label><input type="number" step="0.01" class="form-control valuation-market-value" value="${data.market_value || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="valuation_source">Valuation Source</label><select class="form-select valuation-source"><option value="Manual" data-i18n="val_manual">Manual Input</option><option value="Automatic" data-i18n="val_automatic">System Synced</option></select></div>
    <div class="col-md-2"><label class="form-label small">&nbsp;</label><button type="button" class="btn btn-danger w-100" onclick="this.closest('.valuation-row').remove()"><i class="bi bi-trash"></i></button></div>
    <div class="col-md-12"><label class="form-label small" data-i18n="notes">Notes</label><textarea class="form-control valuation-notes" rows="2">${data.notes || ""}</textarea></div>
  `;
  container.appendChild(row);
  row.querySelector(".valuation-source").value = data.valuation_source || "Manual";
  applyTranslations();
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

function collectVehicleDetailsPayload() {
  return {
    brand: document.getElementById("vd_brand")?.value || "",
    model: document.getElementById("vd_model")?.value || "",
    year: parseInt(document.getElementById("vd_year")?.value, 10) || null,
    vin: document.getElementById("vd_vin")?.value || "",
    engine: document.getElementById("vd_engine")?.value || "",
    transmission: document.getElementById("vd_transmission")?.value || "",
    fuel_type: document.getElementById("vd_fuel_type")?.value || "",
    mileage: parseFloat(document.getElementById("vd_mileage")?.value) || 0,
    plate_number: document.getElementById("vd_plate_number")?.value || "",
    license_expiry_date: document.getElementById("vd_license_expiry_date")?.value || null,
    color: document.getElementById("vd_color")?.value || "",
  };
}

function collectGoldDetailsPayload() {
  return {
    gold_type: document.getElementById("gd_gold_type")?.value || "",
    purity: document.getElementById("gd_purity")?.value || "",
    weight: parseFloat(document.getElementById("gd_weight")?.value) || 0,
    unit: document.getElementById("gd_unit")?.value || "gram",
    cashback_per_gram: parseFloat(document.getElementById("gd_cashback_per_gram")?.value) || 0,
    purchase_weight: parseFloat(document.getElementById("gd_purchase_weight")?.value) || 0,
  };
}

function collectOtherAssetDetailsPayload() {
  return {
    category: document.getElementById("od_category")?.value || "",
    manufacturer: document.getElementById("od_manufacturer")?.value || "",
    model: document.getElementById("od_model")?.value || "",
    serial_number: document.getElementById("od_serial_number")?.value || "",
    description: document.getElementById("od_description")?.value || "",
    warranty_expiry: document.getElementById("od_warranty_expiry")?.value || null,
    notes: document.getElementById("od_notes")?.value || "",
  };
}

function updateGoldValuation() {
  if (!isGoldAssetType(document.getElementById("fa_type")?.value)) {
    return;
  }
  refreshGoldCalculatedFields();
}

function addMaintenanceRow(data = {}) {
  const container = document.getElementById("maintenanceContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "row g-2 mb-3 maintenance-row";
  row.innerHTML = `
    <div class="col-md-3"><label class="form-label small" data-i18n="date">Date</label><input type="date" class="form-control maintenance-date" value="${data.date || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="type">Type</label><input type="text" class="form-control maintenance-type" value="${data.type || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="cost">Cost</label><input type="number" step="0.01" class="form-control maintenance-cost" value="${data.cost || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="notes">Notes</label><input type="text" class="form-control maintenance-notes" value="${data.notes || ""}"></div>
    <div class="col-md-1"><label class="form-label small">&nbsp;</label><button type="button" class="btn btn-danger w-100" onclick="this.closest('.maintenance-row').remove()"><i class="bi bi-trash"></i></button></div>
  `;
  container.appendChild(row);
  applyTranslations();
}

function collectMaintenance() {
  const items = [];
  document.querySelectorAll(".maintenance-row").forEach((row) => {
    const date = row.querySelector(".maintenance-date")?.value;
    if (!date) return;
    items.push({
      date,
      type: row.querySelector(".maintenance-type")?.value || "",
      cost: parseFloat(row.querySelector(".maintenance-cost")?.value) || 0,
      notes: row.querySelector(".maintenance-notes")?.value || "",
    });
  });
  return items;
}

function addInsuranceRow(data = {}) {
  const container = document.getElementById("insuranceContainer");
  if (!container) return;

  const insuranceId = data.id || null;
  const documentsButton = insuranceId
    ? `<button type="button" class="btn btn-outline-secondary w-100" onclick="openInsuranceDocumentsModal(${insuranceId})" data-i18n="documents_title">Documents</button>`
    : `<button type="button" class="btn btn-outline-secondary w-100" onclick="showToast(t('documents_save_first', 'Save this record first to manage documents.'), 'warning')" data-i18n="documents_title">Documents</button>`;

  const row = document.createElement("div");
  row.className = "row g-2 mb-3 insurance-row";
  row.innerHTML = `
    <div class="col-md-3"><label class="form-label small" data-i18n="company">Company</label><input type="text" class="form-control insurance-company" value="${data.company || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="policy_number">Policy Number</label><input type="text" class="form-control insurance-policy" value="${data.policy_number || ""}"></div>
    <div class="col-md-3"><label class="form-label small" data-i18n="expiry_date">Expiry Date</label><input type="date" class="form-control insurance-expiry" value="${data.expiry_date || ""}"></div>
    <div class="col-md-2"><label class="form-label small" data-i18n="premium">Premium</label><input type="number" step="0.01" class="form-control insurance-premium" value="${data.premium || ""}"></div>
    <div class="col-md-2"><label class="form-label small">&nbsp;</label>${documentsButton}</div>
    <div class="col-md-1"><label class="form-label small">&nbsp;</label><button type="button" class="btn btn-danger w-100" onclick="this.closest('.insurance-row').remove()"><i class="bi bi-trash"></i></button></div>
  `;
  container.appendChild(row);
  applyTranslations();
}

function openInsuranceDocumentsModal(insuranceId) {
  if (!insuranceId) {
    showToast(t("documents_save_first", "Save this record first to manage documents."), "warning");
    return;
  }

  showModal(`
    <div class="modal-header">
      <h5 class="modal-title" data-i18n="documents_title">${t("documents_title", "Documents")}</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
    </div>
    <div class="modal-body">
      <div id="insuranceDocumentManagerContainer"></div>
    </div>
    <div class="modal-footer">
      <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="close">${t("close", "Close")}</button>
    </div>
  `);
  applyTranslations();

  if (window.DocumentManager) {
    window.DocumentManager.init({
      containerId: "insuranceDocumentManagerContainer",
      parentType: "asset_insurance",
      parentId: insuranceId,
      disabledMessage: t("documents_save_first", "Save this record first to manage documents."),
    });
  }
}

function collectInsurance() {
  const items = [];
  document.querySelectorAll(".insurance-row").forEach((row) => {
    const company = row.querySelector(".insurance-company")?.value;
    if (!company) return;
    items.push({
      company,
      policy_number: row.querySelector(".insurance-policy")?.value || "",
      expiry_date: row.querySelector(".insurance-expiry")?.value || null,
      premium: parseFloat(row.querySelector(".insurance-premium")?.value) || 0,
    });
  });
  return items;
}

// ════════════════════════════════════════════════════════════════════════════
// GLOBAL ROUTER EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.renderFixedAssets = renderFixedAssets;
window.switchFixedAssetsTab = switchFixedAssetsTab;
window.toggleFixedAssetsReportScope = toggleFixedAssetsReportScope;
window.downloadFixedAssetsReport = downloadFixedAssetsReport;
window.showFixedAssetModal = showFixedAssetModal;
window.showGoldPurityGroupDetails = showGoldPurityGroupDetails;
window.openGoldPurchaseDetails = openGoldPurchaseDetails;
window.openGoldPurchaseEditor = openGoldPurchaseEditor;
window.deleteFixedAssetFromGoldGroup = deleteFixedAssetFromGoldGroup;
window.handleAssetWindowClose = handleAssetWindowClose;
window.clearGoldPurityReturnContext = clearGoldPurityReturnContext;
window.showSaleModal = showSaleModal;
window.openInsuranceDocumentsModal = openInsuranceDocumentsModal;
window.refreshPropertyValuation = refreshPropertyValuation;

if (window.location.hash === "#fixed-assets") {
  renderFixedAssets();
}
