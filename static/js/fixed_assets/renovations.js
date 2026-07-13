// Scanner references: _t('renovation_finishing'), _t('renovation_painting'), _t('renovation_flooring'), _t('renovation_kitchen'), _t('renovation_bathroom'), _t('renovation_electrical'), _t('renovation_plumbing'), _t('renovation_doors_windows'), _t('renovation_furniture'), _t('renovation_landscape'), _t('renovation_maintenance'), _t('renovation_flooring_ceramic'), _t('renovation_wall_tiles'), _t('renovation_alumital_windows'), _t('renovation_other')

let renovationCategories = [];

// Fetch categories from backend API
fetch("/api/asset-renovations/categories/")
  .then(res => res.json())
  .then(data => {
    if (data && data.categories && data.categories.length) {
      renovationCategories = data.categories;
    }
  })
  .catch(err => console.error("Error fetching renovation categories:", err));

function updateRenovationSummary() {
  const summaryStrip = document.getElementById("renovationSummaryStrip");
  const badge = document.getElementById("renovation-count-badge");

  const rows = document.querySelectorAll(".renovation-row");
  const count = rows.length;

  if (badge) {
    badge.textContent = count > 0 ? `(${count})` : "";
  }

  let totalEGP = 0;
  let totalUSD = 0;

  rows.forEach(row => {
    const egp = parseFloat(row.querySelector(".renovation-egp").value) || 0;
    const usd = parseFloat(row.querySelector(".renovation-usd").value) || 0;
    totalEGP += egp;
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

function addRenovationRow(data = {}, expand = false) {
  const container = document.getElementById("renovationContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "renovation-row item-card card";

  const category = data.category || "Finishing";
  const normVal = category.toLowerCase().replace(/ & /g, '_').replace(/ /g, '_');
  const amountEgpVal = data.amount_egp || "";
  const descVal = data.description || "";

  const fmt = (n) => Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const initialAmountPreview = amountEgpVal ? `EGP ${fmt(parseFloat(amountEgpVal) || 0)}` : "EGP 0.00";

  row.innerHTML = `
    <div class="item-header card-header">
      <div class="item-header-left">
        <svg class="item-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
        <span class="item-category-badge" data-i18n-prefix="renovation_" data-i18n-value="${normVal}">${category}</span>
        <span class="item-name-preview">${descVal || t("unnamed_item", "(Unnamed item)")}</span>
      </div>
      <div class="item-header-right">
        <span class="item-amount-preview">${initialAmountPreview}</span>
        <button type="button" class="item-remove-btn" title="Remove" onclick="const r = this.closest('.renovation-row'); r.remove(); updateRenovationSummary();">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z"/></svg>
        </button>
      </div>
    </div>
    <div class="item-body card-body">
      <div class="field-grid">
        <div class="field">
          <label class="form-label small" data-i18n="renovation_date">Date</label>
          <input type="date" class="form-control renovation-date" value="${data.date || ""}">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="renovation_type">Renovation Type</label>
          <select class="form-select renovation-category">
            ${renovationCategories.map(cat => {
              const norm = cat.toLowerCase().replace(/ & /g, '_').replace(/ /g, '_');
              return `
                <option value="${cat}" data-i18n-prefix="renovation_" data-i18n-value="${norm}" ${cat === category ? "selected" : ""}>
                  ${cat}
                </option>
              `;
            }).join("")}
          </select>
        </div>
        <div class="field span-2">
          <label class="form-label small" data-i18n="description">Description</label>
          <input type="text" class="form-control renovation-description" data-i18n-placeholder="description" placeholder="Description" value="${descVal}">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="amount">Amount</label>
          <input type="number" step="0.01" class="form-control renovation-egp" value="${amountEgpVal}" oninput="updateRenovationUSD(this)">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="amount_usd">USD</label>
          <input type="number" step="0.01" class="form-control renovation-usd" value="${data.amount_usd || ""}" readonly>
        </div>
        <div class="field span-2">
          <label class="form-label small">&nbsp;</label>
        </div>
        <div class="field span-4">
          <label class="form-label small" data-i18n="notes">Notes</label>
          <textarea class="form-control renovation-notes" rows="2">${data.notes || ""}</textarea>
        </div>
      </div>
    </div>
  `;

  container.appendChild(row);

  // Initialize event listeners on new row inputs
  const descInput = row.querySelector(".renovation-description");
  const descPreview = row.querySelector(".item-name-preview");
  descInput.addEventListener("input", () => {
    descPreview.textContent = descInput.value.trim() || t("unnamed_item", "(Unnamed item)");
  });

  const categorySelect = row.querySelector(".renovation-category");
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

  const egpInput = row.querySelector(".renovation-egp");
  const amountPreview = row.querySelector(".item-amount-preview");
  egpInput.addEventListener("input", () => {
    updateRenovationUSD(egpInput);
    amountPreview.textContent = `EGP ${fmt(parseFloat(egpInput.value) || 0)}`;
    updateRenovationSummary();
  });

  // Reusable card accordion init
  initCollapsibleCard(row, "#renovationContainer");

  // Initial expansion state
  const isFirstCard = container.children.length === 1;
  const shouldExpand = expand;
  toggleCollapsibleCard(row, "#renovationContainer", shouldExpand);

  // Auto-calc USD amount if input has initial EGP amount
  if (amountEgpVal) {
    updateRenovationUSD(egpInput);
  }

  // Translate labels inside the new row
  if (typeof applyTranslations === "function") {
    applyTranslations();
  }

  // Update summary totals
  updateRenovationSummary();
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

