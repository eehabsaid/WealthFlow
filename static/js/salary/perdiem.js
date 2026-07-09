'use strict';

async function showPerDiemListModal(companyId, year) {
    if (!year) {
        year = parseInt(document.querySelector('.year-pill.active')?.textContent) || new Date().getFullYear();
    }
    
    // Show spinner while loading
    showModal('<div class="modal-body text-center py-5"><div class="spinner-border text-primary"></div></div>');
    
    try {
        const [pdRes, bRes] = await Promise.all([
            fetch(`/api/per-diems/?company_id=${companyId}&year=${year}`),
            fetch('/api/banks/')
        ]);
        const pdData = await pdRes.json();
        const bData = await bRes.json();
        
        const perDiems = pdData.entries || [];
        const banks = bData.banks || [];
        
        const modalHtml = `
            <div class="modal-header">
                <h5 class="modal-title" data-i18n="per_diem_list">Per Diem List</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div style="display:flex; align-items:center; gap:8px">
                        <label data-i18n="currency_filter" style="margin-bottom:0">Currency Filter</label>
                        <select class="form-select form-select-sm" id="pdCurrencyFilter" style="width:120px" onchange="filterPerDiems()">
                            <option value="ALL" data-i18n="all_option">All</option>
                        </select>
                    </div>
                    <button class="btn btn-primary btn-sm btn-primary-custom" onclick="showPerDiemFormModal(null, ${companyId}, ${year})" data-i18n="add_per_diem">
                        <i class="bi bi-plus-lg"></i> Add Per Diem
                    </button>
                </div>
                
                <div class="table-container" style="max-height: 400px; overflow-y: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th data-i18n="date">Date</th>
                                <th data-i18n="currency">Currency</th>
                                <th class="text-end" data-i18n="amount_label">Amount</th>
                                <th class="text-end" data-i18n="amount_egp">Amount (EGP)</th>
                                <th data-i18n="received_in">Received In</th>
                                <th data-i18n="notes">Notes</th>
                                <th data-i18n="actions">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="perDiemTableBody">
                        </tbody>
                        <tfoot id="perDiemTableFoot">
                        </tfoot>
                    </table>
                </div>
            </div>
        `;
        
        showModal(modalHtml);
        
        // Populate Currency Filter
        const filterSelect = document.getElementById('pdCurrencyFilter');
        const uniqueCurrencies = [...new Set(perDiems.map(pd => pd.currency_code))];
        uniqueCurrencies.forEach(code => {
            const opt = document.createElement('option');
            opt.value = code;
            opt.textContent = code;
            filterSelect.appendChild(opt);
        });
        
        window._currentPerDiems = perDiems;
        window._currentBanks = banks;
        window._currentCompanyId = companyId;
        window._currentYear = year;
        
        filterPerDiems();
    } catch (e) {
        showToast('Failed to load Per Diem data', 'error');
    }
}

function filterPerDiems() {
    const filterVal = document.getElementById('pdCurrencyFilter').value;
    const pds = window._currentPerDiems || [];
    
    const filtered = filterVal === 'ALL' ? pds : pds.filter(pd => pd.currency_code === filterVal);
    
    const tbody = document.getElementById('perDiemTableBody');
    const tfoot = document.getElementById('perDiemTableFoot');
    if (!tbody) return;
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center" data-i18n="no_records">No records found</td></tr>`;
        tfoot.innerHTML = '';
        applyTranslations();
        return;
    }
    
    tbody.innerHTML = filtered.map(pd => `
        <tr>
            <td>${pd.date}</td>
            <td>${pd.currency_flag} ${pd.currency_code}</td>
            <td class="text-end">${fmt(pd.amount)}</td>
            <td class="text-end amt-positive">${fmt(pd.amount_egp)}</td>
            <td>${pd.bank_name ? pd.bank_name : `<span class="badge bg-secondary" style="font-weight: normal;" data-i18n="cash_option">${t('cash_option', 'Cash')}</span>`}</td>
            <td>${pd.notes || ''}</td>
            <td>
                <button class="btn-icon" onclick="showPerDiemFormModal(${pd.id}, ${window._currentCompanyId}, ${window._currentYear})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deletePerDiem(${pd.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
    
    let sumAmount = 0;
    let sumEgp = 0;
    filtered.forEach(pd => {
        sumAmount += pd.amount;
        sumEgp += pd.amount_egp;
    });
    
    const displayAmount = filterVal === 'ALL' ? '—' : fmt(sumAmount);
    
    tfoot.innerHTML = `
        <tr style="font-weight:bold; background: rgba(13, 110, 253, 0.05)">
            <td colspan="2" data-i18n="totals">Totals</td>
            <td class="text-end">${displayAmount}</td>
            <td class="text-end amt-positive">${fmt(sumEgp)}</td>
            <td colspan="3"></td>
        </tr>
    `;
    
    applyTranslations();
}

async function showPerDiemFormModal(perDiemId, companyId, year) {
    const modalContent = document.querySelector('#customModal .modal-content');
    if (modalContent) {
        modalContent.innerHTML = '<div class="modal-body text-center py-5"><div class="spinner-border text-primary"></div></div>';
    }
    
    try {
        const [cRes, rRes, pdRes] = await Promise.all([
            fetch('/api/per-diems/currencies/'),
            fetch('/api/rates/'),
            perDiemId ? fetch(`/api/per-diems/${perDiemId}/`) : Promise.resolve(null)
        ]);
        
        const cData = await cRes.json();
        const rData = await rRes.json();
        const pd = pdRes ? await pdRes.json() : null;
        
        const currencies = cData.currencies || [];
        const rates = rData.rates || [];
        const banks = window._currentBanks || [];
        
        const currencyOpts = currencies.map(c => `
            <option value="${c.id}" data-code="${c.code}" ${pd && pd.currency_id === c.id ? 'selected' : ''}>
                ${c.flag} ${c.code}
            </option>
        `).join('');
        
        const bankOpts = banks.map(b => `
            <option value="${b.id}" ${pd && pd.bank_id === b.id ? 'selected' : ''}>
                ${b.name}
            </option>
        `).join('');
        
        const selectCurText = t('select_currency_option', '— Select currency —');
        const cashText = t('cash_option', 'Cash');
        
        const formHtml = `
            <div class="modal-header">
                <h5 class="modal-title" data-i18n="${pd ? 'edit_per_diem' : 'add_per_diem'}">${pd ? 'Edit Per Diem' : 'Add Per Diem'}</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="perDiemForm" onsubmit="event.preventDefault();">
                    <div class="row g-3">
                        <div class="col-6">
                            <label class="form-label" data-i18n="date">Date</label>
                            <input type="date" class="form-control" id="pdDate" required value="${pd ? pd.date : new Date().toISOString().substring(0, 10)}">
                        </div>
                        <div class="col-6">
                            <label class="form-label" data-i18n="received_in">Received In</label>
                            <select class="form-select" id="pdBank">
                                <option value="">${cashText}</option>
                                ${bankOpts}
                            </select>
                        </div>
                        
                        <div class="col-6">
                            <label class="form-label" data-i18n="amount_label">Amount</label>
                            <input type="number" step="0.01" min="0" class="form-control" id="pdAmount" required value="${pd ? pd.amount : ''}" oninput="recalcPerDiemEgp()">
                        </div>
                        <div class="col-6">
                            <label class="form-label" data-i18n="currency">Currency</label>
                            <select class="form-select" id="pdCurrency" required onchange="recalcPerDiemEgp()">
                                <option value="">${selectCurText}</option>
                                ${currencyOpts}
                            </select>
                        </div>
                        
                        <div class="col-12">
                            <label class="form-label" data-i18n="amount_egp">Amount (EGP)</label>
                            <input type="text" class="form-control" id="pdAmountEgp" readonly value="${pd ? fmt(pd.amount_egp) : '0.00'}">
                        </div>
                        
                        <div class="col-12">
                            <label class="form-label" data-i18n="notes">Notes</label>
                            <textarea class="form-control" id="pdNotes" rows="2">${pd ? pd.notes : ''}</textarea>
                        </div>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary btn-secondary-custom" onclick="showPerDiemListModal(${companyId}, ${year})" data-i18n="cancel_button">Cancel</button>
                <button class="btn btn-primary btn-primary-custom" onclick="savePerDiem(${perDiemId}, ${companyId}, ${year})" data-i18n="save_button">Save</button>
            </div>
        `;
        
        showModal(formHtml);
        applyTranslations();
        
        window._currentRates = rates;
        if (pd) {
            recalcPerDiemEgp();
        }
    } catch (e) {
        showToast('Failed to initialize Per Diem form', 'error');
    }
}

function recalcPerDiemEgp() {
    const amountVal = parseFloat(document.getElementById('pdAmount').value) || 0;
    const currencySelect = document.getElementById('pdCurrency');
    const selectedOpt = currencySelect.options[currencySelect.selectedIndex];
    
    if (!selectedOpt || !selectedOpt.value) {
        document.getElementById('pdAmountEgp').value = '0.00';
        return;
    }
    
    const code = selectedOpt.getAttribute('data-code');
    let rate = 1.0;
    
    if (code !== 'EGP') {
        const rates = window._currentRates || [];
        const rateObj = rates.find(r => r.currency_code === code);
        rate = rateObj ? rateObj.buy_rate : 0;
    }
    
    const amountEgp = amountVal * rate;
    document.getElementById('pdAmountEgp').value = fmt(amountEgp);
}

async function savePerDiem(perDiemId, companyId, year) {
    const form = document.getElementById('perDiemForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const body = {
        company_id: companyId,
        year: year,
        date: document.getElementById('pdDate').value,
        currency_id: parseInt(document.getElementById('pdCurrency').value),
        amount: parseFloat(document.getElementById('pdAmount').value),
        bank_id: document.getElementById('pdBank').value ? parseInt(document.getElementById('pdBank').value) : null,
        notes: document.getElementById('pdNotes').value
    };
    
    const url = perDiemId ? `/api/per-diems/${perDiemId}/` : '/api/per-diems/';
    const method = perDiemId ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
        
        if (response.ok) {
            showToast(t('per_diem_saved', 'Per Diem saved successfully'), 'success');
            showPerDiemListModal(companyId, year);
        } else {
            const err = await response.json();
            showToast(err.error || 'Failed to save Per Diem', 'error');
        }
    } catch (error) {
        showToast('Failed to save Per Diem', 'error');
    }
}

async function deletePerDiem(perDiemId) {
    const msg = t('delete_confirm', 'Are you sure you want to delete this Per Diem record?');
    if (!confirm(msg)) return;
    
    try {
        const response = await fetch(`/api/per-diems/${perDiemId}/`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast(t('per_diem_deleted', 'Per Diem deleted successfully'), 'success');
            showPerDiemListModal(window._currentCompanyId, window._currentYear);
        } else {
            const err = await response.json();
            showToast(err.error || 'Failed to delete Per Diem', 'error');
        }
    } catch (error) {
        showToast('Failed to delete Per Diem', 'error');
    }
}

// Expose functions globally