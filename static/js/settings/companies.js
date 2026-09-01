"use strict";
// Company configuration settings
// This file is part of the settings module. Do not edit directly.

async function renderCompanySettings() {
  const res = await fetch("/api/companies/");
  const { companies = [] } = await res.json();

  const rows = companies
    .map(
      (c) => `
        <tr>
            <td>
                <span style="background:${c.color_hex};width:12px;height:12px;border-radius:3px;
                             display:inline-block;margin-right:8px"></span>${c.name}
            </td>
            <td>${c.display_name}</td>
            <td><span class="group-badge">${c.group_name || "—"}</span></td>
            <td>
                <input type="color" value="${c.color_hex}"
                    onchange="updateCompanyColor(${c.id}, this.value)"
                    style="background:none;border:none;width:32px;height:32px;cursor:pointer">
            </td>
            <td>${c.order}</td>
            <td>
                <span style="color:${c.is_active ? "var(--accent-green)" : "var(--accent-red)"}"
                    data-i18n="${c.is_active ? "active" : "inactive"}">
                </span>
            </td>
            <td>
                <button class="btn-icon" onclick="showCompanyModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteCompany(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`
    )
    .join("");

  const contentEl = document.getElementById("settingsContent");
  if (!contentEl) return;
  contentEl.innerHTML = `
        <div style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:14px">
            
            <button class="btn-primary-custom" onclick="showCompanyModal(null)" data-i18n="btn_add">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="company_name">Name</th>
                    <th data-i18n="company_display_name">Display Name</th>
                    <th data-i18n="group_name">Group</th>
                    <th data-i18n="color">Color</th>
                    <th data-i18n="order">Order</th>
                    <th data-i18n="active">Active</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
  applyTranslations();
}

async function showCompanyModal(companyId) {
  const [cRes, bRes, compRes] = await Promise.all([
    fetch("/api/currencies/"),
    fetch("/api/banks/"),
    companyId ? fetch(`/api/companies/${companyId}/`) : Promise.resolve(null),
  ]);
  const currData = await cRes.json();
  const bankData = await bRes.json();
  const currencies = currData.currencies || [];
  const banks = bankData.banks || [];
  const c = compRes ? await compRes.json() : null;

  const noneText = t("none_option", "— None —");
  const selectCurText = t("select_currency_option", "— Select currency —");

  const bankOpts = banks
    .map(
      (b) =>
        `<option value="${b.id}" ${c && c.default_bank_id === b.id ? "selected" : ""}>${b.name}</option>`
    )
    .join("");
  const currencyOpts = currencies
    .map(
      (curr) =>
        `<option value="${curr.id}" ${c && c.current_salary_currency_id === curr.id ? "selected" : ""}>${curr.flag} ${curr.code}</option>`
    )
    .join("");
  const currencyOpts2 = currencies
    .map(
      (curr) =>
        `<option value="${curr.id}" ${c && c.per_diem_currency_id === curr.id ? "selected" : ""}>${curr.flag} ${curr.code}</option>`
    )
    .join("");

  showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${c ? "edit_company" : "add_company"}">${c ? "Edit Company" : "Add Company"}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="company_name">Name</label>
                    <input class="form-control" id="cName" value="${c?.name || ""}">
                </div>
                <div class="col-6">
                    <label data-i18n="company_display_name">Display Name</label>
                    <input class="form-control" id="cDisplay" value="${c?.display_name || ""}">
                </div>
                <div class="col-6">
                    <label data-i18n="group_name">Group Name</label>
                    <input class="form-control" id="cGroup" value="${c?.group_name || ""}">
                </div>
                <div class="col-3">
                    <label data-i18n="color">Color</label>
                    <input type="color" class="form-control" id="cColor" value="${c?.color_hex || "#0d6efd"}">
                </div>
                <div class="col-3">
                    <label data-i18n="order">Order</label>
                    <input type="number" class="form-control" id="cOrder" value="${c?.order ?? 0}">
                </div>
                <div class="col-12">
                    <label data-i18n="active">Active</label>
                    <select class="form-select" id="cActive">
                        <option value="true"  ${!c || c.is_active ? "selected" : ""} data-i18n="active">Active</option>
                        <option value="false" ${c && !c.is_active ? "selected" : ""} data-i18n="inactive">Inactive</option>
                    </select>
                </div>

                <div class="col-12"><hr style="border-top: 1px solid var(--border-color); margin: 15px 0;"></div>
                <div class="col-12 mt-1">
                    <h6 style="color: var(--accent-primary); font-weight: 700; margin-bottom: 0;" data-i18n="payroll_configuration">💰 Payroll Configuration</h6>
                </div>

                <div class="col-6">
                    <label data-i18n="current_salary">Current Monthly Salary</label>
                    <input type="number" step="0.01" class="form-control" id="cSalaryAmount" value="${c ? c.current_salary_amount || 0 : 0}">
                </div>
                <div class="col-6">
                    <label data-i18n="salary_currency">Salary Currency</label>
                    <select class="form-select" id="cSalaryCurrency">
                        <option value="">${selectCurText}</option>
                        ${currencyOpts}
                    </select>
                </div>

                <div class="col-6">
                    <label data-i18n="payment_day">Payment Day (1-31)</label>
                    <input type="number" min="1" max="31" class="form-control" id="cPaymentDay" value="${c ? c.payment_day || 25 : 25}">
                </div>
                <div class="col-6">
                    <label data-i18n="default_bank">Default Bank</label>
                    <select class="form-select" id="cDefaultBank">
                        <option value="">${noneText}</option>
                        ${bankOpts}
                    </select>
                </div>

                <div class="col-6">
                    <label data-i18n="perdiem_amount">Per Diem Amount</label>
                    <input type="number" step="0.01" class="form-control" id="cPerDiemAmount" value="${c ? c.per_diem_amount || 0 : 0}">
                </div>
                <div class="col-6">
                    <label data-i18n="perdiem_currency">Per Diem Currency</label>
                    <select class="form-select" id="cPerDiemCurrency">
                        <option value="">${selectCurText}</option>
                        ${currencyOpts2}
                    </select>
                </div>

                <div class="col-6">
                    <label data-i18n="bonus_amount">Bonus Amount</label>
                    <input type="number" step="0.01" class="form-control" id="cBonusAmount" value="${c ? c.bonus_amount || 0 : 0}">
                </div>
                <div class="col-6">
                </div>

                <div class="col-12">
                    <label data-i18n="payroll_notes">Payroll Notes</label>
                    <textarea class="form-control" id="cPayrollNotes" rows="2">${c ? c.payroll_notes || "" : ""}</textarea>
                </div>

                <div class="col-12 mt-3">
                    <div class="alert alert-info py-2 px-3 d-flex align-items-center" style="font-size: 13px; gap: 8px; border: 1px solid rgba(13, 110, 253, 0.25); background: rgba(13, 110, 253, 0.05); color: var(--text-primary);">
                        <i class="bi bi-info-circle-fill text-primary" style="font-size: 16px;"></i>
                        <span>
                            <strong>Important:</strong> Current Monthly Salary is used to generate salary entries for future months. Existing entries are not affected by changes. Payment Day applies when marking salary as paid.
                        </span>
                    </div>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveCompany(${companyId})" data-i18n="save_button">Save</button>
        </div>`);
  applyTranslations();
}

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
