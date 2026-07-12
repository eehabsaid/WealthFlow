'use strict';

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
    const rows = by_year.map((r, index) => `
        <tr ${index >= 5 ? 'class="hidden-salary-row" style="display:none"' : ''}>
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

    const showAllBtnHtml = by_year.length > 5 ? `
      <div class="card border-0" style="background:var(--bg-secondary); border-top:1px solid var(--border-color) !important; border-radius:0 0 12px 12px; cursor:pointer;" onclick="
        const container = this.closest('.table-container') ? this.closest('.table-container').parentNode : this.parentNode;
        const hiddenRows = container.querySelectorAll('.hidden-salary-row');
        const isShowingAll = this.getAttribute('data-showing') === 'true';
        hiddenRows.forEach(r => r.style.display = isShowingAll ? 'none' : 'table-row');
        this.setAttribute('data-showing', !isShowingAll);
        
        const span = this.querySelector('span');
        if (isShowingAll) {
            span.setAttribute('data-i18n-key', 'show_all_rows');
            span.setAttribute('data-i18n-params', JSON.stringify({ count: ${by_year.length} }));
        } else {
            span.setAttribute('data-i18n-key', 'show_less_rows');
            span.removeAttribute('data-i18n-params');
        }
        if (typeof applyTranslations === 'function') applyTranslations();
      ">
        <div class="card-body text-center" style="padding:12px;">
          <span style="color:var(--bs-primary, #0d6efd); font-weight:600; font-size:14px;" data-i18n-key="show_all_rows" data-i18n-params='{"count": ${by_year.length}}'></span>
        </div>
      </div>
    ` : '';

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
            ${showAllBtnHtml}
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