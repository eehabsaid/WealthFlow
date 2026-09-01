'use strict';

// balance/card_renewal_fee/render.js — Card Renewal Fee tab renderer
// ════════════════════════════════════════════════════════════════════════════

let _cardRenewalFeeData = [];

function renderBalanceCardRenewalFee(data) {
    const pane = document.getElementById('bal-pane-card_renewal_fee');
    if (!pane) return;

    _cardRenewalFeeData = data.card_renewal_fees || [];

    const dateText     = t('crf_date',              'Date');
    const bankText      = t('crf_bank',               'Bank');
    const cardText       = t('crf_card_label',        'Card');
    const amountText    = t('amount',               'Amount');
    const notesText     = t('notes',                'Notes');
    const actionsText   = t('actions',               'Actions');
    const newText       = t('new_card_renewal_fee', 'New Card Renewal Fee');
    const noneText      = t('no_card_renewal_fees_found', 'No card renewal fees found.');
    const editText      = t('edit',                 'Edit');
    const deleteText    = t('delete',                'Delete');

    let rowsHtml = '';

    if (_cardRenewalFeeData.length === 0) {
        rowsHtml = `<tr><td colspan="6" class="text-center py-4" style="opacity:0.8; font-weight:500;" data-i18n="no_card_renewal_fees_found">${noneText}</td></tr>`;
    } else {
        rowsHtml = _cardRenewalFeeData.map(crf => `
            <tr>
                <td>${formatDate(crf.fee_date)}</td>
                <td>${crf.bank_name || '-'}</td>
                <td>${crf.card_label || '-'}</td>
                <td class="text-end amt-negative num-fmt" data-value="${crf.amount_egp}">${fmt(crf.amount_egp)}</td>
                <td class="text-truncate" style="max-width: 150px;" title="${crf.notes}">${crf.notes || '-'}</td>
                <td>
                    <button class="btn-icon" onclick="showCardRenewalFeeModal(${crf.id})" title="${editText}"><i class="bi bi-pencil"></i></button>
                    <button class="btn-icon del" onclick="deleteCardRenewalFee(${crf.id})" title="${deleteText}"><i class="bi bi-trash"></i></button>
                </td>
            </tr>
        `).join('');
    }

    pane.innerHTML = `
        <div class="d-flex justify-content-end align-items-center mb-3">
            <button class="btn-primary-custom" onclick="showCardRenewalFeeModal()">
                <i class="bi bi-plus-lg me-1"></i>
                <span data-i18n="new_card_renewal_fee">${newText}</span>
            </button>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="crf_date">${dateText}</th>
                            <th data-i18n="crf_bank">${bankText}</th>
                            <th data-i18n="crf_card_label">${cardText}</th>
                            <th class="text-end" data-i18n="amount">${amountText}</th>
                            <th data-i18n="notes">${notesText}</th>
                            <th data-i18n="actions">${actionsText}</th>
                        </tr>
                    </thead>
                    <tbody id="cardRenewalFeeTableBody">
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}
