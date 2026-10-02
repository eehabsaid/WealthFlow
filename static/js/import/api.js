"use strict";

let _importState = null; // { headers, rows, mapping }

async function handleImportFileSelected(input) {
  const file = input.files[0];
  if (!file) return;
  const mc = document.getElementById("importPreviewArea");
  mc.innerHTML =
    '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("/api/import/preview/", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    showToast(payload.error || t("error_import_preview", "Could not read the file"), "error");
    mc.innerHTML = "";
    return;
  }
  const data = await res.json();
  _importState = { headers: data.headers, rows: data.rows, mapping: data.suggested_mapping };
  renderImportPreview(data.sample_rows, data.total_rows);
}

async function confirmImport() {
  if (!_importState) return;
  const mapping = {
    date: document.getElementById("mapDate").value || null,
    amount: document.getElementById("mapAmount").value || null,
    description: document.getElementById("mapDescription").value || null,
    category: document.getElementById("mapCategory").value || null,
  };
  const currencyId = parseInt(document.getElementById("importCurrency").value) || null;
  const categoryId = parseInt(document.getElementById("importCategory").value) || null;
  const paymentMethod = document.getElementById("importMethod").value;
  const skipDuplicates = document.getElementById("importSkipDuplicates").checked;

  const res = await fetch("/api/import/confirm/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      rows: _importState.rows,
      mapping,
      currency_id: currencyId,
      category_id: categoryId,
      payment_method: paymentMethod,
      skip_duplicates: skipDuplicates,
    }),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    showToast(payload.error || t("error_import_confirm", "Import failed"), "error");
    return;
  }
  const result = await res.json();
  showToast(
    `${result.created_count} ${t("import_created_suffix", "imported")}, ${result.skipped_duplicate_count} ${t("import_skipped_suffix", "duplicates skipped")}, ${result.error_count} ${t("import_errors_suffix", "errors")}`,
    result.error_count ? "warning" : "success"
  );
  _importState = null;
  renderImportData();
  refreshFinancialViewsAfterExpenseChange();
}
