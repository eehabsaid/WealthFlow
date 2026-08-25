// Scanner references: _t('furniture_living_room'), _t('furniture_bedroom'), _t('furniture_kitchen'), _t('furniture_bathroom'), _t('furniture_dining_room'), _t('furniture_office'), _t('furniture_outdoor'), _t('furniture_air_conditioner'), _t('furniture_refrigerator'), _t('furniture_freezer'), _t('furniture_cooker'), _t('furniture_oven'), _t('furniture_range_hood'), _t('furniture_microwave'), _t('furniture_dishwasher'), _t('furniture_washing_machine'), _t('furniture_water_heater'), _t('furniture_water_dispenser'), _t('furniture_tv'), _t('furniture_ceiling_fan'), _t('furniture_router'), _t('furniture_vacuum_cleaner'), _t('furniture_water_pump'), _t('furniture_generator'), _t('furniture_other_appliance'), _t('furniture_other')

let furnitureCategories = [];

// Fetch categories from backend API
fetch("/api/asset-furniture/categories/")
  .then(res => res.json())
  .then(data => {
    if (data && data.categories && data.categories.length) {
      furnitureCategories = data.categories;
    }
  })
  .catch(err => console.error("Error fetching furniture categories:", err));

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

  rows.forEach(row => {
    const egp = parseFloat(row.querySelector(".furniture-egp").value) || 0;
    const qty = parseInt(row.querySelector(".furniture-quantity").value) || 1;
    const usd = parseFloat(row.querySelector(".furniture-usd").value) || 0;
    totalEGP += (egp * qty);
    totalUSD += usd;
  });

  const fmt = (n) => Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

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

function addFurnitureRow(data = {}, expand = false) {
  const container = document.getElementById("furnitureContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "furniture-row item-card card";
  row.dataset.furnitureId = data.id || "";

  const category = data.category || "Living Room";
  const normVal = category.toLowerCase().replace(/ & /g, '_').replace(/ /g, '_');
  const quantity = (parseInt(data.quantity) || 1);
  const amountEgpVal = data.amount_egp || 0; // Use raw amount
  const nameVal = data.name || "";
  const paymentMethodVal = data.payment_method || "Cash";
  const bankIdVal = data.bank_id || "";

  const fmt = (n) => Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const initialAmountPreview = amountEgpVal ? `EGP ${fmt(parseFloat(amountEgpVal) || 0)}` : "EGP 0.00";

  row.innerHTML = `
    <div class="item-header card-header">
      <div class="item-header-left">
        <svg class="item-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
        <span class="item-name-preview">${nameVal || t("unnamed_item", "(Unnamed item)")}</span>
        <span class="item-category-badge" data-i18n-prefix="furniture_" data-i18n-value="${normVal}">${category}</span>
      </div>
      <div class="item-header-right">
        <span class="item-amount-preview">${initialAmountPreview}</span>
        <button type="button" class="item-remove-btn" title="Remove" onclick="const r = this.closest('.furniture-row'); r.remove(); updateFurnitureSummary();">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z"/></svg>
        </button>
      </div>
    </div>
    <div class="item-body card-body">
      <div class="field-grid">
        <div class="field">
          <label class="form-label small" data-i18n="asset_name">Item Name</label>
          <input type="text" class="form-control furniture-name" value="${nameVal}">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="category">Category</label>
          <select class="form-select furniture-category">
            ${furnitureCategories.map(cat => {
              const norm = cat.toLowerCase().replace(/ & /g, '_').replace(/ /g, '_');
              return `
                <option value="${cat}" data-i18n-prefix="furniture_" data-i18n-value="${norm}" ${cat === category ? "selected" : ""}>
                  ${cat}
                </option>
              `;
            }).join("")}
          </select>
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="purchase_date">Purchase Date</label>
          <input type="date" class="form-control furniture-purchase-date" value="${data.purchase_date || ""}">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="quantity">Quantity</label>
          <input type="number" step="1" min="0" class="form-control furniture-quantity" value="${data.quantity || 1}" oninput="updateFurnitureUSD(this)">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="amount_egp">Amount</label>
          <input type="number" step="0.01" min="0" class="form-control furniture-egp" value="${amountEgpVal}" oninput="updateFurnitureUSD(this)">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="purchase_usd_rate">USD Exchange Rate</label>
          <input type="number" step="0.0001" min="0" class="form-control furniture-usd-rate" value="${data.usd_rate || document.getElementById("fa_purchase_usd_rate")?.value || ""}" oninput="updateFurnitureUSD(this)">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="amount_usd">Amount USD</label>
          <input type="number" step="0.01" class="form-control furniture-usd" value="${data.amount_usd || ""}" readonly>
        </div>
        ${renderMoneyMovementFields("furniture", paymentMethodVal, bankIdVal)}
        <div class="field span-4">
          <label class="form-label small" data-i18n="notes">Notes</label>
          <textarea class="form-control furniture-notes" rows="2">${data.notes || ""}</textarea>
        </div>
      </div>
    </div>
  `;

  if (expand) {
    container.prepend(row);
    row.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } else {
    container.appendChild(row);
  }

  // Initialize event listeners on new row inputs
  const nameInput = row.querySelector(".furniture-name");
  const namePreview = row.querySelector(".item-name-preview");
  nameInput.addEventListener("input", () => {
    namePreview.textContent = nameInput.value.trim() || t("unnamed_item", "(Unnamed item)");
  });

  const categorySelect = row.querySelector(".furniture-category");
  const categoryBadge = row.querySelector(".item-category-badge");
  categorySelect.addEventListener("change", () => {
    const cat = categorySelect.value;
    const norm = cat.toLowerCase().replace(/ & /g, '_').replace(/ /g, '_');
    categoryBadge.setAttribute("data-i18n-value", norm);
    categoryBadge.textContent = cat;
    if (typeof applyTranslations === "function") {
      applyTranslations();
    }
  });

  const egpInput = row.querySelector(".furniture-egp");
  const amountPreview = row.querySelector(".item-amount-preview");
  egpInput.addEventListener("input", () => {
    amountPreview.textContent = `EGP ${fmt(parseFloat(egpInput.value) || 0)}`;
    updateFurnitureUSD(egpInput);
    updateFurnitureSummary();
  });

  const rateInput = row.querySelector(".furniture-usd-rate");
  rateInput.addEventListener("input", () => {
    updateFurnitureUSD(rateInput);
    updateFurnitureSummary();
  });

  toggleMoneyMovementBankField(row.querySelector(".furniture-payment-method"), "furniture");

  // Reusable card accordion init
  initCollapsibleCard(row, "#furnitureContainer");

  // Initial expansion state
  const isFirstCard = container.children.length === 1;
  const shouldExpand = expand;
  toggleCollapsibleCard(row, "#furnitureContainer", shouldExpand);

  // Auto-calc USD amount if input has initial EGP amount
  if (amountEgpVal) {
    updateFurnitureUSD(egpInput);
  }

  // Translate labels inside the new row
  if (typeof applyTranslations === "function") {
    applyTranslations();
  }

  // Update summary totals
  updateFurnitureSummary();
}

function updateFurnitureUSD(input) {
  const row = input.closest(".furniture-row");
  if (!row) return;

  const egpInput = row.querySelector(".furniture-egp");
  const rateInput = row.querySelector(".furniture-usd-rate");
  const qtyInput = row.querySelector(".furniture-quantity");
  const usdInput = row.querySelector(".furniture-usd");
  const amountPreview = row.querySelector(".item-amount-preview");

  // --- VALIDATION: SANITIZE INPUTS ---
  // If input is negative, reset to allowed minimum (0 for amount/rate, 1 for quantity)
  if (parseFloat(egpInput.value) < 0) egpInput.value = 0;
  if (parseFloat(rateInput.value) < 0) rateInput.value = 0;
  if (parseInt(qtyInput.value) < 0) qtyInput.value = 1;
  // ------------------------------------

  const fmt = (n) => Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // 1. Get live values
  const egp = parseFloat(egpInput.value) || 0;
  const rate = parseFloat(rateInput.value) || 0;
  const quantity = parseInt(qtyInput.value) || 1;

  // 2. Perform the math
  const totalEgp = egp * quantity;
  const totalUsd = rate > 0 ? (totalEgp / rate) : 0;

  // 3. Update UI
  usdInput.value = totalUsd.toFixed(2);
  amountPreview.textContent = `EGP ${fmt(totalEgp)}`;
  
  // 4. Update Header Badge
  const headerPreview = row.querySelector(".item-header-right .item-amount-preview");
  if (headerPreview) {
      headerPreview.textContent = `EGP ${fmt(totalEgp)}`;
  }

  updateFurnitureSummary();
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

