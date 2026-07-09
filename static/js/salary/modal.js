'use strict';

async function showSalaryModal(entryId, companyId) {
    let entry = null;
    if (entryId) {
        const res  = await fetch(`/api/salary/?company=${companyId}`);
        const data = await res.json();
        entry = data.entries.find(e => e.id === entryId);
    }

    const opts = MONTHS.map(m =>
        `<option value="${m}" ${entry?.month === m ? 'selected' : ''}>${m}</option>`
    ).join('');

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title">${entry ? t('btn_edit', 'Edit') : t('btn_add', 'Add')} Entry</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="salary_year">Year</label>
                    <input type="number" class="form-control" id="mYear"
                        value="${entry ? entry.year : new Date().getFullYear()}">
                </div>
                <div class="col-6">
                    <label data-i18n="salary_month">Month</label>
                    <select class="form-select" id="mMonth">${opts}</select>
                </div>
                <div class="col-4">
                    <label data-i18n="salary_expected">Expected</label>
                    <input type="number" step="0.01" class="form-control" id="mExpected"
                        value="${entry ? entry.expected : ''}">
                </div>
                <div class="col-4">
                    <label data-i18n="salary_paid">Paid</label>
                    <input type="number" step="0.01" class="form-control" id="mPaid"
                        value="${entry ? entry.paid : ''}">
                </div>
                <div class="col-4">
                    <label data-i18n="salary_bonus">Bonus</label>
                    <input type="number" step="0.01" class="form-control" id="mBonus"
                        value="${entry ? entry.bonus : '0'}">
                </div>
                <div class="col-12">
                    <label data-i18n="notes">Notes</label>
                    <input type="text" class="form-control" id="mNotes"
                        value="${entry ? entry.notes : ''}">
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="saveSalaryEntry(${entryId}, ${companyId})"
                data-i18n="btn_save">Save</button>
        </div>`);

    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// CRUD
// ════════════════════════════════════════════════════════════════════════════