// Scanner references: _t('renovation_finishing'), _t('renovation_painting'), _t('renovation_flooring'), _t('renovation_kitchen'), _t('renovation_bathroom'), _t('renovation_electrical'), _t('renovation_plumbing'), _t('renovation_doors_windows'), _t('renovation_furniture'), _t('renovation_landscape'), _t('renovation_maintenance'), _t('renovation_flooring_ceramic'), _t('renovation_wall_tiles'), _t('renovation_other')

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
                ${renovationCategories.map(cat => {
                    const normVal = cat.toLowerCase().replace(/ & /g, '_').replace(/ /g, '_');
                    return `
                        <option value="${cat}" data-i18n-prefix="renovation_" data-i18n-value="${normVal}">
                            ${cat}
                        </option>
                    `;
                }).join("")}
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

