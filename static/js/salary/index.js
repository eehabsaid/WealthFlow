'use strict';

// salary.js — Dashboard and salary page rendering

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ════════════════════════════════════════════════════════════════════════════

const MONTHS = [
    'January', 'February', 'March',     'April',
    'May',     'June',     'July',      'August',
    'September','October', 'November',  'December',
];

// ════════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ════════════════════════════════════════════════════════════════════════════

async function renderSalaryPage(companyId) {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const company = (_companies || []).find(c => c.id === companyId);
    const res     = await fetch(`/api/salary/?company=${companyId}`);
    const data    = await res.json();
    const entries = data.entries;

    const years      = [...new Set(entries.map(e => e.year))].sort();
    const activeYear = years[years.length - 1] || new Date().getFullYear();

    mc.innerHTML = `
        <div class="page-header d-flex justify-content-between align-items-center">
            <div>
                <div class="page-title">${company ? company.display_name : ''}</div>
                <div class="page-subtitle">${company ? (company.group_name || '') : ''}</div>
            </div>
            <div style="display:flex;gap:10px">
                <button class="btn btn-success btn-primary-custom" onclick="generateCurrentSalary(${companyId})" data-i18n="generate_current_month">
                    🔄 Generate Current Month
                </button>
                <button class="btn btn-primary-custom" onclick="showPerDiemListModal(${companyId})" data-i18n="per_diem">
                    ✈️ Per Diem
                </button>
            </div>
        </div>
        <div class="year-pills" id="yearPills"></div>
        <div id="salaryTableArea"></div>`;

    renderYearPills(years, activeYear, companyId);
    renderSalaryTable(entries, activeYear, companyId);
}

// ── Year pills ────────────────────────────────────────────────────────────

function renderYearPills(years, activeYear, companyId) {
    const container = document.getElementById('yearPills');
    if (!container) return;
    container.innerHTML = years.map(y => `
        <button class="year-pill ${y === activeYear ? 'active' : ''}"
            onclick="switchYear(${y}, ${companyId})">${y}</button>`
    ).join('');
}

async function switchYear(year, companyId) {
    document.querySelectorAll('.year-pill').forEach(p =>
        p.classList.toggle('active', parseInt(p.textContent) === year));
    const res  = await fetch(`/api/salary/?company=${companyId}`);
    const data = await res.json();
    renderSalaryTable(data.entries, year, companyId);
}

// ── Salary table ──────────────────────────────────────────────────────────


window.showPerDiemListModal = showPerDiemListModal;
window.filterPerDiems = filterPerDiems;
window.showPerDiemFormModal = showPerDiemFormModal;
window.recalcPerDiemEgp = recalcPerDiemEgp;
window.savePerDiem = savePerDiem;
window.deletePerDiem = deletePerDiem;
