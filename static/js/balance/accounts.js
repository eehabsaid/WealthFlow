'use strict';

// balance/accounts.js — Accounts tab renderer
// Renders: Balance Entries Table with Edit / Delete
// Called by index.js with pre-fetched data. Zero API calls here.
// ════════════════════════════════════════════════════════════════════════════

function renderBalanceAccounts(data) {
    const pane = document.getElementById('bal-pane-accounts');
    if (!pane) return;

    const { entries } = data;

    const editText      = t('edit',            'Edit');
    const deleteText    = t('delete',          'Delete');
    const titleLabel    = t('balance_title',   'Title');
    const typeLabel     = t('balance_type',    'Balance Type');
    const bankLabel     = t('balance_bank',    'Bank');
    const currencyLabel = t('balance_currency','Currency');
    const amountLabel   = t('balance_amount',  'Amount');
    const actionsLabel  = t('actions',         'Actions');
    const purityLabel   = t('purity',          'Purity');

    const rows = entries.map((e) => `
        <tr>
            <td data-i18n-key="${e.title || ''}">${_t && _t[e.title] ? _t[e.title] : (e.title || '')}</td>
            <td data-i18n-prefix="type_" data-i18n-value="${e.balance_type || ''}">${_t && _t['type_' + e.balance_type] ? _t['type_' + e.balance_type] : (e.balance_type || '')}</td>
            <td data-i18n-prefix="bank_" data-i18n-value="${e.bank_name || ''}">${e.bank_name || '_'}</td>
            <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${e.currency_flag} ${e.currency_code}</span></td>
            <td>${e.balance_type === 'gold' ? (e.purity || '-') : '-'}</td>
            <td class="text-end amt-positive num-fmt" data-value="${e.amount}">${fmt(e.amount)}</td>
            <td>
                <button class="btn-icon" onclick="showBalanceModal(${e.id})" title="${editText}"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deleteBalanceEntry(${e.id})" title="${deleteText}"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');

    pane.innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="balance_title">${titleLabel}</th>
                            <th data-i18n="balance_type">${typeLabel}</th>
                            <th data-i18n="balance_bank">${bankLabel}</th>
                            <th data-i18n="balance_currency">${currencyLabel}</th>
                            <th data-i18n="purity">${purityLabel}</th>
                            <th class="text-end" data-i18n="balance_amount">${amountLabel}</th>
                            <th data-i18n="actions">${actionsLabel}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>
    `;
}
