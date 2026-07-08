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

async function renderDashboard() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const res  = await fetch('/api/salary/summary/');
    const data = await res.json();
    const g    = data.grand_total;

    // Sum remaining manually to ensure footer matches company rows
    const sumRemaining = data.companies.reduce((sum, c) => sum + c.total_remaining, 0);

    const companyRows = data.companies.map(c => `
        <tr>
            <td>
                <span style="background:${c.color_hex};display:inline-block;
                             width:8px;height:8px;border-radius:50%;margin-right:6px"></span>
                ${c.display_name}
                ${c.group_name ? `<span class="group-badge">${c.group_name}</span>` : ''}
            </td>
            <td>${c.years.length > 0 ? `${c.years[0]} – ${c.years[c.years.length - 1]}` : '—'}</td>
            <td>${c.total_months}</td>
            <td class="text-end">${fmt(c.total_expected)}</td>
            <td class="text-end amt-positive">${fmt(c.total_paid)}</td>
            <td class="text-end ${amtClass(c.total_remaining)}">${fmt(c.total_remaining)}</td>
        </tr>`).join('');

    try {
        mc.innerHTML = `
            <div class="page-header">
                <div><div class="page-title" data-i18n="dashboard">Dashboard</div></div>
            </div>

            <button class="btn-primary-custom" onclick="window.location.href='/api/export/excel/'">
                <i class="bi bi-file-earmark-excel"></i>
                <span data-i18n="download_excel"></span>
            </button>

            <div class="row g-3 mb-4">
                ${kpiCard('kpi_total_earned',    fmt(g.total_expected), 'bi-cash-stack',      'var(--accent-primary)')}
                ${kpiCard('kpi_total_paid',      fmt(g.total_paid),     'bi-check-circle',    'var(--accent-green)')}
                ${kpiCard('kpi_total_remaining', fmt(sumRemaining),     'bi-hourglass-split', sumRemaining > 0 ? 'var(--accent-red)' : 'var(--text-muted)')}
                ${kpiCard('kpi_work_months',     fmtInt(g.total_months),        'bi-calendar3',       'var(--accent-yellow)')}
            </div>

            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                        border-radius:12px;padding:20px;margin-bottom:24px">
                <canvas id="salaryChart" height="80"></canvas>
            </div>

            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                        border-radius:12px;overflow:visible">
                <div class="table-container">
                <table class="data-table">
                    <thead><tr>
                        <th data-i18n="company">Company</th>
                        <th>Years</th>
                        <th data-i18n="work_months">Months</th>
                        <th class="text-end" data-i18n="salary_expected">Expected</th>
                        <th class="text-end" data-i18n="salary_paid">Paid</th>
                        <th class="text-end" data-i18n="salary_remaining">Remaining</th>
                    </tr></thead>
                    <tbody>${companyRows}</tbody>
                    <tfoot><tr class="total-row">
                        <td colspan="2" data-i18n="grand_total">Grand Total</td>
                        <td>${g.total_months}</td>
                        <td class="text-end">${fmt(g.total_expected)}</td>
                        <td class="text-end">${fmt(g.total_paid)}</td>
                        <td class="text-end">${fmt(sumRemaining)}</td>
                    </tr></tfoot>
                </table>
                </div>
            </div>`;

        applyTranslations();
        drawDashboardChart(data.companies);
        _renderDashboardEnhancements();

    } catch (err) {
        console.error('Dashboard Render Error:', err);
        mc.innerHTML = '<div class="alert alert-danger">Error loading dashboard. Check console.</div>';
    }
}

// ── Dashboard enhancements — expiring certs + active reminders ────────────

async function _renderDashboardEnhancements() {
    try {
        const [summRes, settRes] = await Promise.all([
            fetch('/api/dashboard/summary/'),
            fetch('/api/settings/'),
        ]);
        if (!summRes.ok) return;

        const d    = await summRes.json();
        const sett = settRes.ok ? (await settRes.json()).settings || {} : {};
        const mc   = document.getElementById('main-content');
        if (!mc) return;

        let html = '';

        // Expiring certificates widget
        if (sett.dashboard_show_certs !== 'false' && d.expiring_soon?.length > 0) {
            const rows = d.expiring_soon.map(c => `
                <tr>
                    <td>${c['bank__name'] || '—'}</td>
                    <td style="white-space:nowrap">${c.expiry_date}</td>
                    <td class="text-end">
                        ${(parseFloat(c.amount) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td>
                        <span style="color:${c.days_left <= 7 ? 'var(--accent-danger)' : c.days_left <= 30 ? '#f59e0b' : 'var(--accent-green)'};font-weight:700">
                            ${c.days_left}d
                        </span>
                    </td>
                    <td>
                        <span style="background:var(--bg-tertiary);padding:2px 8px;border-radius:8px;font-size:11px">
                            ${c.status || '—'}
                        </span>
                    </td>
                </tr>`).join('');

            html += `
                <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                            border-radius:12px;margin-top:20px;overflow:visible">
                    <div style="padding:14px 20px;display:flex;justify-content:space-between;
                                align-items:center;border-bottom:1px solid var(--border-color)">
                        <div style="font-weight:700;color:var(--text-primary)">
                            ⚠️ <span data-i18n="expiring_certs_title">Certificates Expiring Soon</span>
                            <span style="background:var(--accent-danger);color:#fff;border-radius:10px;
                                         padding:1px 7px;font-size:11px;margin-left:6px">
                                ${d.expiring_soon.length}
                            </span>
                        </div>
                        <button class="btn-secondary-custom"
                            onclick="navigate('bank-certificates')"
                            data-i18n="view_all">View All</button>
                    </div>
                    <div class="table-container">
                    <table class="data-table">
                        <thead><tr>
                            <th data-i18n="bank">Bank</th>
                            <th data-i18n="expiry_date">Expiry</th>
                            <th class="text-end" data-i18n="amount">Amount (EGP)</th>
                            <th data-i18n="days_left">Days Left</th>
                            <th data-i18n="status">Status</th>
                        </tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                    </div>
                </div>`;
        }

        // Active reminders widget
        if (sett.dashboard_show_reminders !== 'false' && d.active_reminders?.length > 0) {
            const rems = d.active_reminders.map(r => `
                <div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--border-color)">
                    <span style="font-size:16px">🔔</span>
                    <div>
                        <div style="font-size:12px;font-weight:700;color:var(--text-primary)">${r.rule}</div>
                        <div style="font-size:12px;color:var(--text-secondary)">${r.message}</div>
                    </div>
                </div>`).join('');

            html += `
                <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                            border-radius:12px;margin-top:16px;padding:16px 20px">
                    <div style="font-weight:700;color:var(--text-primary);margin-bottom:10px">
                        🔔 <span data-i18n="active_reminders">Active Reminders Today</span>
                    </div>
                    ${rems}
                </div>`;
        }

        if (html) {
            mc.insertAdjacentHTML('beforeend', html);
            applyTranslations();
        }
    } catch (e) {}
}

// ── KPI card helper ───────────────────────────────────────────────────────

function kpiCard(label, value, icon, color) {
    // Run the key through your global translation helper function t() so it drops the actual text inside the div
    const titleText = typeof t === 'function' ? t(label, label) : label;
    return `
        <div class="col-6 col-lg-3">
            <div class="kpi-card">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                    <i class="bi ${icon}" style="font-size:20px;color:${color}"></i>
                    <div class="kpi-label" data-i18n="${label}">${titleText}</div>
                </div>
                <div class="kpi-value" style="color:${color}">${value}</div>
            </div>
        </div>`;
}

// ── Dashboard chart ───────────────────────────────────────────────────────

function drawDashboardChart(companies) {
    const ctx = document.getElementById('salaryChart');
    if (!ctx) return;

    // Aggregate by group_name, falling back to display_name
    const groupMap = {};
    companies.forEach(c => {
        const key = c.group_name || c.display_name;
        if (!groupMap[key]) {
            groupMap[key] = { name: key, total_paid: 0, color: c.color_hex };
        }
        groupMap[key].total_paid += c.total_paid;
    });

    const groups   = Object.values(groupMap);
    const isMobile = window.innerWidth < 768;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels:   groups.map(g => g.name),
            datasets: [{
                label:           t('salary_paid', 'Total Paid'),
                data:            groups.map(g => g.total_paid),
                backgroundColor: groups.map(g => g.color + 'bb'),
                borderColor:     groups.map(g => g.color),
                borderWidth:     1,
                borderRadius:    6,
            }],
        },
        options: {
            responsive:          true,
            maintainAspectRatio: !isMobile,
            indexAxis:           isMobile ? 'y' : 'x',
            plugins: {
                legend: { labels: { color: '#7b93c9' } },
            },
            scales: {
                x: { ticks: { color: '#7b93c9' }, grid: { color: '#1e3a6e44' } },
                y: { ticks: { color: '#7b93c9' }, grid: { color: '#1e3a6e44' } },
            },
        },
    });
}

// ════════════════════════════════════════════════════════════════════════════
// SALARY PAGE (per company)
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

function renderSalaryTable(allEntries, year, companyId) {
    const area = document.getElementById('salaryTableArea');
    if (!area) return;

    const entries = allEntries.filter(e => e.year === year);

    let totExp = 0, totPaid = 0, totBonus = 0, totRemaining = 0;
    entries.forEach(e => {
        totExp       += e.expected;
        totPaid      += e.paid;
        totBonus     += e.bonus;
        totRemaining += e.remaining;
    });

    const rows = entries.map(e => `
        <tr>
            <td>
                <input type="checkbox" class="form-check-input" ${e.paid > 0 ? 'checked' : ''} onchange="toggleSalaryPaid(${e.id}, this.checked, ${companyId})">
            </td>
            <td>${e.month}</td>
            <td class="text-end">${fmt(e.expected)}</td>
            <td class="text-end amt-positive">${fmt(e.paid)}</td>
            <td class="text-end amt-positive">
                ${e.bonus > 0 ? fmt(e.bonus) : '<span class="amt-zero">—</span>'}
            </td>
            <td class="text-end ${amtClass(e.remaining)}">${fmt(e.remaining)}</td>
            <td>
                <button class="btn-icon" onclick="showSalaryModal(${e.id}, ${companyId})" title="Edit">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn-icon del" onclick="deleteSalaryEntry(${e.id}, ${companyId})" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>`).join('');

    const emptyRow = `<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px">
        No entries for this year.</td></tr>`;

    area.innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th style="width: 40px;" data-i18n="mark_paid">✓</th>
                    <th data-i18n="salary_month">Month</th>
                    <th class="text-end" data-i18n="salary_expected">Expected</th>
                    <th class="text-end" data-i18n="salary_paid">Paid</th>
                    <th class="text-end" data-i18n="salary_bonus">Bonus</th>
                    <th class="text-end" data-i18n="salary_remaining">Remaining</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows || emptyRow}</tbody>
                <tfoot><tr class="total-row">
                    <td colspan="2" data-i18n="total">Total</td>
                    <td class="text-end">${fmt(totExp)}</td>
                    <td class="text-end">${fmt(totPaid)}</td>
                    <td class="text-end">${fmt(totBonus)}</td>
                    <td class="text-end ${amtClass(totRemaining)}">${fmt(totRemaining)}</td>
                    <td></td>
                </tr></tfoot>
            </table>
            </div>
        </div>
        
        <div class="alert alert-info py-3 px-4 mt-4" style="border: 1px solid rgba(13, 110, 253, 0.25); background: rgba(13, 110, 253, 0.05); color: var(--text-primary); border-radius: 12px;">
            <h6 style="color: var(--accent-primary); font-weight: 700; margin-bottom: 10px;">✓ How it works:</h6>
            <ul style="margin-bottom: 0; padding-left: 20px; font-size: 13px; line-height: 1.6; color: var(--text-secondary);">
                <li>Check the ✓ box to mark salary as paid</li>
                <li>Unchecking reverses the payment (removes from bank balance)</li>
                <li>Payment goes to the default bank configured for this company</li>
                <li>"Generate Current Month" creates entries for missing months</li>
                <li>Uses current_salary_amount from company payroll config</li>
            </ul>
        </div>`;

    applyTranslations();
}

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

async function showPerDiemListModal(companyId, year) {
    if (!year) {
        year = parseInt(document.querySelector('.year-pill.active')?.textContent) || new Date().getFullYear();
    }
    
    // Show spinner while loading
    showModal('<div class="modal-body text-center py-5"><div class="spinner-border text-primary"></div></div>');
    
    try {
        const [pdRes, bRes] = await Promise.all([
            fetch(`/api/per-diems/?company_id=${companyId}&year=${year}`),
            fetch('/api/banks/')
        ]);
        const pdData = await pdRes.json();
        const bData = await bRes.json();
        
        const perDiems = pdData.entries || [];
        const banks = bData.banks || [];
        
        const modalHtml = `
            <div class="modal-header">
                <h5 class="modal-title" data-i18n="per_diem_list">Per Diem List</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div style="display:flex; align-items:center; gap:8px">
                        <label data-i18n="currency_filter" style="margin-bottom:0">Currency Filter</label>
                        <select class="form-select form-select-sm" id="pdCurrencyFilter" style="width:120px" onchange="filterPerDiems()">
                            <option value="ALL" data-i18n="all_option">All</option>
                        </select>
                    </div>
                    <button class="btn btn-primary btn-sm btn-primary-custom" onclick="showPerDiemFormModal(null, ${companyId}, ${year})" data-i18n="add_per_diem">
                        <i class="bi bi-plus-lg"></i> Add Per Diem
                    </button>
                </div>
                
                <div class="table-container" style="max-height: 400px; overflow-y: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th data-i18n="date">Date</th>
                                <th data-i18n="currency">Currency</th>
                                <th class="text-end" data-i18n="amount_label">Amount</th>
                                <th class="text-end" data-i18n="amount_egp">Amount (EGP)</th>
                                <th data-i18n="received_in">Received In</th>
                                <th data-i18n="notes">Notes</th>
                                <th data-i18n="actions">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="perDiemTableBody">
                        </tbody>
                        <tfoot id="perDiemTableFoot">
                        </tfoot>
                    </table>
                </div>
            </div>
        `;
        
        showModal(modalHtml);
        
        // Populate Currency Filter
        const filterSelect = document.getElementById('pdCurrencyFilter');
        const uniqueCurrencies = [...new Set(perDiems.map(pd => pd.currency_code))];
        uniqueCurrencies.forEach(code => {
            const opt = document.createElement('option');
            opt.value = code;
            opt.textContent = code;
            filterSelect.appendChild(opt);
        });
        
        window._currentPerDiems = perDiems;
        window._currentBanks = banks;
        window._currentCompanyId = companyId;
        window._currentYear = year;
        
        filterPerDiems();
    } catch (e) {
        showToast('Failed to load Per Diem data', 'error');
    }
}

function filterPerDiems() {
    const filterVal = document.getElementById('pdCurrencyFilter').value;
    const pds = window._currentPerDiems || [];
    
    const filtered = filterVal === 'ALL' ? pds : pds.filter(pd => pd.currency_code === filterVal);
    
    const tbody = document.getElementById('perDiemTableBody');
    const tfoot = document.getElementById('perDiemTableFoot');
    if (!tbody) return;
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center" data-i18n="no_records">No records found</td></tr>`;
        tfoot.innerHTML = '';
        applyTranslations();
        return;
    }
    
    tbody.innerHTML = filtered.map(pd => `
        <tr>
            <td>${pd.date}</td>
            <td>${pd.currency_flag} ${pd.currency_code}</td>
            <td class="text-end">${fmt(pd.amount)}</td>
            <td class="text-end amt-positive">${fmt(pd.amount_egp)}</td>
            <td>${pd.bank_name ? pd.bank_name : `<span class="badge bg-secondary" style="font-weight: normal;" data-i18n="cash_option">${t('cash_option', 'Cash')}</span>`}</td>
            <td>${pd.notes || ''}</td>
            <td>
                <button class="btn-icon" onclick="showPerDiemFormModal(${pd.id}, ${window._currentCompanyId}, ${window._currentYear})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="deletePerDiem(${pd.id})"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
    
    let sumAmount = 0;
    let sumEgp = 0;
    filtered.forEach(pd => {
        sumAmount += pd.amount;
        sumEgp += pd.amount_egp;
    });
    
    const displayAmount = filterVal === 'ALL' ? '—' : fmt(sumAmount);
    
    tfoot.innerHTML = `
        <tr style="font-weight:bold; background: rgba(13, 110, 253, 0.05)">
            <td colspan="2" data-i18n="totals">Totals</td>
            <td class="text-end">${displayAmount}</td>
            <td class="text-end amt-positive">${fmt(sumEgp)}</td>
            <td colspan="3"></td>
        </tr>
    `;
    
    applyTranslations();
}

async function showPerDiemFormModal(perDiemId, companyId, year) {
    const modalContent = document.querySelector('#customModal .modal-content');
    if (modalContent) {
        modalContent.innerHTML = '<div class="modal-body text-center py-5"><div class="spinner-border text-primary"></div></div>';
    }
    
    try {
        const [cRes, rRes, pdRes] = await Promise.all([
            fetch('/api/per-diems/currencies/'),
            fetch('/api/rates/'),
            perDiemId ? fetch(`/api/per-diems/${perDiemId}/`) : Promise.resolve(null)
        ]);
        
        const cData = await cRes.json();
        const rData = await rRes.json();
        const pd = pdRes ? await pdRes.json() : null;
        
        const currencies = cData.currencies || [];
        const rates = rData.rates || [];
        const banks = window._currentBanks || [];
        
        const currencyOpts = currencies.map(c => `
            <option value="${c.id}" data-code="${c.code}" ${pd && pd.currency_id === c.id ? 'selected' : ''}>
                ${c.flag} ${c.code}
            </option>
        `).join('');
        
        const bankOpts = banks.map(b => `
            <option value="${b.id}" ${pd && pd.bank_id === b.id ? 'selected' : ''}>
                ${b.name}
            </option>
        `).join('');
        
        const selectCurText = t('select_currency_option', '— Select currency —');
        const cashText = t('cash_option', 'Cash');
        
        const formHtml = `
            <div class="modal-header">
                <h5 class="modal-title" data-i18n="${pd ? 'edit_per_diem' : 'add_per_diem'}">${pd ? 'Edit Per Diem' : 'Add Per Diem'}</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="perDiemForm" onsubmit="event.preventDefault();">
                    <div class="row g-3">
                        <div class="col-6">
                            <label class="form-label" data-i18n="date">Date</label>
                            <input type="date" class="form-control" id="pdDate" required value="${pd ? pd.date : new Date().toISOString().substring(0, 10)}">
                        </div>
                        <div class="col-6">
                            <label class="form-label" data-i18n="received_in">Received In</label>
                            <select class="form-select" id="pdBank">
                                <option value="">${cashText}</option>
                                ${bankOpts}
                            </select>
                        </div>
                        
                        <div class="col-6">
                            <label class="form-label" data-i18n="amount_label">Amount</label>
                            <input type="number" step="0.01" min="0" class="form-control" id="pdAmount" required value="${pd ? pd.amount : ''}" oninput="recalcPerDiemEgp()">
                        </div>
                        <div class="col-6">
                            <label class="form-label" data-i18n="currency">Currency</label>
                            <select class="form-select" id="pdCurrency" required onchange="recalcPerDiemEgp()">
                                <option value="">${selectCurText}</option>
                                ${currencyOpts}
                            </select>
                        </div>
                        
                        <div class="col-12">
                            <label class="form-label" data-i18n="amount_egp">Amount (EGP)</label>
                            <input type="text" class="form-control" id="pdAmountEgp" readonly value="${pd ? fmt(pd.amount_egp) : '0.00'}">
                        </div>
                        
                        <div class="col-12">
                            <label class="form-label" data-i18n="notes">Notes</label>
                            <textarea class="form-control" id="pdNotes" rows="2">${pd ? pd.notes : ''}</textarea>
                        </div>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary btn-secondary-custom" onclick="showPerDiemListModal(${companyId}, ${year})" data-i18n="cancel_button">Cancel</button>
                <button class="btn btn-primary btn-primary-custom" onclick="savePerDiem(${perDiemId}, ${companyId}, ${year})" data-i18n="save_button">Save</button>
            </div>
        `;
        
        showModal(formHtml);
        applyTranslations();
        
        window._currentRates = rates;
        if (pd) {
            recalcPerDiemEgp();
        }
    } catch (e) {
        showToast('Failed to initialize Per Diem form', 'error');
    }
}

function recalcPerDiemEgp() {
    const amountVal = parseFloat(document.getElementById('pdAmount').value) || 0;
    const currencySelect = document.getElementById('pdCurrency');
    const selectedOpt = currencySelect.options[currencySelect.selectedIndex];
    
    if (!selectedOpt || !selectedOpt.value) {
        document.getElementById('pdAmountEgp').value = '0.00';
        return;
    }
    
    const code = selectedOpt.getAttribute('data-code');
    let rate = 1.0;
    
    if (code !== 'EGP') {
        const rates = window._currentRates || [];
        const rateObj = rates.find(r => r.currency_code === code);
        rate = rateObj ? rateObj.buy_rate : 0;
    }
    
    const amountEgp = amountVal * rate;
    document.getElementById('pdAmountEgp').value = fmt(amountEgp);
}

async function savePerDiem(perDiemId, companyId, year) {
    const form = document.getElementById('perDiemForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const body = {
        company_id: companyId,
        year: year,
        date: document.getElementById('pdDate').value,
        currency_id: parseInt(document.getElementById('pdCurrency').value),
        amount: parseFloat(document.getElementById('pdAmount').value),
        bank_id: document.getElementById('pdBank').value ? parseInt(document.getElementById('pdBank').value) : null,
        notes: document.getElementById('pdNotes').value
    };
    
    const url = perDiemId ? `/api/per-diems/${perDiemId}/` : '/api/per-diems/';
    const method = perDiemId ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
        
        if (response.ok) {
            showToast(t('per_diem_saved', 'Per Diem saved successfully'), 'success');
            showPerDiemListModal(companyId, year);
        } else {
            const err = await response.json();
            showToast(err.error || 'Failed to save Per Diem', 'error');
        }
    } catch (error) {
        showToast('Failed to save Per Diem', 'error');
    }
}

async function deletePerDiem(perDiemId) {
    const msg = t('delete_confirm', 'Are you sure you want to delete this Per Diem record?');
    if (!confirm(msg)) return;
    
    try {
        const response = await fetch(`/api/per-diems/${perDiemId}/`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast(t('per_diem_deleted', 'Per Diem deleted successfully'), 'success');
            showPerDiemListModal(window._currentCompanyId, window._currentYear);
        } else {
            const err = await response.json();
            showToast(err.error || 'Failed to delete Per Diem', 'error');
        }
    } catch (error) {
        showToast('Failed to delete Per Diem', 'error');
    }
}

// Expose functions globally
window.showPerDiemListModal = showPerDiemListModal;
window.filterPerDiems = filterPerDiems;
window.showPerDiemFormModal = showPerDiemFormModal;
window.recalcPerDiemEgp = recalcPerDiemEgp;
window.savePerDiem = savePerDiem;
window.deletePerDiem = deletePerDiem;
