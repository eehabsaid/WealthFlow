// bank_certificates.js — Bank Certificates management page

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// MODULE STATE
// ════════════════════════════════════════════════════════════════════════════

let _currencies = [];

// ════════════════════════════════════════════════════════════════════════════
// BANK CERTIFICATES RENDERING
// ════════════════════════════════════════════════════════════════════════════

async function renderBankCertificates() {
    const mc = document.getElementById('main-content');
    mc.innerHTML =
        '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    await refreshBanks();
    const [cRes, certRes] = await Promise.all([
        fetch('/api/currencies/'),
        fetch('/api/bank-certificates/'),
    ]);

    const currData = await cRes.json();
    const certData = await certRes.json();
    const certificates = certData.certificates || [];
    _currencies = currData.currencies || [];

    const editTitle = t('edit', 'Edit');
    const deleteTitle = t('delete', 'Delete');
    const historyTitle = t('interest_history', 'Interest History');

    const rows = certificates
        .map(
            (c) => {
                const isClosed = String(c.status || '').trim().toLowerCase() === 'closed';
                
                // Apply the background tint, explicit red text color, and semi-bold font to every cell if closed
                const tdStyle = isClosed 
                    ? 'style="background-color: rgba(255, 77, 109, 0.05) !important; color: var(--accent-red) !important; font-weight: 700 !important;"' 
                    : '';

                return `
                <tr>
                    <td ${tdStyle}>${c.bank_name || '—'}</td>
                    <td ${tdStyle}><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${c.currency_flag} ${c.currency_code || '—'}</span></td>
                    <td ${tdStyle}>${c.issue_date || '—'}</td>
                    <td ${tdStyle}>${c.expiry_date || '—'}</td>
                    <td ${tdStyle} class="text-end">${fmt(c.amount)}</td>
                    <td ${tdStyle}>${c.interest_rate ? c.interest_rate : '—'}</td>
                    <td ${tdStyle}>${c.interest_value ? fmt(c.interest_value) : '—'}</td>
                    <td ${tdStyle} class="local-freq-field" data-freq="${c.frequency || ''}">
                    ${c.frequency ? c.frequency.replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase()) : '—'}
                    </td>
                    <td ${tdStyle}>
                        ${c.status || '—'}
                    </td>
                    <td ${tdStyle}>
                        <button class="btn-icon" onclick="showBankCertificateModal(${c.id})" title="${editTitle}"><i class="bi bi-pencil"></i></button>
                        <button class="btn-icon" onclick="showBankCertificateInterestHistory(${c.id})" title="${historyTitle}"><i class="bi bi-clock-history"></i></button>
                        <button class="btn-icon del" onclick="deleteBankCertificate(${c.id})" title="${deleteTitle}"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>`;
            }
        )
        .join('');

    const bankCertificatesTitle = t('bank_certificates', 'Bank Certificates');
    const bankHeader = t('bank', 'Bank');
    const currencyHeader = t('currency', 'Currency');
    const issueDateHeader = t('issue_date', 'Issue Date');
    const expiryDateHeader = t('expiry_date', 'Expiry Date');
    const amountHeader = t('balance_amount', 'Amount');
    const rateHeader = t('interest_rate', 'Interest Rate');
    const valueHeader = t('interest_value', 'Interest Value');
    const frequencyHeader = t('frequency', 'Frequency');
    const statusHeader = t('status', 'Status');
    const actionsHeader = t('actions', 'Actions');

    mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="bank_certificates">${bankCertificatesTitle}</div></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="bank">${bankHeader}</th>
                            <th data-i18n="currency">${currencyHeader}</th>
                            <th data-i18n="issue_date">${issueDateHeader}</th>
                            <th data-i18n="expiry_date">${expiryDateHeader}</th>
                            <th class="text-end" data-i18n="balance_amount">${amountHeader}</th>
                            <th data-i18n="interest_rate">${rateHeader}</th>
                            <th data-i18n="interest_value">${valueHeader}</th>
                            <th data-i18n="frequency">${frequencyHeader}</th>
                            <th data-i18n="status">${statusHeader}</th>
                            <th data-i18n="actions">${actionsHeader}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// MODAL MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════

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
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button class="btn-primary-custom" onclick="saveBankCertificate(${certificateId})" data-i18n="btn_save">${saveText}</button>
        </div>`;
    showModal(html);
    applyTranslations();

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

async function _getCertStatusOptions(currentStatus) {
    try {
        const res = await fetch('/api/cert-statuses/');
        const data = await res.json();
        const statuses = data.statuses || [];
        
        if (statuses.length === 0) {
            const defaultStatuses = ['Active', 'Maturing', 'Renewed', 'Closed'];
            return defaultStatuses
                .map((s) => `<option value="${s}" ${s === (currentStatus || 'Active') ? 'selected' : ''}>${s}</option>`)
                .join('');
        } else {
            return statuses
                .map(
                    (s) => `<option value="${s.name}" ${s.name === (currentStatus || '') || (!currentStatus && s.is_default) ? 'selected' : ''}>${s.name}</option>`
                )
                .join('');
        }
    } catch (e) {
        // Fallback if API fails
        const defaultStatuses = ['Active', 'Maturing', 'Renewed', 'Closed'];
        return defaultStatuses
            .map((s) => `<option value="${s}" ${s === (currentStatus || 'Active') ? 'selected' : ''}>${s}</option>`)
            .join('');
    }
}

function parseNumberInput(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    const raw = el.value || '';
    const normalized = String(raw).replace(/,/g, '').trim();
    if (normalized === '') return null;
    const num = Number(normalized);
    return Number.isFinite(num) ? num : null;
}

// ════════════════════════════════════════════════════════════════════════════
// SAVE & DELETE
// ════════════════════════════════════════════════════════════════════════════

async function saveBankCertificate(certificateId) {
    // Normalize certificateId to ensure "undefined" or "null" strings are treated as clean null
    let cleanId = certificateId;
    if (cleanId === 'undefined' || cleanId === 'null' || !cleanId) {
        cleanId = null;
    }

    const amount = parseNumberInput('bcAmount');
    const interestRate = parseNumberInput('bcInterestRate');
    const interestValue = parseNumberInput('bcInterestValue');
    
    const body = {
        status: document.getElementById('bcStatus').value.trim(),
        bank_id: parseInt(document.getElementById('bcBank').value, 10) || null,
        currency_id: parseInt(document.getElementById('bcCurrency').value, 10) || null,
        issue_date: document.getElementById('bcIssue').value || null,
        expiry_date: document.getElementById('bcExpiry').value || null,
        amount: amount === null ? 0 : amount,
        interest_rate: interestRate === null ? 0 : interestRate,
        interest_value: interestValue === null ? 0 : interestValue,
        frequency: document.getElementById('bcFrequency').value.trim(),
        notes: document.getElementById('bcNotes').value.trim(),
    };

    // Use the normalized cleanId variable here
    const url = cleanId
        ? `/api/bank-certificates/${cleanId}/`
        : '/api/bank-certificates/';
    const method = cleanId ? 'PUT' : 'POST';

    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    
    if (res.ok) {
        closeModal();
        showToast(t('bank_certificate_saved', 'Bank Certificate saved ✓'), 'success');
        renderBankCertificates();
        if (typeof renderBalanceEntries === 'function') {
            renderBalanceEntries(); 
        }
    } else {
        const text = await res.text();
        console.error('Bank certificate save failed', res.status, text);
        const errorMsg = t('error_saving_certificate', 'Error saving certificate: ') + (text || res.status);
        showToast(errorMsg, 'error');
    }
}

async function deleteBankCertificate(certificateId) {
    const confirmMsg = t('confirm_delete_certificate', 'Delete this certificate?');
    if (!confirm(confirmMsg)) return;
    const res = await fetch(`/api/bank-certificates/${certificateId}/`, {
        method: 'DELETE',
    });
    if (res.ok) {
        showToast(t('certificate_deleted', 'Certificate deleted'), 'success');
        renderBankCertificates();
    } else {
        showToast(t('error_deleting_certificate', 'Error deleting certificate'), 'error');
    }
}

// ════════════════════════════════════════════════════════════════════════════
// INTEREST CALCULATION
// ════════════════════════════════════════════════════════════════════════════

function calculateCertificateInterest() {
    const amount = parseNumberInput('bcAmount') || 0;
    const rate = parseNumberInput('bcInterestRate') || 0; // e.g., 0.10 for 10%
    const frequency = document.getElementById('bcFrequency').value;
    
    // Calculate base yearly interest
    const yearlyInterest = amount * (rate / 100);
    let computedValue = 0;

    if (yearlyInterest <= 0) {
        document.getElementById('bcInterestValue').value = '0.00';
        return;
    }

    switch (frequency) {
        case 'monthly':
            computedValue = yearlyInterest / 12;
            break;
        case 'quarterly':
            computedValue = yearlyInterest / 4;
            break;
        case 'semi_annually':
            computedValue = yearlyInterest / 2;
            break;
        case 'annually':
            computedValue = yearlyInterest;
            break;
        case 'at_maturity':
            const issueDateVal = document.getElementById('bcIssue').value;
            const expiryDateVal = document.getElementById('bcExpiry').value;
            
            if (issueDateVal && expiryDateVal) {
                const issue = new Date(issueDateVal);
                const expiry = new Date(expiryDateVal);
                
                // Calculate total days between dates, converted to fractional years
                const diffTime = Math.max(0, expiry - issue);
                const diffDays = diffTime / (1000 * 60 * 60 * 24);
                const totalYears = diffDays / 365.25; // Accounting for leap years safely
                
                computedValue = yearlyInterest * totalYears;
            } else {
                computedValue = 0; // Can't calculate maturity return without clear dates
            }
            break;
        default:
            computedValue = 0;
    }

    // Populate field locked to standard financial decimal precision
    document.getElementById('bcInterestValue').value = computedValue.toFixed(2);
}

async function showBankCertificateInterestHistory(certificateId) {
    const res = await fetch(`/api/bank-certificates/${certificateId}/interest-history/`);
    if (!res.ok) {
        showToast(t('error_loading_interest_history', 'Error loading interest history'), 'error');
        return;
    }

    const data = await res.json();
    const certificate = data.certificate || {};
    const items = data.items || [];
    const totalRecords = items.length;
    const totalInterestPaid = items.reduce((sum, item) => sum + (parseFloat(item.interest_amount) || 0), 0);

    const prettyIssueDate = formatCertificateHistoryDate(certificate.issue_date);
    const prettyNextPosting = getCertificateNextPostingDate(certificate, items);
    const prettyFrequency = formatCertificateFrequencyLabel(certificate.frequency || '');

    const rows = items.length
        ? items.map((item) => `
            <tr data-posting-date="${item.posting_date || ''}">
                <td>${item.posting_date || '—'}</td>
                <td>${item.posting_period || '—'}</td>
                <td class="text-end">${fmt(item.interest_amount || 0)}</td>
                <td>${item.bank_name || '—'}</td>
                <td>${item.currency_code || '—'}</td>
                <td>${item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</td>
            </tr>
        `).join('')
        : `<tr><td colspan="6" style="text-align:center;padding:22px;color:var(--text-muted)" data-i18n="no_interest_history">No interest history yet.</td></tr>`;

    const certTitle = certificate.bank_name
        ? `${certificate.bank_name} - ${certificate.currency_code || ''}`
        : (certificate.id ? `#${certificate.id}` : '');

    const summaryRows = `
        <div class="row g-2" style="margin-bottom:12px;">
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="certificate">Certificate</div>
                    <div style="font-weight:700;color:var(--text-primary);">${certificate.bank_name || certTitle || '—'}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="issue_date">Issue Date</div>
                    <div style="font-weight:700;color:var(--text-primary);">${prettyIssueDate}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="frequency">Frequency</div>
                    <div style="font-weight:700;color:var(--text-primary);">${prettyFrequency}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="monthly_interest">Monthly Interest</div>
                    <div style="font-weight:700;color:var(--text-primary);">${fmt(parseFloat(certificate.interest_value) || 0)}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="total_posted">Total Posted</div>
                    <div style="font-weight:700;color:var(--text-primary);">${fmt(totalInterestPaid)}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div style="padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                    <div style="font-size:11px;color:var(--text-secondary);" data-i18n="next_posting">Next Posting</div>
                    <div style="font-weight:700;color:var(--text-primary);">${prettyNextPosting}</div>
                </div>
            </div>
        </div>
    `;

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="interest_history">Interest History</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="closeModal()"></button>
        </div>
        <div class="modal-body">
            <div style="margin-bottom:10px;color:var(--text-secondary);font-size:13px;">
                <span data-i18n="certificate">Certificate</span>: ${certTitle || '—'}
            </div>
            ${summaryRows}
            <div class="row g-2" style="margin-bottom:10px;">
                <div class="col-sm-6">
                    <label class="form-label" data-i18n="start_date">Start Date</label>
                    <input type="date" class="form-control" id="interestHistoryStart" oninput="filterBankCertificateInterestHistoryRows()">
                </div>
                <div class="col-sm-6">
                    <label class="form-label" data-i18n="end_date">End Date</label>
                    <input type="date" class="form-control" id="interestHistoryEnd" oninput="filterBankCertificateInterestHistoryRows()">
                </div>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="posting_date">Posting Date</th>
                            <th data-i18n="posting_period">Posting Period</th>
                            <th class="text-end" data-i18n="interest_amount">Interest Amount</th>
                            <th data-i18n="bank">Bank</th>
                            <th data-i18n="currency">Currency</th>
                            <th data-i18n="created_at">Created At</th>
                        </tr>
                    </thead>
                    <tbody id="interestHistoryRows">${rows}</tbody>
                </table>
            </div>
            <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:12px;padding:10px;border:1px solid var(--border-color);border-radius:10px;background:var(--bg-secondary);">
                <div><span data-i18n="total_records">Total Records</span> : <strong>${totalRecords}</strong></div>
                <div><span data-i18n="total_interest_paid">Total Interest Paid</span> : <strong>${fmt(totalInterestPaid)}</strong></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" onclick="closeModal()" data-i18n="btn_close">Close</button>
        </div>
    `);
    applyTranslations();
}

function formatCertificateHistoryDate(value) {
    if (!value) return '—';
    const dt = new Date(`${value}T00:00:00`);
    if (Number.isNaN(dt.getTime())) return value;
    const day = String(dt.getDate()).padStart(2, '0');
    const month = dt.toLocaleString(undefined, { month: 'short' });
    const year = dt.getFullYear();
    return `${day}-${month}-${year}`;
}

function formatCertificateFrequencyLabel(value) {
    const freq = String(value || '').trim().toLowerCase();
    if (freq === 'monthly') return t('freq_monthly', 'Monthly');
    if (freq === 'quarterly') return t('freq_quarterly', 'Quarterly');
    if (freq === 'semi_annually' || freq === 'semi-annually' || freq === 'semi annually' || freq === 'semiannual') return t('freq_semi_annually', 'Semi-Annually');
    if (freq === 'annually' || freq === 'annual' || freq === 'yearly') return t('freq_annually', 'Annually');
    if (freq === 'at_maturity') return t('freq_at_maturity', 'At Maturity');
    return value || '—';
}

function addMonthsKeepDay(baseDate, months) {
    const d = new Date(baseDate.getTime());
    const targetMonth = d.getMonth() + months;
    const targetYear = d.getFullYear() + Math.floor(targetMonth / 12);
    const month = ((targetMonth % 12) + 12) % 12;
    const day = d.getDate();
    const lastDay = new Date(targetYear, month + 1, 0).getDate();
    return new Date(targetYear, month, Math.min(day, lastDay));
}

function formatCertificateHistoryDateFromDate(dateObj) {
    if (!(dateObj instanceof Date) || Number.isNaN(dateObj.getTime())) return '—';
    const day = String(dateObj.getDate()).padStart(2, '0');
    const month = dateObj.toLocaleString(undefined, { month: 'short' });
    const year = dateObj.getFullYear();
    return `${day}-${month}-${year}`;
}

function getCertificateNextPostingDate(certificate, items) {
    const status = String(certificate.status || '').trim().toLowerCase();
    if (status !== 'active') return '—';

    const issue = certificate.issue_date ? new Date(`${certificate.issue_date}T00:00:00`) : null;
    if (!issue || Number.isNaN(issue.getTime())) return '—';

    const frequency = String(certificate.frequency || '').trim().toLowerCase();
    const stepMonthsMap = {
        monthly: 1,
        quarterly: 3,
        semi_annually: 6,
        'semi-annually': 6,
        'semi annually': 6,
        semiannual: 6,
        annually: 12,
        annual: 12,
        yearly: 12,
    };

    if (frequency === 'at_maturity') {
        return formatCertificateHistoryDate(certificate.expiry_date);
    }

    const stepMonths = stepMonthsMap[frequency];
    if (!stepMonths) return '—';

    let baseline = issue;
    if (items && items.length) {
        const latest = items
            .map((x) => x.posting_date)
            .filter(Boolean)
            .sort()
            .slice(-1)[0];
        if (latest) {
            const latestDt = new Date(`${latest}T00:00:00`);
            if (!Number.isNaN(latestDt.getTime())) {
                baseline = latestDt;
            }
        }
    }

    const nextPosting = addMonthsKeepDay(baseline, stepMonths);
    return formatCertificateHistoryDateFromDate(nextPosting);
}

function filterBankCertificateInterestHistoryRows() {
    const start = document.getElementById('interestHistoryStart')?.value || '';
    const end = document.getElementById('interestHistoryEnd')?.value || '';
    const rows = document.querySelectorAll('#interestHistoryRows tr[data-posting-date]');

    rows.forEach((row) => {
        const postingDate = row.getAttribute('data-posting-date') || '';
        const inStart = !start || postingDate >= start;
        const inEnd = !end || postingDate <= end;
        row.style.display = inStart && inEnd ? '' : 'none';
    });
}

window.showBankCertificateInterestHistory = showBankCertificateInterestHistory;
window.filterBankCertificateInterestHistoryRows = filterBankCertificateInterestHistoryRows;