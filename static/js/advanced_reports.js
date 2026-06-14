// advanced_reports.js — Advanced Reports & Analytics (Feature 5)
// Adds new tabs to the existing reports page pattern

async function renderAdvancedReports(tab) {
    tab = tab || 'salary_trends';
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const tabs = [
        { id: 'salary_trends',  label: t('adv_report_salary_trends','Salary Trends'),       icon: '📈' },
        { id: 'cert_summary',   label: t('adv_report_cert_summary','Certificate Summary'),   icon: '🏦' },
        { id: 'expense_trends', label: t('adv_report_expense_trends','Expense Trends'),      icon: '💸' },
    ];

    const tabBar = tabs.map(tb => `
        <button class="settings-tab ${tab === tb.id ? 'active' : ''}"
            onclick="renderAdvancedReports('${tb.id}')">${tb.icon} ${tb.label}</button>`).join('');

    mc.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title" data-i18n="nav_advanced_reports">📊 Advanced Analytics</div>
                <div style="color:var(--text-muted);font-size:13px" data-i18n="adv_reports_subtitle">Trends, summaries and analytics</div>
            </div>
        </div>
        <div style="border-bottom:1px solid var(--border-color);margin-bottom:20px;display:flex;gap:4px;overflow-x:auto;scrollbar-width:none">
            ${tabBar}
        </div>
        <div id="advReportContent"></div>`;

    applyTranslations();

    if (tab === 'salary_trends')  await _renderSalaryTrends();
    else if (tab === 'cert_summary') await _renderCertSummary();
    else if (tab === 'expense_trends') await _renderExpenseTrends();
}

// ── Salary Trends ────────────────────────────────────────────
async function _renderSalaryTrends() {
    const [trendsRes, companiesRes] = await Promise.all([
        fetch('/api/salary-trends/'),
        fetch('/api/companies/'),
    ]);
    const { trends, companies } = await trendsRes.json();
    const years  = trends.map(t => t.year);
    const paid   = trends.map(t => parseFloat(t.total_paid   || 0));
    const bonus  = trends.map(t => parseFloat(t.total_bonus  || 0));
    const expected = trends.map(t => parseFloat(t.total_expected || 0));

    const total_paid  = paid.reduce((a,b)=>a+b, 0);
    const total_bonus = bonus.reduce((a,b)=>a+b, 0);

    document.getElementById('advReportContent').innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:20px">
            ${_kpi('💰', t('total_salary_paid','Total Salary Paid'), fmt(total_paid), t('all_time','All time'))}
            ${_kpi('🎁', t('total_bonus','Total Bonus'), fmt(total_bonus), t('all_time','All time'))}
            ${_kpi('📅', t('years_active','Years Active'), years.length, t('with_paid_salary','with paid salary'))}
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;margin-bottom:20px">
            <div style="font-weight:700;color:var(--text-primary);margin-bottom:16px" data-i18n="salary_by_year">Salary by Year</div>
            <div class="chart-container" style="height:300px"><canvas id="salaryTrendChart"></canvas></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="year">Year</th>
                    <th class="text-end" data-i18n="total_paid">Total Paid</th>
                    <th class="text-end" data-i18n="total_bonus">Bonus</th>
                    <th class="text-end" data-i18n="total_expected">Expected</th>
                    <th class="text-end" data-i18n="remaining">Remaining</th>
                </tr></thead>
                <tbody>
                    ${trends.map(tr => `
                    <tr>
                        <td><strong>${tr.year}</strong></td>
                        <td class="text-end">${fmt(tr.total_paid)}</td>
                        <td class="text-end">${fmt(tr.total_bonus)}</td>
                        <td class="text-end">${fmt(tr.total_expected)}</td>
                        <td class="text-end" style="color:${parseFloat(tr.total_expected)>parseFloat(tr.total_paid)?'var(--accent-danger)':'var(--accent-green)'}">${fmt(parseFloat(tr.total_expected)-parseFloat(tr.total_paid))}</td>
                    </tr>`).join('')}
                </tbody>
            </table>
            </div>
        </div>`;

    // Draw chart
    setTimeout(() => {
        const ctx = document.getElementById('salaryTrendChart');
        if (!ctx || !window.Chart) return;
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: years,
                datasets: [
                    { label: t('total_paid','Paid'), data: paid, backgroundColor: 'rgba(26,110,245,0.7)', borderRadius: 4 },
                    { label: t('total_bonus','Bonus'), data: bonus, backgroundColor: 'rgba(16,185,129,0.7)', borderRadius: 4 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: {
                    x: { stacked: true, ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                    y: { stacked: true, ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                },
            },
        });
    }, 100);
}

// ── Certificate Summary ──────────────────────────────────────
async function _renderCertSummary() {
    const res = await fetch('/api/certificate-summary/');
    const data = await res.json();
    const { summary, upcoming_30, upcoming_90, by_status } = data;

    const statusRows = Object.entries(by_status).map(([s, c]) =>
        `<tr><td>${s}</td><td><strong>${c}</strong></td></tr>`).join('');

    const upcoming30Rows = upcoming_30.length === 0
        ? `<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--text-muted)" data-i18n="none_due">None due</td></tr>`
        : upcoming_30.map(c => `
            <tr>
                <td>${c.bank_name}</td>
                <td>${c.expiry_date}</td>
                <td class="text-end">${fmt(c.amount)}</td>
                <td><span style="background:var(--accent-danger);color:#fff;padding:2px 8px;border-radius:10px;font-size:11px">${c.status}</span></td>
            </tr>`).join('');

    document.getElementById('advReportContent').innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:20px">
            ${_kpi('🏦', t('total_certificates','Total Certificates'), summary.total_count, '')}
            ${_kpi('💵', t('total_amount','Total Amount'), fmt(summary.total_amount), '')}
            ${_kpi('💹', t('total_interest','Total Interest p.m.'), fmt(summary.total_interest/12), t('per_month','per month'))}
        </div>
        <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px">
            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px">
                <div style="font-weight:700;margin-bottom:14px;color:var(--text-primary)" data-i18n="maturing_30_days">⚠️ Maturing in 30 Days</div>
                <div class="table-container">
                <table class="data-table">
                    <thead><tr>
                        <th data-i18n="bank">Bank</th>
                        <th data-i18n="expiry_date">Expiry</th>
                        <th data-i18n="amount">Amount</th>
                        <th data-i18n="status">Status</th>
                    </tr></thead>
                    <tbody>${upcoming30Rows}</tbody>
                </table>
                </div>
            </div>
            <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px">
                <div style="font-weight:700;margin-bottom:14px;color:var(--text-primary)" data-i18n="by_status">By Status</div>
                <table class="data-table">
                    <thead><tr><th data-i18n="status">Status</th><th data-i18n="count">Count</th></tr></thead>
                    <tbody>${statusRows || '<tr><td colspan="2" style="padding:16px;color:var(--text-muted)">—</td></tr>'}</tbody>
                </table>
            </div>
        </div>`;
    applyTranslations();
}

// ── Expense Trends ───────────────────────────────────────────
async function _renderExpenseTrends() {
    const res = await fetch('/api/expenses/summary/');
    const data = await res.json();
    const yearly = data.yearly || {};
    const years = Object.keys(yearly).sort();
    const totals = years.map(y => parseFloat(yearly[y] || 0));

    document.getElementById('advReportContent').innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px;margin-bottom:20px">
            <div style="font-weight:700;color:var(--text-primary);margin-bottom:16px" data-i18n="expense_by_year">Expenses by Year</div>
            <div class="chart-container" style="height:280px"><canvas id="expTrendChart"></canvas></div>
        </div>
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
            <table class="data-table">
                <thead><tr>
                    <th data-i18n="year">Year</th>
                    <th class="text-end" data-i18n="total_expenses">Total Expenses</th>
                </tr></thead>
                <tbody>
                    ${years.map((y,i) => `<tr><td><strong>${y}</strong></td><td class="text-end">${fmt(totals[i])}</td></tr>`).join('')}
                </tbody>
            </table>
            </div>
        </div>`;

    setTimeout(() => {
        const ctx = document.getElementById('expTrendChart');
        if (!ctx || !window.Chart) return;
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: years,
                datasets: [{ label: t('expenses','Expenses'), data: totals,
                    borderColor: '#1a6ef5', backgroundColor: 'rgba(26,110,245,0.1)',
                    fill: true, tension: 0.3, pointRadius: 4 }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: {
                    x: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                    y: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                },
            },
        });
    }, 100);
    applyTranslations();
}

function _kpi(icon, label, value, sub) {
    return `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:20px">
            <div style="font-size:22px;margin-bottom:6px">${icon}</div>
            <div style="font-size:11px;font-weight:700;letter-spacing:.05em;color:var(--text-muted);text-transform:uppercase;margin-bottom:6px">${label}</div>
            <div style="font-size:24px;font-weight:800;color:var(--text-primary)">${value}</div>
            ${sub ? `<div style="font-size:12px;color:var(--text-muted);margin-top:4px">${sub}</div>` : ''}
        </div>`;
}

function fmt(n) {
    const num = parseFloat(n) || 0;
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
