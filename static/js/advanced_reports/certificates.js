'use strict';

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