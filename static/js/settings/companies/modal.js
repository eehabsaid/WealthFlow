"use strict";
// Company configuration settings — modal
// This file is part of the settings module. Do not edit directly.

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

