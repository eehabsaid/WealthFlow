"use strict";

function _importMappingSelect(id, headers, selected) {
  const opts = headers
    .map((h) => `<option value="${h}" ${h === selected ? "selected" : ""}>${h}</option>`)
    .join("");
  return `<select class="form-select form-select-sm" id="${id}"><option value="">—</option>${opts}</select>`;
}

function renderImportPreview(sampleRows, totalRows) {
  const area = document.getElementById("importPreviewArea");
  const { headers, mapping } = _importState;
  const curs = window._expCurrencies || [];
  const cats = window._expCategories || [];
  const curOpts = curs
    .map(
      (c) =>
        `<option value="${c.id}" ${c.code === baseCurrencyCode() ? "selected" : ""}>${c.flag} ${c.code}</option>`
    )
    .join("");
  const catOpts = cats.map((c) => `<option value="${c.id}">${c.icon} ${c.name}</option>`).join("");
  const methOpts = PAYMENT_METHODS.map(
    (m) => `<option value="${m.value}" data-i18n="${m.key}">${m.value}</option>`
  ).join("");

  const headerRow = headers.map((h) => `<th>${h}</th>`).join("");
  const bodyRows = sampleRows
    .map((r) => `<tr>${headers.map((h) => `<td>${r[h] ?? ""}</td>`).join("")}</tr>`)
    .join("");

  area.innerHTML = `
    <div class="card mb-3" style="background:var(--bg-secondary);border:1px solid var(--border-color)">
      <div class="card-body">
        <h6 data-i18n="import_column_mapping">Column mapping</h6>
        <div class="row g-2">
          <div class="col-3">
            <label class="form-label" data-i18n="import_map_date">Date column</label>
            ${_importMappingSelect("mapDate", headers, mapping.date)}
          </div>
          <div class="col-3">
            <label class="form-label" data-i18n="import_map_amount">Amount column</label>
            ${_importMappingSelect("mapAmount", headers, mapping.amount)}
          </div>
          <div class="col-3">
            <label class="form-label" data-i18n="import_map_description">Description column</label>
            ${_importMappingSelect("mapDescription", headers, mapping.description)}
          </div>
          <div class="col-3">
            <label class="form-label" data-i18n="import_map_category">Category column (optional)</label>
            ${_importMappingSelect("mapCategory", headers, mapping.category)}
          </div>
        </div>
        <div class="row g-2 mt-1">
          <div class="col-3">
            <label class="form-label" data-i18n="budget_currency">Currency</label>
            <select class="form-select form-select-sm" id="importCurrency">${curOpts}</select>
          </div>
          <div class="col-3">
            <label class="form-label" data-i18n="budget_category">Default category</label>
            <select class="form-select form-select-sm" id="importCategory">${catOpts}</select>
          </div>
          <div class="col-3">
            <label class="form-label" data-i18n="payment_method">Payment method</label>
            <select class="form-select form-select-sm" id="importMethod">${methOpts}</select>
          </div>
          <div class="col-3 d-flex align-items-end">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" id="importSkipDuplicates" checked>
              <label class="form-check-label" data-i18n="import_skip_duplicates">Skip likely duplicates</label>
            </div>
          </div>
        </div>
        <p class="text-secondary mt-2" style="font-size:12px">
          <span data-i18n="import_showing_sample">Showing sample of</span> ${sampleRows.length} / ${totalRows} <span data-i18n="import_rows_label">rows</span>
        </p>
        <div class="table-responsive" style="max-height:300px">
          <table class="table table-sm"><thead><tr>${headerRow}</tr></thead><tbody>${bodyRows}</tbody></table>
        </div>
        <button class="btn btn-primary mt-2" onclick="confirmImport()" data-i18n="btn_confirm_import">Confirm Import</button>
      </div>
    </div>`;
  applyTranslations();
}

async function renderImportData() {
  const mc = document.getElementById("main-content");
  const [catRes, curRes] = await Promise.all([
    fetch("/api/expense-categories/"),
    fetch("/api/currencies/"),
  ]);
  window._expCategories = (await catRes.json()).categories || [];
  window._expCurrencies = (await curRes.json()).currencies || [];
  _importState = null;

  mc.innerHTML = `
    <div class="container-fluid p-3">
      <h5 data-i18n="nav_import_data">Import Data</h5>
      <p class="text-secondary" data-i18n="import_intro">Upload a CSV or Excel export from your bank or another app. No live bank connection is used.</p>
      <div class="mb-3">
        <input type="file" class="form-control" accept=".csv,.txt,.xlsx,.xls" onchange="handleImportFileSelected(this)">
      </div>
      <div id="importPreviewArea"></div>
    </div>`;
  applyTranslations();
}
