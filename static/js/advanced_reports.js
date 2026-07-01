// advanced_reports.js — Advanced Reports & Analytics (Feature 4)

async function renderAdvancedReports(tab) {
    tab = tab || 'salary';
    const mc = document.getElementById('main-content');
    mc.innerHTML = `<div style="display:flex;justify-content:center;padding:60px">
        <div class="spinner-border" style="color:var(--accent-primary)"></div></div>`;

        const tabs = [
            { id: 'salary',       key: 'report_salary',       icon: '💰' },
            { id: 'company',      key: 'report_company',      icon: '🏢' },
            { id: 'balance',      key: 'report_balance',      icon: '🏛️' },
            { id: 'certificates', key: 'report_certificates', icon: '🏦' },
        ];

        const tabBar = tabs.map(tb => `
            <button class="settings-tab ${tab === tb.id ? 'active' : ''}"
                onclick="renderAdvancedReports('${tb.id}');closeMobileSidebar && closeMobileSidebar()">
                ${tb.icon} <span data-i18n="${tb.key}"></span>
            </button>
        `).join('');

    mc.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title">📊 <span data-i18n="nav_advanced_reports"></span></div>
        
                <div style="color:var(--text-muted);font-size:13px" data-i18n="advanced_reports_subtitle"></div>
            </div>
        </div>
        <div style="border-bottom:1px solid var(--border-color);margin-bottom:20px;display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap">
            ${tabBar}
        </div>
        <div id="reportContent"></div>`;

    applyTranslations();

    if (tab === 'salary')       await _renderSalaryReport();
    else if (tab === 'company') await _renderCompanyReport();
    else if (tab === 'balance') await _renderBalanceReport();
    else if (tab === 'certificates') await _renderCertReport();
}

// ── Salary & Bonus Report ──────────────────────────────────────
async function _renderSalaryReport(selectedYear = '', selectedCompany = '') {
    const params = new URLSearchParams();
    if (selectedYear) params.set('year', selectedYear);
    if (selectedCompany) params.set('company_id', selectedCompany);

    const res = await fetch('/api/reports/salary/?' + params);
    const d   = await res.json();
    const by_year = d.by_year || [];
    const g       = d.grand || {};

    // KPIs
    const kpis = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px">
            ${_kpi('💵', 'total_paid', _fmt(g.total_paid), '')}
            ${_kpi('🎁', 'total_bonus', _fmt(g.total_bonus), '')}
            ${_kpi('📋', 'total_expected', _fmt(g.total_expected), '')}
            ${_kpi('📅', 'paid_months', g.paid_months || 0, '')}
        </div>`;

    // Chart
    const years  = by_year.map(r => r.year);
    const paid   = by_year.map(r => parseFloat(r.total_paid   || 0));
    const bonus  = by_year.map(r => parseFloat(r.total_bonus  || 0));
    const exp    = by_year.map(r => parseFloat(r.total_expected || 0));

    // Filters
    const yearOpts = ['<option value="">All Years</option>',
        ...d.years.map(y => `<option value="${y}" ${y === selectedYear ? 'selected' : ''}>${y}</option>`)].join('');
    const coOpts = ['<option value="">All Companies</option>',
        ...(d.companies||[]).map(c => `<option value="${c.id}" ${String(c.id) === selectedCompany ? 'selected' : ''}>${esc(c.name)}</option>`)].join('');

    // Table
    const rows = by_year.map(r => `
        <tr>
            <td><strong>${r.year}</strong></td>
            <td class="text-end">${_fmt(r.total_paid)}</td>
            <td class="text-end" style="color:var(--accent-green)">${_fmt(r.total_bonus)}</td>
            <td class="text-end">${_fmt(parseFloat(r.total_paid||0) + parseFloat(r.total_bonus||0))}</td>
            <td class="text-end">${_fmt(r.total_expected)}</td>
            <td class="text-end" style="color:${parseFloat(r.total_expected||0) > parseFloat(r.total_paid||0) ? 'var(--accent-danger)' : 'var(--accent-green)'}">
                ${_fmt(parseFloat(r.total_expected||0) - parseFloat(r.total_paid||0))}
            </td>
            <td class="text-end">${r.paid_months || 0}</td>
        </tr>`).join('');

    document.getElementById('reportContent').innerHTML = `
        <!-- Filters -->
        <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;align-items:flex-end">
            <div>
                <label style="font-size:12px;color:var(--text-muted)" data-i18n="filter_year">Year</label>
                <select class="form-select" id="salRepYear" style="margin-top:4px" onchange="_applySalaryFilter()">
                    ${yearOpts}
                </select>
            </div>
            <div>
                <label style="font-size:12px;color:var(--text-muted)" data-i18n="filter_company">Company</label>
                <select class="form-select" id="salRepCompany" style="margin-top:4px" onchange="_applySalaryFilter()">
                    ${coOpts}
                </select>
            </div>
        </div>
        ${kpis}
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;margin-bottom:16px">
            <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px" data-i18n="salary_by_year">Salary by Year</div>
            <div style="position:relative;height:280px"><canvas id="salaryTrendChart"></canvas></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="year">Year</th>
                    <th class="text-end" data-i18n="total_paid">Paid</th>
                    <th class="text-end" data-i18n="total_bonus">Bonus</th>
                    <th class="text-end" data-i18n="total_paid_incl_bonus">Total incl. Bonus</th>
                    <th class="text-end" data-i18n="total_expected">Expected</th>
                    <th class="text-end" data-i18n="remaining">Remaining</th>
                    <th class="text-end" data-i18n="paid_months">Paid Months</th>
                </tr></thead>
                <tbody>${rows || _noData(7)}</tbody>
                <tfoot>
                    <tr style="font-weight:700;background:var(--bg-tertiary)">
                        <td data-i18n="grand_total">Grand Total</td>
                        <td class="text-end">${_fmt(g.total_paid)}</td>
                        <td class="text-end">${_fmt(g.total_bonus)}</td>
                        <td class="text-end">${_fmt((g.total_paid||0)+(g.total_bonus||0))}</td>
                        <td class="text-end">${_fmt(g.total_expected)}</td>
                        <td class="text-end">${_fmt((g.total_expected||0)-(g.total_paid||0))}</td>
                        <td class="text-end">${g.paid_months || 0}</td>
                    </tr>
                </tfoot>
            </table>
            </div>
        </div>`;

    _drawBarChart('salaryTrendChart', years,
        [{ label: t('paid','Paid'), data: paid, color: '#1a6ef5' },
         { label: t('bonus','Bonus'), data: bonus, color: '#10b981' },
         { label: t('expected','Expected'), data: exp, color: '#f59e0b' }]);
    applyTranslations();
}

async function _applySalaryFilter() {
    const year = document.getElementById('salRepYear')?.value || '';
    const co   = document.getElementById('salRepCompany')?.value || '';
    await _renderSalaryReport(year, co);
}

// ── Company Summary Report ─────────────────────────────────────
async function _renderCompanyReport() {
    const res = await fetch('/api/reports/salary/');
    const d   = await res.json();
    const companies = d.by_company || [];

    const rows = companies.map(c => `
        <tr>
            <td>
                <span style="display:inline-flex;align-items:center;gap:8px">
                    ${c.color_hex ? `<span style="width:10px;height:10px;border-radius:50%;background:${c.color_hex};flex-shrink:0;display:inline-block"></span>` : ''}
                    <strong>${esc(c.company_name)}</strong>
                </span>
            </td>
            <td class="text-end">${c.paid_months || 0}</td>
            <td class="text-end">${_fmt(c.total_paid)}</td>
            <td class="text-end" style="color:var(--accent-green)">${_fmt(c.total_bonus)}</td>
            <td class="text-end">${_fmt(c.total_paid + c.total_bonus)}</td>
            <td class="text-end">${_fmt(c.total_expected)}</td>
            <td class="text-end">
                <div style="display:flex;align-items:center;gap:6px">
                    <div style="flex:1;background:var(--bg-tertiary);border-radius:4px;height:6px;overflow:hidden">
                        <div style="height:100%;background:var(--accent-primary);width:${Math.min(100,(c.total_paid/(d.grand.total_paid||1))*100).toFixed(1)}%"></div>
                    </div>
                    <span style="font-size:12px;color:var(--text-muted);width:40px;text-align:right">
                        ${((c.total_paid/(d.grand.total_paid||1))*100).toFixed(1)}%
                    </span>
                </div>
            </td>
        </tr>`).join('');

    const names  = companies.map(c => c.company_name);
    const totals = companies.map(c => c.total_paid + c.total_bonus);

    document.getElementById('reportContent').innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;margin-bottom:16px">
            <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px" data-i18n="total_by_company">Total by Company</div>
            <div style="position:relative;height:260px"><canvas id="companyChart"></canvas></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="company">Company</th>
                    <th class="text-end" data-i18n="paid_months">Months</th>
                    <th class="text-end" data-i18n="total_paid">Paid</th>
                    <th class="text-end" data-i18n="total_bonus">Bonus</th>
                    <th class="text-end" data-i18n="total_paid_incl_bonus">Total</th>
                    <th class="text-end" data-i18n="total_expected">Expected</th>
                    <th data-i18n="share">Share</th>
                </tr></thead>
                <tbody>${rows || _noData(7)}</tbody>
            </table>
            </div>
        </div>`;

    _drawPieChart('companyChart', names, totals);
    applyTranslations();
}

// ── Balance Report ─────────────────────────────────────────────
async function _renderBalanceReport() {
    const res = await fetch('/api/reports/balance/');
    const d   = await res.json();
    const banks = d.by_bank || [];
    const home  = d.home_entries || [];

    const bankRows = banks.map(b => `
        <tr>
            <td><strong>${esc(b.bank_name)}</strong></td>
            <td class="text-end">${_fmt(b.total_egp)} <span data-i18n="EGP"></span></td>
            <td>${b.entries.map(e => `<span style="font-size:11px;color:var(--text-muted)">${_fmt(e.amount)} ${e.currency_code||''}</span>`).join(', ')}</td>
        </tr>`).join('');

    const homeRows = home.map(e => `
        <tr>
            <td>${esc(e.title || 'Home')}</td>
            <td class="text-end">${_fmt(e.amount)} ${e.currency_code || ''}</td>
            <td style="color:var(--text-muted)">—</td>
        </tr>`).join('');

    const grandEGP = banks.reduce((s, b) => s + b.total_egp, 0)
                   + d.cert_total;

    document.getElementById('reportContent').innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px">
            ${_kpi('🏛️', 'bank_balance', _fmt(banks.reduce((s,b)=>s+b.total_egp,0)) + ' <span data-i18n="EGP"></span>', '')}
            ${_kpi('🏦', 'cert_balance', _fmt(d.cert_total) + ' <span data-i18n="EGP"></span>', '')}
            ${_kpi('💹', 'total_monthly_interest', _fmt(d.cert_interest) + ' <span data-i18n="EGP"></span>', '<span data-i18n="per_month">per month</span>')}
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible;margin-bottom:16px">
            <div style="padding:14px 20px;font-weight:700;color:var(--text-primary);border-bottom:1px solid var(--border-color)" data-i18n="bank_accounts">Bank Accounts</div>
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="bank">Bank</th>
                    <th class="text-end" data-i18n="egp_balance">EGP Balance</th>
                    <th data-i18n="other_currencies">Other Currencies</th>
                </tr></thead>
                <tbody>${bankRows || _noData(3)}</tbody>
            </table>
            </div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div style="padding:14px 20px;font-weight:700;color:var(--text-primary);border-bottom:1px solid var(--border-color)" data-i18n="home_cash">Home / Cash</div>
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="description">Description</th>
                    <th class="text-end" data-i18n="amount">Amount</th>
                    <th data-i18n="note">Note</th>
                </tr></thead>
                <tbody>${homeRows || _noData(3)}</tbody>
            </table>
            </div>
        </div>`;
    applyTranslations();
}

// ── Certificate Report ─────────────────────────────────────────
async function _renderCertReport() {
    const res = await fetch('/api/reports/certificates/');
    const d   = await res.json();
    const s   = d.summary || {};
    const cf  = d.monthly_cf || [];

    const bucketLabels = {
        overdue:    { key: 'overdue',          color: 'var(--accent-danger)' },
        '30_days':  { key: 'within_30_days',   color: '#f59e0b' },
        '90_days':  { key: 'within_90_days',   color: '#1a6ef5' },
        '180_days': { key: 'within_180_days',  color: '#10b981' },
        later:      { key: 'beyond_180_days',  color: 'var(--text-muted)' },
    };

    const bucketCards = Object.entries(d.buckets || {}).map(([key, certs]) => {
        // Fallback: If key not found, just use the raw string, otherwise get the key
        const bl = bucketLabels[key] || { key: null, color: 'var(--text-primary)', label: key };
        
        return `
            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:10px;padding:14px 16px">
                <div style="font-size:12px;font-weight:700;color:${bl.color};text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px" 
                    ${bl.key ? `data-i18n="${bl.key}"` : ''}>${bl.key ? '' : bl.label}</div>
                <div style="font-size:22px;font-weight:800;color:var(--text-primary)">${certs.length}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:2px">
                    ${_fmt(certs.reduce((s, c) => s + parseFloat(c.amount||0), 0))} <span data-i18n="EGP"></span>
                </div>
            </div>`;
    }).join('');

    const months = cf.map(m => m.month);
    const amounts = cf.map(m => m.amount);

    const statusRows = Object.entries(d.by_status || {}).map(([status, info]) => `
        <tr>
            <td>${esc(status)}</td>
            <td class="text-end">${info.count}</td>
            <td class="text-end">${_fmt(info.total)} EGP</td>
        </tr>`).join('');

    document.getElementById('reportContent').innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px">
            ${_kpi('🏦', 'total_certificates', s.total_count || 0, '')}
            ${_kpi('💵', 'total_amount', `<span>${_fmt(s.total_amount)}</span> <span data-i18n="EGP">EGP</span>`, '')}
            ${_kpi('💹', 'total_monthly_interest', `<span>${_fmt(s.monthly_interest)}</span> <span data-i18n="EGP">EGP</span>`, '<span data-i18n="per_month">per month</span>')}
        </div>
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px">
            ${bucketCards}
        </div>
        <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px">
            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px">
                <div style="font-weight:700;color:var(--text-primary);margin-bottom:14px" data-i18n="maturing_cashflow">Maturing Cashflow (Next 12 Months)</div>
                <div style="position:relative;height:220px"><canvas id="certCfChart"></canvas></div>
            </div>
            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
                <div style="padding:14px 16px;font-weight:700;color:var(--text-primary);border-bottom:1px solid var(--border-color)" data-i18n="by_status">By Status</div>
                <div class="table-container">
                <table class="data-table">
                    <thead><tr>
                        <th data-i18n="status">Status</th>
                        <th class="text-end" data-i18n="count">Count</th>
                        <th class="text-end" data-i18n="amount">Amount</th>
                    </tr></thead>
                    <tbody>${statusRows || _noData(3)}</tbody>
                </table>
                </div>
            </div>
        </div>`;

    _drawBarChart('certCfChart', months,
        [{ label: t('maturing_amount','Maturing Amount'), data: amounts, color: '#1a6ef5' }]);
    applyTranslations();
}

// ── Chart helpers ──────────────────────────────────────────────
function _drawBarChart(canvasId, labels, datasets) {
    setTimeout(() => {
        const ctx = document.getElementById(canvasId);
        if (!ctx || !window.Chart) return;
        if (ctx._chart) ctx._chart.destroy();
        ctx._chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: datasets.map(ds => ({
                    label: ds.label,
                    data: ds.data,
                    backgroundColor: ds.color + 'cc',
                    borderColor: ds.color,
                    borderRadius: 4,
                    borderWidth: 1,
                })),
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12 } } },
                scales: {
                    x: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                    y: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                },
            },
        });
    }, 50);
}

function _drawPieChart(canvasId, labels, data) {
    setTimeout(() => {
        const ctx = document.getElementById(canvasId);
        if (!ctx || !window.Chart) return;
        if (ctx._chart) ctx._chart.destroy();
        const colors = ['#1a6ef5','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899'];
        ctx._chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data, backgroundColor: colors.slice(0, data.length), borderWidth: 0 }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'right', labels: { color: '#94a3b8', boxWidth: 12, padding: 12 } } },
            },
        });
    }, 50);
}

// ── Shared helpers ─────────────────────────────────────────────
function _kpi(icon, label, value, sub) {
    // Check if the label is one of our known keys to decide on the data-i18n attribute
    // We assume your keys don't contain spaces, while normal labels do.
    const isKey = !label.includes(' ') && !label.includes('<');
    const attr = isKey ? `data-i18n="${label}"` : '';

    return `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:18px 20px" class="kpi-card">
            <div style="font-size:20px;margin-bottom:4px">${icon}</div>
            <div style="font-size:11px;font-weight:700;letter-spacing:.05em;color:var(--text-muted);text-transform:uppercase;margin-bottom:6px" ${attr}>${isKey ? '' : label}</div>
            <div style="font-size:22px;font-weight:800;color:var(--text-primary)" class="kpi-value">${value}</div>
            ${sub ? `<div style="font-size:12px;color:var(--text-muted);margin-top:4px">${sub}</div>` : ''}
        </div>`;
}

function _fmt(n) {
    return (parseFloat(n) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function _noData(cols) {
    return `<tr><td colspan="${cols}" style="text-align:center;padding:28px;color:var(--text-muted)" data-i18n="no_data">No data available</td></tr>`;
}

function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
