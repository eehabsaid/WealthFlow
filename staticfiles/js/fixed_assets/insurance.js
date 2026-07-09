"use strict";
// Insurance rows management and documents modal
// This file is part of the fixed_assets module. Do not edit directly.

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

