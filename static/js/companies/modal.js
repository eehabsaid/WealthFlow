// companies.js — All Companies management page (modal)

"use strict";

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
  const company = compRes ? await compRes.json() : null;

  const titleText = company ? t("btn_edit", "Edit") : t("btn_add", "Add");
  const activeLabel = t("is_active", "Active");
  const noneText = t("none_option", "— None —");
  const selectCurText = t("select_currency_option", "— Select currency —");

  const bankOpts = banks
    .map(
      (b) =>
        `<option value="${b.id}" ${company && company.default_bank_id === b.id ? "selected" : ""}>${b.name}</option>`
    )
    .join("");
  const currencyOpts = currencies
    .map(
      (c) =>
        `<option value="${c.id}" ${company && company.current_salary_currency_id === c.id ? "selected" : ""}>${c.flag} ${c.code}</option>`
    )
    .join("");
  const currencyOpts2 = currencies
    .map(
      (c) =>
        `<option value="${c.id}" ${company && company.per_diem_currency_id === c.id ? "selected" : ""}>${c.flag} ${c.code}</option>`
    )
    .join("");

  const html = `
        <div class="modal-header">
            <h5 class="modal-title">${titleText} ${t("company", "Company")}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="company_name">${t("company_name", "Name")}</label>
                    <input type="text" class="form-control" id="cName" value="${company ? company.name : ""}">
                </div>
                <div class="col-6">
                    <label data-i18n="company_display_name">${t("company_display_name", "Display Name")}</label>
                    <input type="text" class="form-control" id="cDisplayName" value="${company ? company.display_name : ""}">
                </div>
                <div class="col-6">
                    <label data-i18n="group">${t("group", "Group")}</label>
                    <input type="text" class="form-control" id="cGroupName" placeholder="${t("optional", "Optional")}" value="${company ? company.group_name : ""}">
                </div>
                <div class="col-6">
                    <label data-i18n="color">${t("color", "Color")}</label>
                    <input type="color" class="form-control form-control-color" id="cColor" value="${company ? company.color_hex : "#0d6efd"}" style="height:38px">
                </div>
                <div class="col-6">
                    <label data-i18n="order">${t("order", "Order")}</label>
                    <input type="number" class="form-control" id="cOrder" value="${company ? company.order : "0"}">
                </div>
                <div class="col-6">
                    <label>&nbsp;</label>
                    <div style="padding-top:8px">
                        <input type="checkbox" id="cActive" ${company && !company.is_active ? "" : "checked"}>
                        <label for="cActive" style="margin-left:6px;margin-bottom:0" data-i18n="is_active">${activeLabel}</label>
                    </div>
                </div>

                <div class="col-12"><hr style="border-top: 1px solid var(--border-color); margin: 15px 0;"></div>
                <div class="col-12 mt-1">
                    <h6 style="color: var(--accent-primary); font-weight: 700; margin-bottom: 0;" data-i18n="payroll_configuration">💰 Payroll Configuration</h6>
                </div>

                <div class="col-6">
                    <label data-i18n="current_salary">Current Monthly Salary</label>
                    <input type="number" step="0.01" class="form-control" id="cSalaryAmount" value="${company ? company.current_salary_amount || 0 : 0}">
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
                    <input type="number" min="1" max="31" class="form-control" id="cPaymentDay" value="${company ? company.payment_day || 25 : 25}">
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
                    <input type="number" step="0.01" class="form-control" id="cPerDiemAmount" value="${company ? company.per_diem_amount || 0 : 0}">
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
                    <input type="number" step="0.01" class="form-control" id="cBonusAmount" value="${company ? company.bonus_amount || 0 : 0}">
                </div>
                <div class="col-6">
                </div>

                <div class="col-12">
                    <label data-i18n="payroll_notes">Payroll Notes</label>
                    <textarea class="form-control" id="cPayrollNotes" rows="2">${company ? company.payroll_notes || "" : ""}</textarea>
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
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t("btn_cancel", "Cancel")}</button>
            <button class="btn-primary-custom" onclick="saveCompany(${companyId || "null"})" data-i18n="btn_save">${t("btn_save", "Save")}</button>
        </div>`;

  showModal(html);
  applyTranslations();
}

