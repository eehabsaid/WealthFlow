'use strict';

async function generateCurrentSalary(companyId) {
    try {
        const response = await fetch('/api/salary/generate-current/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ company_id: companyId })
        });
        if (response.ok) {
            const data = await response.json();
            showToast(`Created: ${data.created}, Skipped: ${data.skipped}`, 'success');
            renderSalaryPage(companyId);
        } else {
            showToast('Failed to generate salary entries', 'error');
        }
    } catch (error) {
        showToast('Failed to generate salary entries', 'error');
    }
}

async function toggleSalaryPaid(salaryId, isPaid, companyId) {
    try {
        const response = await fetch(`/api/salary/${salaryId}/mark-paid/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mark_paid: isPaid })
        });
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                const msg = isPaid 
                    ? t('salary_marked_paid', 'Salary marked as paid. Bank balance updated.') 
                    : t('salary_payment_reversed', 'Payment reversed. Bank balance adjusted.');
                showToast(msg, 'success');
                renderSalaryPage(companyId);
            } else {
                showToast(data.message || 'Failed to update salary status', 'error');
            }
        } else {
            showToast('Failed to update salary status', 'error');
        }
    } catch (error) {
        showToast('Failed to update salary status', 'error');
    }
}

// ════════════════════════════════════════════════════════════════════════════
// MODAL — ADD / EDIT
// ════════════════════════════════════════════════════════════════════════════