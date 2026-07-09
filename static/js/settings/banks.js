"use strict";
// Bank configuration settings
// This file is part of the settings module. Do not edit directly.

async function renderBankSettings() {
    const res   = await fetch('/api/banks/');
    const data  = await res.json();
    window._banks = data.banks;

    const rows = data.banks.map(b => `
        <tr>
            <td>${b.name}</td>
            <td><code style="color:var(--text-muted);font-size:11px">${b.account_number || '—'}</code></td>
            <td><code style="color:var(--text-muted);font-size:11px">${b.swift_code    || '—'}</code></td>
            <td style="color:${b.is_active ? 'var(--accent-green)' : 'var(--accent-red)'}">
                ${b.is_active ? 'Active' : 'Inactive'}
            </td>
            <td>
                <button class="btn-icon" onclick="showBankModal(${b.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteBank(${b.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_banks"></div>
            <button class="btn-primary-custom" onclick="showBankModal(null)" data-i18n="btn_add">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="bank_name">Name</th>
                    <th data-i18n="account_number">Account</th>
                    <th data-i18n="swift_code">Swift</th>
                    <th data-i18n="status">Active</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
    applyTranslations();
}

async function showBankModal(bankId) {
    let b = null;
    if (bankId) {
        const res  = await fetch('/api/banks/');
        const data = await res.json();
        b = data.banks.find(x => x.id === bankId);
    }
    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${b ? 'edit_bank' : 'add_bank'}"></h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12">
                    <label data-i18n="bank_name">Bank Name</label>
                    <input class="form-control" id="bnName" value="${b?.name || ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="account_number">Account Number</label>
                    <input class="form-control" id="bnAcct" value="${b?.account_number || ''}">
                </div>
                <div class="col-6">
                    <label data-i18n="card_id">Card ID</label>
                    <input class="form-control" id="bnCard" value="${b?.card_id || ''}">
                </div>
                <div class="col-4">
                    <label data-i18n="swift_code">Swift Code</label>
                    <input class="form-control" id="bnSwift" value="${b?.swift_code || ''}">
                </div>
                <div class="col-4">
                    <label data-i18n="customer_id">Customer ID</label>
                    <input class="form-control" id="bnCustId" value="${b?.customer_id || ''}">
                </div>
                <div class="col-4">
                    <label data-i18n="customer_name">Customer Name</label>
                    <input class="form-control" id="bnCustName" value="${b?.customer_name || ''}">
                </div>
            </div>
            <div class="mt-3" id="bankDocumentManagerContainer"></div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveBank(${bankId})" data-i18n="save_button">Save</button>
        </div>`);
    applyTranslations();

    if (window.DocumentManager) {
        window.DocumentManager.init({
            containerId: 'bankDocumentManagerContainer',
            parentType: 'bank',
            parentId: bankId,
            disabledMessage: t('documents_save_first', 'Save this record first to manage documents.'),
        });
    }
}

async function saveBank(bankId) {
    const body = {
        name:          document.getElementById('bnName').value,
        account_number:document.getElementById('bnAcct').value,
        card_id:       document.getElementById('bnCard').value,
        swift_code:    document.getElementById('bnSwift').value,
        customer_id:   document.getElementById('bnCustId').value,
        customer_name: document.getElementById('bnCustName').value,
    };
    const res = await fetch(bankId ? `/api/banks/${bankId}/` : '/api/banks/', {
        method:  bankId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
    });
    if (res.ok) { closeModal(); showToast('Bank saved ✓'); renderBankSettings(); }
    else showToast('Error', 'error');
}

async function deleteBank(id) {
    if (!confirm('Delete this bank?')) return;
    await fetch(`/api/banks/${id}/`, { method: 'DELETE' });
    showToast('Deleted');
    renderBankSettings();
}

// ════════════════════════════════════════════════════════════════════════════
// USER MANAGEMENT TAB
// ════════════════════════════════════════════════════════════════════════════

