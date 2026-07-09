'use strict';

async function showBankCertificateModal(certificateId) {
    let certificate = null;
    if (certificateId) {
        const res = await fetch(`/api/bank-certificates/${certificateId}/`);
        certificate = await res.json();
    }
    const bankOpts = _banks
        .map(
            (b) =>
                `<option value="${b.id}" ${certificate && certificate.bank_id === b.id ? 'selected' : ''}>${b.name}</option>`,
        )
        .join('');
    const curOpts = _currencies
        .map(
            (c) =>
                `<option value="${c.id}" ${certificate && certificate.currency_id === c.id ? 'selected' : ''}>${c.flag} ${c.code}</option>`,
        )
        .join('');

    // Fetch status options cleanly BEFORE generating the HTML template to eliminate race conditions
    const statusOpts = await _getCertStatusOptions(certificate ? certificate.status : null);

    const titleText = certificate ? t('edit_bank_certificate', 'Edit Bank Certificate') : t('add_bank_certificate', 'Add Bank Certificate');
    const statusLabel = t('status', 'Status');
    const bankLabel = t('bank', 'Bank');
    const currencyLabel = t('currency', 'Currency');
    const issueDateLabel = t('issue_date', 'Issue Date');
    const expiryDateLabel = t('expiry_date', 'Expiry Date');
    const amountLabel = t('balance_amount', 'Amount');
    const rateLabel = t('interest_rate', 'Interest Rate');
    const valueLabel = t('interest_value', 'Interest Value');
    const frequencyLabel = t('frequency', 'Frequency');
    const notesLabel = t('notes', 'Notes');
    const selectFreqText = t('select_frequency', '— Select Frequency —');
    const monthlyText = t('freq_monthly', 'Monthly');
    const quarterlyText = t('freq_quarterly', 'Quarterly');
    const semiAnnuallyText = t('freq_semi_annually', 'Semi-Annually');
    const annuallyText = t('freq_annually', 'Annually');
    const maturityText = t('freq_at_maturity', 'At Maturity');
    const cancelText = t('btn_cancel', 'Cancel');
    const saveText = t('btn_save', 'Save');
    const noneText = t('none_option', '— None —');
    const selectCurText = t('select_currency_option', '— Select currency —');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${certificate ? 'edit_bank_certificate' : 'add_bank_certificate'}">${titleText}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="status">${statusLabel}</label>
                    <select class="form-select" id="bcStatus">
                        ${statusOpts}
                    </select>
                </div>
                <div class="col-6"><label data-i18n="bank">${bankLabel}</label><select class="form-select" id="bcBank"><option value="">${noneText}</option>${bankOpts}</select></div>
                <div class="col-6"><label data-i18n="currency">${currencyLabel}</label>
                <select class="form-select" id="bcCurrency"><option value="">${selectCurText}</option>${curOpts}</select></div>
                <div class="col-6"><label data-i18n="issue_date">${issueDateLabel}</label>
                <input type="date" class="form-control" id="bcIssue" value="${certificate ? certificate.issue_date : ''}"></div>
                <div class="col-6"><label data-i18n="expiry_date">${expiryDateLabel}</label>
                <input type="date" class="form-control" id="bcExpiry" value="${certificate ? certificate.expiry_date : ''}"></div>
                <div class="col-4"><label data-i18n="balance_amount">${amountLabel}</label>
                <input type="number" step="0.01" class="form-control" id="bcAmount" value="${certificate ? certificate.amount : ''}"></div>
                <div class="col-4"><label data-i18n="interest_rate">${rateLabel}</label>
                <input type="number" step="0.0001" class="form-control" id="bcInterestRate" value="${certificate ? certificate.interest_rate : ''}"></div>
                <div class="col-4"><label data-i18n="interest_value">${valueLabel}</label>
                <input type="number" step="0.01" class="form-control" id="bcInterestValue" value="${certificate ? certificate.interest_value : ''}"></div>
                <div class="col-6">
                    <label data-i18n="frequency">${frequencyLabel}</label>
                    <select class="form-select" id="bcFrequency">
                        <option value="" data-i18n="select_frequency">${selectFreqText}</option>
                        <option value="monthly" data-i18n="freq_monthly" ${certificate && certificate.frequency === 'monthly' ? 'selected' : ''}>${monthlyText}</option>
                        <option value="quarterly" data-i18n="freq_quarterly" ${certificate && certificate.frequency === 'quarterly' ? 'selected' : ''}>${quarterlyText}</option>
                        <option value="semi_annually" data-i18n="freq_semi_annually" ${certificate && certificate.frequency === 'semi_annually' ? 'selected' : ''}>${semiAnnuallyText}</option>
                        <option value="annually" data-i18n="freq_annually" ${certificate && certificate.frequency === 'annually' ? 'selected' : ''}>${annuallyText}</option>
                        <option value="at_maturity" data-i18n="freq_at_maturity" ${certificate && certificate.frequency === 'at_maturity' ? 'selected' : ''}>${maturityText}</option>
                    </select>
                </div>
                <div class="col-6"><label data-i18n="notes">${notesLabel}</label>
                <textarea class="form-control" id="bcNotes" rows="2">${certificate ? certificate.notes : ''}</textarea></div>
            </div>
            <div class="mt-3" id="certificateDocumentManagerContainer"></div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button class="btn-primary-custom" onclick="saveBankCertificate(${certificateId})" data-i18n="btn_save">${saveText}</button>
        </div>`;
    showModal(html);
    applyTranslations();

    if (window.DocumentManager) {
        window.DocumentManager.init({
            containerId: 'certificateDocumentManagerContainer',
            parentType: 'bank_certificate',
            parentId: certificateId,
            disabledMessage: t('documents_save_first', 'Save this record first to manage documents.'),
        });
    }

    // --- ADD EVENT LISTENERS FOR LIVE CALCULATION ---
    const inputsToWatch = ['bcAmount', 'bcInterestRate', 'bcFrequency', 'bcIssue', 'bcExpiry'];
    inputsToWatch.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            // 'input' catches typing inside number boxes; 'change' handles dropdown modifications and datepickers
            el.addEventListener('input', calculateCertificateInterest);
            el.addEventListener('change', calculateCertificateInterest);
        }
    });

    // If editing an existing record, run it once to ensure correct validation display state
    if (certificateId) {
        calculateCertificateInterest();
    }
}

// ════════════════════════════════════════════════════════════════════════════
// STATUS OPTIONS & UTILITIES
// ════════════════════════════════════════════════════════════════════════════