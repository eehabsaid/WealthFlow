// salary.js — Dashboard and salary page rendering

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ════════════════════════════════════════════════════════════════════════════

const MONTHS = [
    'January', 'February', 'March',     'April',
    'May',     'June',     'July',      'August',
    'September','October', 'November',  'December',
    'Quarter-Bonuses',
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
                ${kpiCard('kpi_work_months',     g.total_months,        'bi-calendar3',       'var(--accent-yellow)')}
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
    return `
        <div class="col-6 col-lg-3">
            <div class="kpi-card">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                    <i class="bi ${icon}" style="font-size:20px;color:${color}"></i>
                    <div class="kpi-label" data-i18n="${label}"></div>
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
        <div class="page-header">
            <div>
                <div class="page-title">${company ? company.display_name : ''}</div>
                <div class="page-subtitle">${company ? (company.group_name || '') : ''}</div>
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

    const emptyRow = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px">
        No entries for this year.</td></tr>`;

    area.innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="salary_month">Month</th>
                    <th class="text-end" data-i18n="salary_expected">Expected</th>
                    <th class="text-end" data-i18n="salary_paid">Paid</th>
                    <th class="text-end" data-i18n="salary_bonus">Bonus</th>
                    <th class="text-end" data-i18n="salary_remaining">Remaining</th>
                    <th data-i18n="actions">Actions</th>
                </tr></thead>
                <tbody>${rows || emptyRow}</tbody>
                <tfoot><tr class="total-row">
                    <td data-i18n="total">Total</td>
                    <td class="text-end">${fmt(totExp)}</td>
                    <td class="text-end">${fmt(totPaid)}</td>
                    <td class="text-end">${fmt(totBonus)}</td>
                    <td class="text-end ${amtClass(totRemaining)}">${fmt(totRemaining)}</td>
                    <td></td>
                </tr></tfoot>
            </table>
            </div>
        </div>`;

    applyTranslations();
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
