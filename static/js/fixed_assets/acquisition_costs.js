// Scanner references: _t('acquisition_lawyer_fees'), _t('acquisition_registration_fees'), _t('acquisition_notary_fees'), _t('acquisition_government_fees'), _t('acquisition_utility_transfer_fees'), _t('acquisition_brokerage_fees'), _t('acquisition_other')

let acquisitionCategories = [];

// Fetch categories from backend API
fetch("/api/asset-acquisition-costs/categories/")
  .then((res) => res.json())
  .then((data) => {
    if (data && data.categories && data.categories.length) {
      acquisitionCategories = data.categories;
    }
  })
  .catch(() => {});

function updateAcquisitionSummary() {
  const summaryStrip = document.getElementById("acquisitionSummaryStrip");
  const badge = document.getElementById("acquisition-count-badge");

  const rows = document.querySelectorAll(".acquisition-row");
  const count = rows.length;

  if (badge) {
    badge.textContent = count > 0 ? `(${count})` : "";
  }

  let totalEGP = 0;
  let totalUSD = 0;

  rows.forEach((row) => {
    const egp = parseFloat(row.querySelector(".acquisition-egp").value) || 0;
    const usd = parseFloat(row.querySelector(".acquisition-usd").value) || 0;
    totalEGP += egp;
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

function addAcquisitionRow(data = {}, expand = false) {
  const container = document.getElementById("acquisitionContainer");
  if (!container) return;

  const row = document.createElement("div");
  row.className = "acquisition-row item-card card";
  row.dataset.acquisitionId = data.id || "";

  const category = data.category || "Lawyer Fees";
  const normVal = category.toLowerCase().replace(/ & /g, "_").replace(/ /g, "_");
  const amountEgpVal = data.amount_egp || "";
  const descVal = data.description || "";
  const paymentMethodVal = data.payment_method || "Cash";
  const bankIdVal = data.bank_id || "";

  const fmt = (n) =>
    Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const initialAmountPreview = amountEgpVal
    ? `EGP ${fmt(parseFloat(amountEgpVal) || 0)}`
    : "EGP 0.00";

  row.innerHTML = `
    <div class="item-header card-header">
      <div class="item-header-left">
        <svg class="item-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
        <span class="item-category-badge" data-i18n-prefix="acquisition_" data-i18n-value="${normVal}">${category}</span>
        <span class="item-name-preview">${descVal || t("unnamed_item", "(Unnamed item)")}</span>
      </div>
      <div class="item-header-right">
        <span class="item-amount-preview">${initialAmountPreview}</span>
        <button type="button" class="item-remove-btn" title="Remove" onclick="const r = this.closest('.acquisition-row'); r.remove(); updateAcquisitionSummary();">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z"/></svg>
        </button>
      </div>
    </div>
    <div class="item-body card-body">
      <div class="field-grid">
        <div class="field">
          <label class="form-label small" data-i18n="acquisition_date">Date</label>
          <input type="date" class="form-control acquisition-date" value="${data.date || ""}">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="acquisition_type">Category</label>
          <select class="form-select acquisition-category">
            ${acquisitionCategories
              .map((cat) => {
                const norm = cat.toLowerCase().replace(/ & /g, "_").replace(/ /g, "_");
                return `
                <option value="${cat}" data-i18n-prefix="acquisition_" data-i18n-value="${norm}" ${cat === category ? "selected" : ""}>
                  ${cat}
                </option>
              `;
              })
              .join("")}
          </select>
        </div>
        <div class="field span-2">
          <label class="form-label small" data-i18n="description">Description</label>
          <input type="text" class="form-control acquisition-description" data-i18n-placeholder="description" placeholder="Description" value="${descVal}">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="amount">Amount</label>
          <input type="number" step="0.01" class="form-control acquisition-egp" value="${amountEgpVal}" oninput="updateAcquisitionUSD(this)">
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="purchase_usd_rate">USD Exchange Rate</label>
          <div class="input-group">
            <input type="number" step="0.00001" min="0" class="form-control acquisition-usd-rate" value="${data.usd_rate || document.getElementById("fa_purchase_usd_rate")?.value || ""}" oninput="updateAcquisitionUSD(this)">
            <button type="button" class="btn btn-outline-secondary" onclick="fillRowUsdRateNow(this, '.acquisition-usd-rate', updateAcquisitionUSD)" data-i18n="current_rate_btn">Now</button>
          </div>
        </div>
        <div class="field">
          <label class="form-label small" data-i18n="amount_usd">USD</label>
          <input type="number" step="0.01" class="form-control acquisition-usd" value="${data.amount_usd || ""}" readonly>
        </div>
        ${renderMoneyMovementFields("acquisition", paymentMethodVal, bankIdVal)}
        <div class="field span-4">
          <label class="form-label small" data-i18n="notes">Notes</label>
          <textarea class="form-control acquisition-notes" rows="2">${data.notes || ""}</textarea>
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
  const descInput = row.querySelector(".acquisition-description");
  const descPreview = row.querySelector(".item-name-preview");
  descInput.addEventListener("input", () => {
    descPreview.textContent = descInput.value.trim() || t("unnamed_item", "(Unnamed item)");
  });

  const categorySelect = row.querySelector(".acquisition-category");
  const categoryBadge = row.querySelector(".item-category-badge");
  categorySelect.addEventListener("change", () => {
    const cat = categorySelect.value;
    const norm = cat.toLowerCase().replace(/ & /g, "_").replace(/ /g, "_");
    categoryBadge.setAttribute("data-i18n-value", norm);
    categoryBadge.textContent = cat;
    if (typeof applyTranslations === "function") {
      applyTranslations();
    }
  });

  const egpInput = row.querySelector(".acquisition-egp");
  const amountPreview = row.querySelector(".item-amount-preview");
  egpInput.addEventListener("input", () => {
    updateAcquisitionUSD(egpInput);
    amountPreview.textContent = `EGP ${fmt(parseFloat(egpInput.value) || 0)}`;
    updateAcquisitionSummary();
  });

  toggleMoneyMovementBankField(row.querySelector(".acquisition-payment-method"), "acquisition");

  // Reusable card accordion init
  initCollapsibleCard(row, "#acquisitionContainer");

  // Initial expansion state
  const isFirstCard = container.children.length === 1;
  const shouldExpand = expand;
  toggleCollapsibleCard(row, "#acquisitionContainer", shouldExpand);

  // Auto-calc USD amount if input has initial EGP amount
  if (amountEgpVal) {
    updateAcquisitionUSD(egpInput);
  }

  // Translate labels inside the new row
  if (typeof applyTranslations === "function") {
    applyTranslations();
  }

  // Update summary totals
  updateAcquisitionSummary();
}

function collectAcquisitionCosts() {
  const costs = [];

  document.querySelectorAll(".acquisition-row").forEach((row) => {
    costs.push({
      id: row.dataset.acquisitionId ? parseInt(row.dataset.acquisitionId, 10) : null,
      date: row.querySelector(".acquisition-date").value,
      category: row.querySelector(".acquisition-category").value,
      description: row.querySelector(".acquisition-description").value,
      amount_egp: parseFloat(row.querySelector(".acquisition-egp").value) || 0,
      usd_rate: parseFloat(row.querySelector(".acquisition-usd-rate")?.value) || 0,
      amount_usd: parseFloat(row.querySelector(".acquisition-usd").value) || 0,
      payment_method: row.querySelector(".acquisition-payment-method")?.value || "Cash",
      bank_id: parseInt(row.querySelector(".acquisition-bank")?.value, 10) || null,
      notes: row.querySelector(".acquisition-notes").value,
    });
  });

  return costs;
}

function updateAcquisitionUSD(input) {
  const row = input.closest(".acquisition-row");
  const egp = parseFloat(row.querySelector(".acquisition-egp").value) || 0;
  const rate = parseFloat(row.querySelector(".acquisition-usd-rate")?.value) || 0;
  const usdInput = row.querySelector(".acquisition-usd");

  if (rate > 0) {
    usdInput.value = (egp / rate).toFixed(2);
  } else {
    usdInput.value = "";
  }
}
