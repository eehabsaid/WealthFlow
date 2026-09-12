// companies.js — All Companies management page (actions)

"use strict";

async function saveCompany(companyId) {
  const body = {
    name: document.getElementById("cName").value,
    display_name: document.getElementById("cDisplayName").value,
    group_name: document.getElementById("cGroupName").value,
    color_hex: document.getElementById("cColor").value,
    order: parseInt(document.getElementById("cOrder").value) || 0,
    is_active: document.getElementById("cActive").checked,
    current_salary_amount: parseFloat(document.getElementById("cSalaryAmount").value) || 0,
    current_salary_currency_id: document.getElementById("cSalaryCurrency").value
      ? parseInt(document.getElementById("cSalaryCurrency").value)
      : null,
    payment_day: parseInt(document.getElementById("cPaymentDay").value) || 25,
    default_bank_id: document.getElementById("cDefaultBank").value
      ? parseInt(document.getElementById("cDefaultBank").value)
      : null,
    per_diem_amount: parseFloat(document.getElementById("cPerDiemAmount").value) || 0,
    per_diem_currency_id: document.getElementById("cPerDiemCurrency").value
      ? parseInt(document.getElementById("cPerDiemCurrency").value)
      : null,
    bonus_amount: parseFloat(document.getElementById("cBonusAmount").value) || 0,
    payroll_notes: document.getElementById("cPayrollNotes").value,
  };

  if (!body.name.trim()) {
    showToast(t("validation_company_name_required", "Please enter a company name"), "error");
    return;
  }

  const url = companyId ? `/api/companies/${companyId}/` : "/api/companies/";
  const method = companyId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    closeModal();
    await refreshCompanies();
    renderAllCompanies();
    renderSidebar();
    const successMsg = companyId
      ? t("msg_updated", "Updated successfully")
      : t("msg_created", "Created successfully");
    showToast(successMsg, "success");
  } else {
    showToast(t("error_saving_company", "Error saving company"), "error");
  }
}

async function deleteCompany(companyId) {
  const confirmMsg = t("confirm_delete_company", "Are you sure you want to delete this company?");
  if (!confirm(confirmMsg)) return;

  const res = await fetch(`/api/companies/${companyId}/`, { method: "DELETE" });
  if (res.ok) {
    await refreshCompanies();
    renderAllCompanies();
    renderSidebar();
    showToast(t("msg_deleted", "Company deleted"), "success");
  } else {
    showToast(t("error_deleting_company", "Error deleting company"), "error");
  }
}
