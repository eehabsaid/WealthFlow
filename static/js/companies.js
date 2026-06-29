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
    let company = null;
    if (companyId) {
        const res = await fetch(`/api/companies/${companyId}/`);
        company = await res.json();
    }

    const titleText = company ? t('btn_edit', 'Edit') : t('btn_add', 'Add');
    const activeLabel = t('is_active', 'Active');

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
