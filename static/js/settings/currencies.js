"use strict";
// Currency configuration settings
// This file is part of the settings module. Do not edit directly.

async function renderCurrencySettings() {
    const res        = await fetch('/api/currencies/');
    const { currencies = [] } = await res.json();

    const rows = currencies.map(c => `
        <tr>
            <td style="font-size:20px">${c.flag}</td>
            <td><code style="color:var(--accent-primary);font-weight:700">${c.code}</code></td>
            <td>${c.symbol || '—'}</td>
            <td>${c.name}</td>
            <td>
                <button class="btn-icon" onclick="showCurrencyModal(${c.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteCurrency(${c.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="settings_currency"></div>
            <button class="btn-primary-custom" onclick="showCurrencyModal(null)" data-i18n="add_currency">
                <i class="bi bi-plus-lg"></i>
            </button>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="currency_flag">Flag</th>
                    <th data-i18n="currency_code">Code</th>
                    <th data-i18n="currency_symbol">Symbol</th>
                    <th data-i18n="currency_name">Name</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>
        <div style="margin-top:14px;font-size:13px;color:var(--text-secondary)"
            data-i18n="currency_settings_desc"></div>`;
    applyTranslations();
}

async function showCurrencyModal(currencyId) {
    let c = null;
    if (currencyId) {
        const res = await fetch(`/api/currencies/${currencyId}/`);
        c = await res.json();
    }
    const titleText = c ? (typeof t === 'function' ? t('edit_currency', 'Edit Currency') : 'Edit Currency') : (typeof t === 'function' ? t('add_currency', 'Add Currency') : 'Add Currency');
    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${c ? 'edit_currency' : 'add_currency'}">${titleText}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">

            <div class="row g-3">
                <div class="col-4">
                    <label data-i18n="currency_code">Code</label>
                    <input class="form-control" id="curCode" value="${c?.code || ''}" placeholder="USD">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_symbol">Symbol</label>
                    <input class="form-control" id="curSymbol" value="${c?.symbol || ''}" placeholder="$">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_flag">Flag</label>
                    <input class="form-control" id="curFlag" value="${c?.flag || '💱'}" placeholder="🇺🇸" maxlength="5">
                </div>
                <div class="col-12">
                    <label data-i18n="currency_name">Name</label>
                    <input class="form-control" id="curName" value="${c?.name || ''}" placeholder="US Dollar">
                </div>
                <div class="col-4">
                    <label data-i18n="currency_order">Order</label>
                    <input type="number" class="form-control" id="curOrder" value="${c?.order ?? 0}">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="cancel_button">Cancel</button>
            <button class="btn-primary-custom" onclick="saveCurrency(${currencyId})" data-i18n="save_button">Save</button>
        </div>`);
    applyTranslations();
}

async function saveCurrency(currencyId) {
    const body = {
        code:   document.getElementById('curCode').value.toUpperCase(),
        symbol: document.getElementById('curSymbol').value,
        flag:   document.getElementById('curFlag').value,
        name:   document.getElementById('curName').value,
        order:  parseInt(document.getElementById('curOrder').value) || 0,
    };
    if (!body.code || !body.name) { showToast('Code and Name are required', 'error'); return; }
    const res = await fetch(currencyId ? `/api/currencies/${currencyId}/` : '/api/currencies/', {
        method:  currencyId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
    });
    if (res.ok) { closeModal(); showToast('Currency saved ✓'); renderCurrencySettings(); }
    else showToast('Error', 'error');
}

async function deleteCurrency(currencyId) {
    if (!confirm('Delete this currency?')) return;
    const res = await fetch(`/api/currencies/${currencyId}/`, { method: 'DELETE' });
    if (res.ok) { showToast('Deleted'); renderCurrencySettings(); }
    else showToast('Error deleting currency', 'error');
}

// ════════════════════════════════════════════════════════════════════════════
// COMPANY SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

