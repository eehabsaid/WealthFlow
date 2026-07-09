'use strict';

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
            <button class="wf-tab ${tab === tb.id ? 'active' : ''}"
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
        <div class="wf-tabs-shell">
          <div class="wf-tabs-row" id="advancedReportsTabsBar">
              ${tabBar}
          </div>
        </div>
        <div id="reportContent"></div>`;

    applyTranslations();
    if (typeof window.initTabsWithMoreMenu === 'function') {
        window.initTabsWithMoreMenu({
            containerId: 'advancedReportsTabsBar',
            visibleCount: 4,
            moreLabel: t('financial_advisor_tab_more', 'More'),
            tabSelector: '.wf-tab',
            activeClass: 'active',
        });
    }

    if (tab === 'salary')       await _renderSalaryReport();
    else if (tab === 'company') await _renderCompanyReport();
    else if (tab === 'balance') await _renderBalanceReport();
    else if (tab === 'certificates') await _renderCertReport();
}

// ── Salary & Bonus Report ──────────────────────────────────────

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