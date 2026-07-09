'use strict';

async function saveSalaryEntry(entryId, companyId) {
    const body = {
        company_id: companyId,
        year:       parseInt(document.getElementById('mYear').value),
        month:      document.getElementById('mMonth').value,
        expected:   parseFloat(document.getElementById('mExpected').value) || 0,
        paid:       parseFloat(document.getElementById('mPaid').value)     || 0,
        bonus:      parseFloat(document.getElementById('mBonus').value)    || 0,
        notes:      document.getElementById('mNotes').value,
    };

    const url    = entryId ? `/api/salary/${entryId}/` : '/api/salary/';
    const method = entryId ? 'PUT' : 'POST';

    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
    });

    if (res.ok) {
        closeModal();
        showToast(`${t('btn_save', 'Saved')} ✓`);
        renderSalaryPage(companyId);
    } else {
        const err = await res.json();
        showToast(JSON.stringify(err), 'error');
    }
}

async function deleteSalaryEntry(entryId, companyId) {
    if (!confirm('Delete this entry?')) return;
    const res = await fetch(`/api/salary/${entryId}/`, { method: 'DELETE' });
    if (res.ok) {
        showToast('Deleted');
        renderSalaryPage(companyId);
    }
}

// ════════════════════════════════════════════════════════════════════════════
// PER DIEM FUNCTIONS
// ════════════════════════════════════════════════════════════════════════════