'use strict';

// balance/transfers.js — Transfers tab renderer
// ════════════════════════════════════════════════════════════════════════════

let _balanceTransfersData = [];
let _editingTransferId = null;

function renderBalanceTransfers(data) {
    const pane = document.getElementById('bal-pane-transfers');
    if (!pane) return;

    _balanceTransfersData = data.transfers || [];

    const dateText     = t('transfer_date', 'Date');
    const typeText     = t('transfer_type', 'Type');
    const fromText     = t('transfer_from', 'From');
    const toText       = t('transfer_to',   'To');
    const currencyText = t('currency',      'Currency');
    const amountText   = t('amount',        'Amount');
    const feeText      = t('transfer_fee',  'Fee');
    const notesText    = t('notes',         'Notes');
    const actionsText  = t('actions',       'Actions');
    const newTransText = t('new_transfer',  'New Transfer');
    const noTransText  = t('no_transfers_found', 'No transfers found.');
    const editText     = t('edit',          'Edit');
    const deleteText   = t('delete',        'Delete');

    let rowsHtml = '';

    if (_balanceTransfersData.length === 0) {
        rowsHtml = `<tr><td colspan="9" class="text-center py-4" style="opacity:0.8; font-weight:500;" data-i18n="no_transfers_found">${noTransText}</td></tr>`;
    } else {
        rowsHtml = _balanceTransfersData.map(tr => {
            const typeLabels = {
                'bank_to_bank': t('type_bank_to_bank', 'Bank → Bank'),
                'bank_to_cash': t('type_bank_to_cash', 'Bank → Cash'),
                'cash_to_bank': t('type_cash_to_bank', 'Cash → Bank'),
            };
            const typeLabel = typeLabels[tr.transfer_type] || tr.transfer_type;
            const fromLabel = tr.from_bank_name || (tr.transfer_type === 'cash_to_bank' ? t('label_cash', 'Cash') : '-');
            const toLabel = tr.to_bank_name || (tr.transfer_type === 'bank_to_cash' ? t('label_cash', 'Cash') : '-');

            return `
                <tr>
                    <td>${tr.transfer_date}</td>
                    <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${typeLabel}</span></td>
                    <td>${fromLabel}</td>
                    <td>${toLabel}</td>
                    <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${tr.currency_flag || '💱'} ${tr.currency_code}</span></td>
                    <td class="text-end amt-positive num-fmt" data-value="${tr.amount}">${fmt(tr.amount)}</td>
                    <td class="text-end amt-negative num-fmt" data-value="${tr.fee}">${fmt(tr.fee)}</td>
                    <td class="text-truncate" style="max-width: 150px;" title="${tr.notes}">${tr.notes || '-'}</td>
                    <td>
                        <button class="btn-icon" onclick="showTransferModal(${tr.id})" title="${editText}"><i class="bi bi-pencil"></i></button>
                        <button class="btn-icon del" onclick="deleteTransfer(${tr.id})" title="${deleteText}"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    pane.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h5 style="color:var(--accent-primary);font-size:1.2rem;font-weight:700;margin:0" data-i18n="balance_tab_transfers">${t('balance_tab_transfers', 'Transfers')}</h5>
            <button class="btn-primary-custom" onclick="showTransferModal()">
                <i class="bi bi-plus-lg me-1"></i>
                <span data-i18n="new_transfer">${newTransText}</span>
            </button>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="transfer_date">${dateText}</th>
                            <th data-i18n="transfer_type">${typeText}</th>
                            <th data-i18n="transfer_from">${fromText}</th>
                            <th data-i18n="transfer_to">${toText}</th>
                            <th data-i18n="currency">${currencyText}</th>
                            <th class="text-end" data-i18n="amount">${amountText}</th>
                            <th class="text-end" data-i18n="transfer_fee">${feeText}</th>
                            <th data-i18n="notes">${notesText}</th>
                            <th data-i18n="actions">${actionsText}</th>
                        </tr>
                    </thead>
                    <tbody id="transfersTableBody">
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function showTransferModal(id = null) {
    _editingTransferId = id;
    const isEdit = id !== null;
    let tr = { transfer_type: 'bank_to_bank', transfer_date: new Date().toISOString().split('T')[0], amount: '', fee: 0, notes: '', currency_id: 1 };

    if (isEdit) {
        tr = _balanceTransfersData.find(x => x.id === id) || tr;
    }

    const titleText = isEdit ? t('edit_transfer', 'Edit Transfer') : t('new_transfer', 'New Transfer');
    const cancelText = t('btn_cancel', 'Cancel');
    const saveText = t('btn_save', 'Save');
    
    const bankOptions = _banks.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    
    // Format currency options like modal.js
    const curOptions = (_currencies || []).map(c => {
        const key = c.code === 'Gold' ? 'type_gold' : c.code;
        let translatedName = _t && _t[key] ? _t[key] : `${c.code} - ${c.name}`;
        if (c.code === 'Gold' && _t && _t['type_gold']) {
            translatedName = _t['type_gold'].replace(/[\u{1F300}-\u{1F9FF}]/gu, '').trim();
        }
        const displayName = `${c.flag || '💵'} ${translatedName}`;
        return `<option value="${c.id}" data-i18n="${key}" ${tr.currency_id === c.id ? 'selected' : ''}>${displayName}</option>`;
    }).join('');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${isEdit ? 'edit_transfer' : 'new_transfer'}">
                ${titleText}
            </h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="transferForm" onsubmit="event.preventDefault(); saveTransfer();">
                <div class="row g-3">
                    <div class="col-12">
                        <label data-i18n="transfer_type">${t('transfer_type', 'Transfer Type')}</label>
                        <select class="form-select" id="tr_type" required onchange="onTransferTypeChange()">
                            <option value="bank_to_bank" data-i18n="type_bank_to_bank">${t('type_bank_to_bank', 'Bank → Bank')}</option>
                            <option value="bank_to_cash" data-i18n="type_bank_to_cash">${t('type_bank_to_cash', 'Bank → Cash')}</option>
                            <option value="cash_to_bank" data-i18n="type_cash_to_bank">${t('type_cash_to_bank', 'Cash → Bank')}</option>
                        </select>
                    </div>
                    
                    <div class="col-6" id="from_bank_container">
                        <label data-i18n="transfer_from">${t('transfer_from', 'From Bank')}</label>
                        <select class="form-select" id="tr_from_bank">
                            <option value="" disabled selected data-i18n="select_bank">${t('select_bank', 'Select Bank...')}</option>
                            ${bankOptions}
                        </select>
                    </div>
                    
                    <div class="col-6" id="to_bank_container">
                        <label data-i18n="transfer_to">${t('transfer_to', 'To Bank')}</label>
                        <select class="form-select" id="tr_to_bank">
                            <option value="" disabled selected data-i18n="select_bank">${t('select_bank', 'Select Bank...')}</option>
                            ${bankOptions}
                        </select>
                    </div>
                    
                    <div class="col-4">
                        <label data-i18n="currency">${t('currency', 'Currency')}</label>
                        <select class="form-select" id="tr_currency" required>
                            ${curOptions}
                        </select>
                    </div>
                    
                    <div class="col-4">
                        <label data-i18n="amount">${t('amount', 'Amount')}</label>
                        <input type="number" step="0.01" class="form-control" id="tr_amount" required min="0.01">
                    </div>
                    
                    <div class="col-4">
                        <label data-i18n="transfer_fee">${t('transfer_fee', 'Fee')}</label>
                        <input type="number" step="0.01" class="form-control" id="tr_fee" value="0" min="0">
                    </div>
                    
                    <div class="col-12">
                        <label data-i18n="transfer_date">${t('transfer_date', 'Date')}</label>
                        <input type="date" class="form-control" id="tr_date" required>
                    </div>
                    
                    <div class="col-12">
                        <label data-i18n="notes">${t('notes', 'Notes')}</label>
                        <input type="text" class="form-control" id="tr_notes">
                    </div>
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button type="submit" form="transferForm" class="btn-primary-custom" id="saveTransferBtn" data-i18n="btn_save">${saveText}</button>
        </div>
    `;

    // showModal is globally available from modals.js
    showModal(html);
    
    // Set values after render
    document.getElementById('tr_type').value = tr.transfer_type;
    document.getElementById('tr_date').value = tr.transfer_date;
    document.getElementById('tr_amount').value = tr.amount;
    document.getElementById('tr_fee').value = tr.fee;
    document.getElementById('tr_notes').value = tr.notes;
    
    if (tr.from_bank_id) document.getElementById('tr_from_bank').value = tr.from_bank_id;
    if (tr.to_bank_id) document.getElementById('tr_to_bank').value = tr.to_bank_id;

    onTransferTypeChange();
    applyTranslations();
}

function onTransferTypeChange() {
    const type = document.getElementById('tr_type').value;
    const fromContainer = document.getElementById('from_bank_container');
    const toContainer = document.getElementById('to_bank_container');
    const fromSelect = document.getElementById('tr_from_bank');
    const toSelect = document.getElementById('tr_to_bank');

    fromContainer.style.display = 'block';
    toContainer.style.display = 'block';
    fromSelect.required = true;
    toSelect.required = true;

    if (type === 'bank_to_cash') {
        toContainer.style.display = 'none';
        toSelect.required = false;
        toSelect.value = '';
    } else if (type === 'cash_to_bank') {
        fromContainer.style.display = 'none';
        fromSelect.required = false;
        fromSelect.value = '';
    }
}

async function saveTransfer() {
    const btn = document.getElementById('saveTransferBtn');
    if (btn) btn.disabled = true;

    const payload = {
        transfer_type: document.getElementById('tr_type').value,
        transfer_date: document.getElementById('tr_date').value,
        currency_id: document.getElementById('tr_currency').value,
        amount: document.getElementById('tr_amount').value,
        fee: document.getElementById('tr_fee').value || 0,
        notes: document.getElementById('tr_notes').value,
    };

    if (payload.transfer_type !== 'cash_to_bank') {
        payload.from_bank_id = document.getElementById('tr_from_bank').value;
    }
    if (payload.transfer_type !== 'bank_to_cash') {
        payload.to_bank_id = document.getElementById('tr_to_bank').value;
    }

    try {
        const url = _editingTransferId ? `/api/balance-transfers/${_editingTransferId}/` : '/api/balance-transfers/';
        const method = _editingTransferId ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            const errMsg = err.error ? t(err.error, err.error) : t('error_failed_to_save', 'Failed to save transfer');
            throw new Error(errMsg);
        }

        if (typeof closeModal === 'function') closeModal();
        showToast(t('success_saved', 'Saved successfully'), 'success');
        
        // Re-render whole balance to reflect balance entry changes globally
        if (typeof renderBalance === 'function') {
            await renderBalance();
        }
    } catch (e) {
        showToast(e.message, 'danger');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function deleteTransfer(id) {
    if (!confirm(t('confirm_delete', 'Are you sure you want to delete this?'))) return;
    try {
        const res = await fetch(`/api/balance-transfers/${id}/`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Delete failed');
        
        showToast(t('success_deleted', 'Deleted successfully'), 'success');
        
        // Re-render whole balance to reflect balance entry changes globally
        if (typeof renderBalance === 'function') {
            await renderBalance();
        }
    } catch (e) {
        showToast(e.message, 'danger');
    }
}
