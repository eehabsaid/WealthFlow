'use strict';

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