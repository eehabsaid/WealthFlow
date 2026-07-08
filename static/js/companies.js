// companies.js — All Companies management page

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// COMPANIES PAGE
// ════════════════════════════════════════════════════════════════════════════

async function renderAllCompanies() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const res = await fetch('/api/companies/');
    const data = await res.json();
    const companies = data.companies || [];

    const emptyMessage = `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-secondary)" data-i18n="no_data">No companies found</td></tr>`;

    const rows = companies
        .map(c => `
            <tr>
                <td>
                    <span class="nav-dot" style="background:${c.color_hex};display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px"></span>
                    <strong>${c.name}</strong>
                    ${c.display_name && c.display_name !== c.name ? `<br><small style="color:var(--text-secondary)">${c.display_name}</small>` : ''}
                </td>
                <td>${c.group_name || '-'}</td>
                <td><span class="badge" style="background:${c.color_hex}22;color:${c.color_hex};border:1px solid ${c.color_hex}">${c.color_hex}</span></td>
                <td>${c.is_active ? `<span class="badge bg-success" data-i18n="is_active">Active</span>` : `<span class="badge bg-secondary" data-i18n="inactive">Inactive</span>`}</td>
                <td style="text-align:center">
                    <button class="btn-icon" onclick="showCompanyModal(${c.id})" title="${t('btn_edit', 'Edit')}"><i class="bi bi-pencil"></i></button>
                    <button class="btn-icon" onclick="deleteCompany(${c.id})" title="${t('btn_delete', 'Delete')}"><i class="bi bi-trash"></i></button>
                </td>
            </tr>`)
        .join('');

    mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="nav_all_companies">All Companies</div></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="company">Company</th>
                            <th data-i18n="group">Group</th>
                            <th data-i18n="color">Color</th>
                            <th data-i18n="status">Status</th>
                            <th style="text-align:center;width:80px" data-i18n="actions">Actions</th>
                        </tr>
                    </thead>
                    <tbody>${rows || emptyMessage}</tbody>
                </table>
            </div>
        </div>`;
    applyTranslations();
}

async function showCompanyModal(companyId) {
    const [cRes, bRes, compRes] = await Promise.all([
        fetch('/api/currencies/'),
        fetch('/api/banks/'),
        companyId ? fetch(`/api/companies/${companyId}/`) : Promise.resolve(null)
    ]);
    const currData = await cRes.json();
    const bankData = await bRes.json();
    const currencies = currData.currencies || [];
    const banks = bankData.banks || [];
    const company = compRes ? await compRes.json() : null;

    const titleText = company ? t('btn_edit', 'Edit') : t('btn_add', 'Add');
    const activeLabel = t('is_active', 'Active');
    const noneText = t('none_option', '— None —');
    const selectCurText = t('select_currency_option', '— Select currency —');

    const bankOpts = banks
        .map(
            (b) =>
                `<option value="${b.id}" ${company && company.default_bank_id === b.id ? 'selected' : ''}>${b.name}</option>`,
        )
        .join('');
    const currencyOpts = currencies
        .map(
            (c) =>
                `<option value="${c.id}" ${company && company.current_salary_currency_id === c.id ? 'selected' : ''}>${c.flag} ${c.code}</option>`,
        )
        .join('');
    const currencyOpts2 = currencies
        .map(
            (c) =>
                `<option value="${c.id}" ${company && company.per_diem_currency_id === c.id ? 'selected' : ''}>${c.flag} ${c.code}</option>`,
        )
        .join('');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title">${titleText} ${t('company', 'Company')}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="company_name">${t('company_name', 'Name')}</label>
                    <input type="text" class="form-control" id="cName" value="${company ? company.name : ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="company_display_name">${t('company_display_name', 'Display Name')}</label>
                    <input type="text" class="form-control" id="cDisplayName" value="${company ? company.display_name : ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="group">${t('group', 'Group')}</label>
                    <input type="text" class="form-control" id="cGroupName" placeholder="${t('optional', 'Optional')}" value="${company ? company.group_name : ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="color">${t('color', 'Color')}</label>
                    <input type="color" class="form-control form-control-color" id="cColor" value="${company ? company.color_hex : '#0d6efd'}" style="height:38px">
                </div>
                <div class="col-6">
                    <label data-i18n="order">${t('order', 'Order')}</label>
                    <input type="number" class="form-control" id="cOrder" value="${company ? company.order : '0'}">
                </div>
                <div class="col-6">
                    <label>&nbsp;</label>
                    <div style="padding-top:8px">
                        <input type="checkbox" id="cActive" ${company && !company.is_active ? '' : 'checked'}>
                        <label for="cActive" style="margin-left:6px;margin-bottom:0" data-i18n="is_active">${activeLabel}</label>
                    </div>
                </div>

                <div class="col-12"><hr style="border-top: 1px solid var(--border-color); margin: 15px 0;"></div>
                <div class="col-12 mt-1">
                    <h6 style="color: var(--accent-primary); font-weight: 700; margin-bottom: 0;" data-i18n="payroll_configuration">💰 Payroll Configuration</h6>
                </div>

                <div class="col-6">
                    <label data-i18n="current_salary">Current Monthly Salary</label>
                    <input type="number" step="0.01" class="form-control" id="cSalaryAmount" value="${company ? (company.current_salary_amount || 0) : 0}">
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
                    <input type="number" min="1" max="31" class="form-control" id="cPaymentDay" value="${company ? (company.payment_day || 25) : 25}">
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
                    <input type="number" step="0.01" class="form-control" id="cPerDiemAmount" value="${company ? (company.per_diem_amount || 0) : 0}">
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
                    <input type="number" step="0.01" class="form-control" id="cBonusAmount" value="${company ? (company.bonus_amount || 0) : 0}">
                </div>
                <div class="col-6">
                </div>

                <div class="col-12">
                    <label data-i18n="payroll_notes">Payroll Notes</label>
                    <textarea class="form-control" id="cPayrollNotes" rows="2">${company ? (company.payroll_notes || '') : ''}</textarea>
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
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t('btn_cancel', 'Cancel')}</button>
            <button class="btn-primary-custom" onclick="saveCompany(${companyId || 'null'})" data-i18n="btn_save">${t('btn_save', 'Save')}</button>
        </div>`;

    showModal(html);
    applyTranslations();
}

async function saveCompany(companyId) {
    const body = {
        name: document.getElementById('cName').value,
        display_name: document.getElementById('cDisplayName').value,
        group_name: document.getElementById('cGroupName').value,
        color_hex: document.getElementById('cColor').value,
        order: parseInt(document.getElementById('cOrder').value) || 0,
        is_active: document.getElementById('cActive').checked,
        current_salary_amount: parseFloat(document.getElementById('cSalaryAmount').value) || 0,
        current_salary_currency_id: document.getElementById('cSalaryCurrency').value ? parseInt(document.getElementById('cSalaryCurrency').value) : null,
        payment_day: parseInt(document.getElementById('cPaymentDay').value) || 25,
        default_bank_id: document.getElementById('cDefaultBank').value ? parseInt(document.getElementById('cDefaultBank').value) : null,
        per_diem_amount: parseFloat(document.getElementById('cPerDiemAmount').value) || 0,
        per_diem_currency_id: document.getElementById('cPerDiemCurrency').value ? parseInt(document.getElementById('cPerDiemCurrency').value) : null,
        bonus_amount: parseFloat(document.getElementById('cBonusAmount').value) || 0,
        payroll_notes: document.getElementById('cPayrollNotes').value,
    };

    if (!body.name.trim()) {
        showToast(t('validation_company_name_required', 'Please enter a company name'), 'error');
        return;
    }

    const url = companyId ? `/api/companies/${companyId}/` : '/api/companies/';
    const method = companyId ? 'PUT' : 'POST';
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (res.ok) {
        closeModal();
        await refreshCompanies();
        renderAllCompanies();
        renderSidebar();
        const successMsg = companyId
            ? t('msg_updated', 'Updated successfully')
            : t('msg_created', 'Created successfully');
        showToast(successMsg, 'success');
    } else {
        showToast(t('error_saving_company', 'Error saving company'), 'error');
    }
}

async function deleteCompany(companyId) {
    const confirmMsg = t('confirm_delete_company', 'Are you sure you want to delete this company?');
    if (!confirm(confirmMsg)) return;

    const res = await fetch(`/api/companies/${companyId}/`, { method: 'DELETE' });
    if (res.ok) {
        await refreshCompanies();
        renderAllCompanies();
        renderSidebar();
        showToast(t('msg_deleted', 'Company deleted'), 'success');
    } else {
        showToast(t('error_deleting_company', 'Error deleting company'), 'error');
    }
}
