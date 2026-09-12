// Scanner references: _t('furniture_living_room'), _t('furniture_bedroom'), _t('furniture_kitchen'), _t('furniture_bathroom'), _t('furniture_dining_room'), _t('furniture_office'), _t('furniture_outdoor'), _t('furniture_air_conditioner'), _t('furniture_refrigerator'), _t('furniture_freezer'), _t('furniture_cooker'), _t('furniture_oven'), _t('furniture_range_hood'), _t('furniture_microwave'), _t('furniture_dishwasher'), _t('furniture_washing_machine'), _t('furniture_water_heater'), _t('furniture_water_dispenser'), _t('furniture_tv'), _t('furniture_ceiling_fan'), _t('furniture_router'), _t('furniture_vacuum_cleaner'), _t('furniture_water_pump'), _t('furniture_generator'), _t('furniture_other_appliance'), _t('furniture_other')

let furnitureCategories = [];

// Fetch categories from backend API
fetch("/api/asset-furniture/categories/")
  .then((res) => res.json())
  .then((data) => {
    if (data && data.categories && data.categories.length) {
      furnitureCategories = data.categories;
    }
  })
  .catch(() => {});

function updateFurnitureSummary() {
  const summaryStrip = document.getElementById("furnitureSummaryStrip");
  const badge = document.getElementById("furniture-count-badge");

  const rows = document.querySelectorAll(".furniture-row");
  const count = rows.length;

  if (badge) {
    badge.textContent = count > 0 ? `(${count})` : "";
  }

  let totalEGP = 0;
  let totalUSD = 0;

  rows.forEach((row) => {
    const egp = parseFloat(row.querySelector(".furniture-egp").value) || 0;
    const qty = parseInt(row.querySelector(".furniture-quantity").value) || 1;
    const usd = parseFloat(row.querySelector(".furniture-usd").value) || 0;
    totalEGP += egp * qty;
    totalUSD += usd;
  });

  const fmt = (n) =>
    Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  if (summaryStrip) {
    summaryStrip.innerHTML = `
      <div class="stat">
        <span class="stat-label" data-i18n="items">Items</span>
        <span class="stat-value">${count}</span>
      </div>
      <div class="stat">
        <span class="stat-label" data-i18n="total_egp">Total (EGP)</span>
        <span class="stat-value">${fmt(totalEGP)}</span>
      </div>
      <div class="stat">
        <span class="stat-label" data-i18n="total_usd">Total (USD)</span>
        <span class="stat-value">${fmt(totalUSD)}</span>
      </div>
    `;
    if (typeof applyTranslations === "function") {
      applyTranslations();
    }
  }
}

function collectFurniture() {
  const furniture = [];
  document.querySelectorAll(".furniture-row").forEach((row) => {
    const name = row.querySelector(".furniture-name").value;
    if (!name) return;
    furniture.push({
      id: row.dataset.furnitureId ? parseInt(row.dataset.furnitureId, 10) : null,
      name,
      category: row.querySelector(".furniture-category").value,
      purchase_date: row.querySelector(".furniture-purchase-date").value || null,
      amount_egp: parseFloat(row.querySelector(".furniture-egp").value) || 0,
      usd_rate: parseFloat(row.querySelector(".furniture-usd-rate").value) || 0,
      amount_usd: parseFloat(row.querySelector(".furniture-usd").value) || 0,
      quantity: parseInt(row.querySelector(".furniture-quantity").value, 10) || 1,
      payment_method: row.querySelector(".furniture-payment-method")?.value || "Cash",
      bank_id: parseInt(row.querySelector(".furniture-bank")?.value, 10) || null,
      notes: row.querySelector(".furniture-notes").value,
    });
  });
  return furniture;
}
