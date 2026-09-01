'use strict';

// balance/credit_card_payment/modal.js — Credit Card Payment create/edit modal
// ════════════════════════════════════════════════════════════════════════════

let _editingCreditCardPaymentId = null;

function showCreditCardPaymentModal(id = null) {
    _editingCreditCardPaymentId = id;
    const isEdit = id !== null;
    let cp = {
        payment_date: new Date().toISOString().split('T')[0],
        bank_id: '',
        payment_method: 'Card',
        card_label: '',
        amount_egp: '',
        notes: '',
    };

    if (isEdit) {
        cp = _creditCardPaymentData.find(x => x.id === id) || cp;
    }

    const titleText  = isEdit ? t('edit_credit_card_payment', 'Edit Credit Card Payment') : t('new_credit_card_payment', 'New Credit Card Payment');
    const cancelText = t('btn_cancel', 'Cancel');
    const saveText   = t('btn_save', 'Save');

    // Bank dropdown is sourced dynamically from Settings > Bank list (_banks).
    const bankOptions = _banks.map(b => `<option value="${b.id}" ${cp.bank_id === b.id ? 'selected' : ''}>${b.name}</option>`).join('');

    const methodOptions = ['Card', 'Bank Transfer'].map(m =>
        `<option value="${m}" ${cp.payment_method === m ? 'selected' : ''}>${t('ccp_method_' + m.toLowerCase().replace(' ', '_'), m)}</option>`
    ).join('');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${isEdit ? 'edit_credit_card_payment' : 'new_credit_card_payment'}">
                ${titleText}
            </h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="creditCardPaymentForm" onsubmit="event.preventDefault(); saveCreditCardPayment();">
                <div class="row g-3">
                    <div class="col-12">
                        <label data-i18n="ccp_paid_from_bank">${t('ccp_paid_from_bank', 'Paid From')}</label>
                        <select class="form-select" id="ccp_bank" required>
                            <option value="" disabled ${cp.bank_id ? '' : 'selected'} data-i18n="select_bank">${t('select_bank', 'Select Bank...')}</option>
                            ${bankOptions}
                        </select>
                    </div>

                    <div class="col-6">
                        <label data-i18n="ccp_payment_method">${t('ccp_payment_method', 'Method')}</label>
                        <select class="form-select" id="ccp_method" required>
                            ${methodOptions}
                        </select>
                    </div>

                    <div class="col-6">
                        <label data-i18n="amount">${t('amount', 'Amount')}</label>
                        <input type="number" step="0.01" class="form-control" id="ccp_amount" required min="0.01">
                    </div>

                    <div class="col-12">
                        <label data-i18n="ccp_date">${t('ccp_date', 'Date')}</label>
                        <input type="date" class="form-control" id="ccp_date" required>
                    </div>

                    <div class="col-12">
                        <label data-i18n="ccp_card_label">${t('ccp_card_label', 'Card')}</label>
                        <input type="text" class="form-control" id="ccp_card_label" placeholder="Visa ****1234">
                    </div>

                    <div class="col-12">
                        <label data-i18n="notes">${t('notes', 'Notes')}</label>
                        <input type="text" class="form-control" id="ccp_notes">
                    </div>
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button type="submit" form="creditCardPaymentForm" class="btn-primary-custom" id="saveCreditCardPaymentBtn" data-i18n="btn_save">${saveText}</button>
        </div>
    `;

    showModal(html);

    document.getElementById('ccp_date').value = cp.payment_date;
    document.getElementById('ccp_amount').value = cp.amount_egp;
    document.getElementById('ccp_card_label').value = cp.card_label;
    document.getElementById('ccp_notes').value = cp.notes;
    if (cp.bank_id) document.getElementById('ccp_bank').value = cp.bank_id;

    applyTranslations();
}
