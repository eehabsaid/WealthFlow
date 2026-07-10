'use strict';

// balance/overview.js — Overview tab renderer
// Renders: Currency Summary Cards + Total All Balances + Financial Intelligence
// Called by index.js with pre-fetched data. Zero API calls here.
// ════════════════════════════════════════════════════════════════════════════

function renderBalanceOverview(data) {
    const pane = document.getElementById('bal-pane-overview');
    if (!pane) return;

    const { totals, totalEGP, usdAmount, eurAmount, sarAmount, usdRate, eurRate, sarRate,
            goldValue, grandTotal, netWorth, cashEGP, forecastData, formulaDesc, grandTotalLabel } = data;

    const currencyCards = _currencies.map((cur) => {
        const lookupKey = (cur.code === 'GOLD' || cur.code === 'Gold')
            ? (totals.GOLD !== undefined ? 'GOLD' : 'Gold')
            : cur.code;
        const cardValue = totals[lookupKey] || 0;
        return `
            <div class="col-6 col-md-4 col-lg-2">
                <div class="currency-card">
                    <div class="cur-flag">${cur.flag || '💱'}</div>
                    <div class="cur-code" data-i18n="${cur.code}">${cur.code}</div>
                    <div class="cur-amount num-fmt" data-value="${cardValue}">${fmt(cardValue)}</div>
                </div>
            </div>`;
    }).join('');

    pane.innerHTML = `
        <div class="row g-3 mb-4">${currencyCards}</div>

        <div class="kpi-card mb-4" style="text-align:center">
            <div class="kpi-label" data-i18n="grand_total">${grandTotalLabel}</div>
            <div class="kpi-value num-fmtpresent" style="color:var(--accent-green);font-size:32px" data-value="${grandTotal}">
                ${fmtpresent(grandTotal)} <span data-i18n="EGP">EGP</span>
            </div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px" data-i18n="balance_formula_desc">
                ${formulaDesc}
            </div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px">
                <span class="num-fmt" data-value="${totalEGP}">${fmt(totalEGP)}</span> +
                (<span class="num-fmt" data-value="${usdAmount}">${fmt(usdAmount)}</span> * <span class="num-fmt" data-value="${usdRate}">${fmt(usdRate)}</span>) +
                (<span class="num-fmt" data-value="${eurAmount}">${fmt(eurAmount)}</span> * <span class="num-fmt" data-value="${eurRate}">${fmt(eurRate)}</span>) +
                (<span class="num-fmt" data-value="${sarAmount}">${fmt(sarAmount)}</span> * <span class="num-fmt" data-value="${sarRate}">${fmt(sarRate)}</span>) +
                <span class="num-fmt" data-value="${goldValue}">${fmt(goldValue)}</span>
            </div>
            <div style="margin-top:8px;color:var(--text-secondary);font-size:13px">
                <span class="num-fmt" data-value="${totalEGP}">${fmt(totalEGP)}</span> +
                (<span class="num-fmt" data-value="${usdAmount * usdRate}">${fmt(usdAmount * usdRate)}</span>) +
                (<span class="num-fmt" data-value="${eurAmount * eurRate}">${fmt(eurAmount * eurRate)}</span>) +
                (<span class="num-fmt" data-value="${sarAmount * sarRate}">${fmt(sarAmount * sarRate)}</span>) +
                (<span class="num-fmt" data-value="${goldValue}">${fmt(goldValue)}</span>)
            </div>
        </div>

        <div class="kpi-card mb-4 fi-intelligence-card">
            <div class="kpi-label" data-i18n="financial_intelligence">Financial Intelligence</div>
            <div class="fi-metric-card-grid">
                <div class="fi-metric-tile fi-priority">
                    <div class="fi-metric-icon">💎</div>
                    <div class="fi-metric-title" data-i18n="net_worth">Net Worth</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${netWorth}">${fmtpresent(netWorth)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile fi-priority">
                    <div class="fi-metric-icon">💰</div>
                    <div class="fi-metric-title" data-i18n="liquid_cash">Liquid Cash</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${forecastData.cash_balance || 0}">${fmtpresent(forecastData.cash_balance || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile">
                    <div class="fi-metric-icon">🏦</div>
                    <div class="fi-metric-title" data-i18n="certificate_investments">Certificate Investments</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${forecastData.certificate_balance || 0}">${fmtpresent(forecastData.certificate_balance || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile">
                    <div class="fi-metric-icon">💵</div>
                    <div class="fi-metric-title" data-i18n="liquid_egp_cash">Liquid EGP CASH</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${cashEGP}">${fmtpresent(cashEGP)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile">
                    <div class="fi-metric-icon">🌍</div>
                    <div class="fi-metric-title" data-i18n="foreign_currency_value">Foreign Currency Value</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${usdAmount * usdRate + eurAmount * eurRate + sarAmount * sarRate}">${fmtpresent(usdAmount * usdRate + eurAmount * eurRate + sarAmount * sarRate)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile">
                    <div class="fi-metric-icon">🥇</div>
                    <div class="fi-metric-title" data-i18n="gold_value">Gold Value</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${goldValue}">${fmtpresent(goldValue)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile fi-priority">
                    <div class="fi-metric-icon">👤</div>
                    <div class="fi-metric-title" data-i18n="monthly_salary">Monthly Salary</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${forecastData.monthly_salary || 0}">${fmtpresent(forecastData.monthly_salary || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile">
                    <div class="fi-metric-icon">🏛️</div>
                    <div class="fi-metric-title" data-i18n="certificate_income">Certificate Income</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${forecastData.monthly_certificate_income || 0}">${fmtpresent(forecastData.monthly_certificate_income || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile">
                    <div class="fi-metric-icon">🏠</div>
                    <div class="fi-metric-title" data-i18n="monthly_rental_income">Rental Income</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${forecastData.monthly_rental_income || 0}">${fmtpresent(forecastData.monthly_rental_income || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile">
                    <div class="fi-metric-icon">📊</div>
                    <div class="fi-metric-title" data-i18n="income_dependency">Income Dependency</div>
                    <div class="fi-metric-main"><span class="num-fmt" data-value="${forecastData.certificate_income_ratio || 0}">${fmt(forecastData.certificate_income_ratio || 0)}</span>%</div>
                    <div class="fi-metric-sub" data-i18n="certificate_income">Certificate Income</div>
                </div>
                <div class="fi-metric-tile fi-priority fi-expense-tile">
                    <div class="fi-metric-icon">🧾</div>
                    <div class="fi-metric-title" data-i18n="monthly_expenses">Monthly Expenses</div>
                    <div class="fi-metric-main num-fmtpresent" data-value="${forecastData.avg_monthly_expenses || 0}">${fmtpresent(forecastData.avg_monthly_expenses || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-metric-tile">
                    <div class="fi-metric-icon">🛡️</div>
                    <div class="fi-metric-title" data-i18n="cash_coverage">Cash Coverage</div>
                    <div class="fi-metric-main"><span class="num-fmt" data-value="${forecastData.cash_coverage_months || 0}">${fmt(forecastData.cash_coverage_months || 0)}</span></div>
                    <div class="fi-metric-sub" data-i18n="months">Months</div>
                </div>
            </div>
        </div>
    `;
}
