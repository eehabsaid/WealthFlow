"use strict";
// Company configuration settings — actions
// This file is part of the settings module. Do not edit directly.

async function updateCompanyColor(id, color) {
  await fetch(`/api/companies/${id}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ color_hex: color }),
  });
  window._companies = (window._companies || []).map((c) =>
    c.id === id ? { ...c, color_hex: color } : c
  );
  renderSidebar();
}

async function saveCompany(companyId) {
  const body = {
    name: document.getElementById("cName").value,
    display_name: document.getElementById("cDisplay").value,
    group_name: document.getElementById("cGroup").value,
    color_hex: document.getElementById("cColor").value,
    order: parseInt(document.getElementById("cOrder").value) || 0,
    is_active: document.getElementById("cActive").value === "true",
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
  const res = await fetch(companyId ? `/api/companies/${companyId}/` : "/api/companies/", {
    method: companyId ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    closeModal();
    showToast("Company saved ✓");
    const cRes = await fetch("/api/companies/");
    window._companies = (await cRes.json()).companies;
    renderSidebar();
    renderCompanySettings();
  } else showToast("Error", "error");
}

async function deleteCompany(id) {
  if (!confirm("Delete company? This will also delete all salary entries!")) return;
  await fetch(`/api/companies/${id}/`, { method: "DELETE" });
  showToast("Deleted");
  const cRes = await fetch("/api/companies/");
  window._companies = (await cRes.json()).companies;
  renderSidebar();
  renderCompanySettings();
}

// ════════════════════════════════════════════════════════════════════════════
// BANK SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════
