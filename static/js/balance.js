// balance.js — Personal balance dashboard with assets, investments, and forecasts

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// MODULE STATE
// ════════════════════════════════════════════════════════════════════════════

let entries = [];

// ════════════════════════════════════════════════════════════════════════════
// BALANCE RENDERING
// ════════════════════════════════════════════════════════════════════════════

async function renderBalance() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    const [bRes, bankRes, currRes, forecastRes] = await Promise.all([
        fetch('/api/balance/'),
        fetch('/api/banks/'),
        fetch('/api/currencies/'),
        fetch('/api/certificate-forecast/'),
    ]);

    const bData = await bRes.json();
    const bankData = await bankRes.json();
    const currData = await currRes.json();
    const forecastData = await forecastRes.json();

    entries = bData.entries;
    window.entries = entries;
    _banks = bankData.banks;
    _currencies = currData.currencies || [];

    const summary = bData.summary || {};
    const totals = summary.totals_by_currency || {};

    const totalEGP = totals.EGP || 0;
    const cashEGP = summary.liquid_egp_cash ?? summary.cash_egp ?? 0;
    const certificateEGP = summary.certificate_egp || 0;
    const usdAmount = totals.USD || 0;
    const eurAmount = totals.EUR || 0;
    const sarAmount = totals.SAR || 0;
    const goldGrams = totals.GOLD || totals.Gold || 0;
    const usdRate = summary.usd_rate || 0;
    const eurRate = summary.eur_rate || 0;
    const sarRate = summary.sar_rate || 0;
    const goldValue = summary.gold_value || 0;
    const grandTotal = summary.grand_total || 0;
    const netWorth = summary.net_worth || grandTotal || 0;
    const allocationValues = summary.allocation_values || {};
    const cashAllocationValue = (allocationValues.type_cash || 0) + (allocationValues.type_bank || 0);

    const editText = t('edit', 'Edit');
    const deleteText = t('delete', 'Delete');
    const titleLabel = t('balance_title', 'Title');
    const typeLabel = t('balance_type', 'Balance Type');
    const bankLabel = t('balance_bank', 'Bank');
    const currencyLabel = t('balance_currency', 'Currency');
    const amountLabel = t('balance_amount', 'Amount');
    const actionsLabel = t('actions', 'Actions');

    const resolveI18nTemplate = (key, fallback, params = {}) => {
        let text = t(key, fallback || key);
        Object.entries(params || {}).forEach(([paramKey, rawValue]) => {
            let valueText = rawValue;
            const num = Number(rawValue);
            if (Number.isFinite(num)) {
                if (/days/i.test(paramKey)) {
                    valueText = fmtInt(num);
                } else if (/(ratio|trend|signal|gap|coverage|pct)/i.test(paramKey)) {
                    valueText = fmt(num);
                } else {
                    valueText = fmtpresent(num);
                }
            }
            text = text.split(`{${paramKey}}`).join(String(valueText));
        });
        return text;
    };

    const encodeI18nParams = (params = {}) => encodeURIComponent(JSON.stringify(params || {}));

    const investmentDetails = (forecastData.investment_recommendation_details || []).length
        ? (forecastData.investment_recommendation_details || [])
        : (forecastData.investment_recommendations || []).map((r) => {
            const key = typeof r === 'object' && r.key ? r.key : r;
            const params = typeof r === 'object' && r.days_left != null ? { days_left: r.days_left } : {};
            return { key, params, reason_key: '', reason_params: {} };
        });

    const financialDetails = (forecastData.financial_recommendation_details || []).length
        ? (forecastData.financial_recommendation_details || [])
        : (forecastData.financial_recommendations || []).map((key) => ({
            key,
            params: {},
            reason_key: '',
            reason_params: {},
        }));

    const actionReasonText = forecastData.action_plan?.reason_key
        ? resolveI18nTemplate(
            forecastData.action_plan.reason_key,
            forecastData.action_plan.reason_key,
            forecastData.action_plan.reason_params || {},
        )
        : '';

    const currencyCards = _currencies
    .map((cur) => {
        // 1. Resolve key variations for Gold safely, fallback to cur.code for normal currencies
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
            </div>
        `;
    })
    .join('');

    const bankMap = {};
    _banks.forEach((b) => { bankMap[b.id] = b.name; });

    const rows = entries
        .map((e) => `
            <tr>
                <td data-i18n-key="${e.title || ''}">${_t && _t[e.title] ? _t[e.title] : (e.title || '')}</td>
                <td data-i18n-prefix="type_" data-i18n-value="${e.balance_type || ''}">${_t && _t['type_' + e.balance_type] ? _t['type_' + e.balance_type] : (e.balance_type || '')}</td>
                <td data-i18n-prefix="bank_" data-i18n-value="${e.bank_name || ''}">${e.bank_name || '_'}</td>
                <td><span style="background:rgba(26,110,245,.15);color:var(--accent-primary);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">${e.currency_flag} ${e.currency_code}</span></td>
                <td>${e.balance_type === 'gold' ? (e.purity || '-') : '-'}</td>
                <td class="text-end amt-positive num-fmt" data-value="${e.amount}">${fmt(e.amount)}</td>
                <td>
                    <button class="btn-icon" onclick="showBalanceModal(${e.id})" title="${editText}"><i class="bi bi-pencil"></i></button>
                    <button class="btn-icon del" onclick="deleteBalanceEntry(${e.id})" title="${deleteText}"><i class="bi bi-trash"></i></button>
                </td>
            </tr>
        `)
        .join('');

    const balanceTitle = t('nav_balance', 'Balance');
    const grandTotalLabel = t('grand_total', 'Total All Balances (EGP equiv.)');
    const formulaDesc = t('balance_formula_desc', '= EGP + (USD x rate) + (EUR x rate) + (SAR x rate) + Sum(Gold amount x (purity sell price + purity cashback))');

    mc.innerHTML = `
        <div class="page-header">
            <div><div class="page-title" data-i18n="nav_balance">${balanceTitle}</div></div>
        </div>
        
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
        
        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="financial_intelligence">Financial Intelligence</div>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:20px;">
                <div><div class="kpi-label" data-i18n="net_worth">Net Worth</div><div class="kpi-value num-fmtpresent" data-value="${netWorth}">${fmtpresent(netWorth)}</div></div>
                <div><div class="kpi-label" data-i18n="liquid_cash">Liquid Cash</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.cash_balance || 0}">${fmtpresent(forecastData.cash_balance || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="certificate_investments">Certificate Investments</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.certificate_balance || 0}">${fmtpresent(forecastData.certificate_balance || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="liquid_egp_cash">Liquid EGP CASH</div><div class="kpi-value num-fmtpresent" data-value="${cashEGP}">${fmtpresent(cashEGP)}</div></div>
                <div><div class="kpi-label" data-i18n="foreign_currency_value">Foreign Currency Value</div><div class="kpi-value num-fmtpresent" data-value="${usdAmount * usdRate + eurAmount * eurRate + sarAmount * sarRate}">${fmtpresent(usdAmount * usdRate + eurAmount * eurRate + sarAmount * sarRate)}</div></div>
                <div><div class="kpi-label" data-i18n="gold_value">Gold Value</div><div class="kpi-value num-fmtpresent" data-value="${goldValue}">${fmtpresent(goldValue)}</div></div>
                <div><div class="kpi-label" data-i18n="monthly_salary">Monthly Salary</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.monthly_salary || 0}">${fmtpresent(forecastData.monthly_salary || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="certificate_income">Certificate Income</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.monthly_certificate_income || 0}">${fmtpresent(forecastData.monthly_certificate_income || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="monthly_rental_income">Rental Income</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.monthly_rental_income || 0}">${fmtpresent(forecastData.monthly_rental_income || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="income_dependency">Income Dependency</div><div class="kpi-value"><span class="num-fmtint" data-value="${forecastData.certificate_income_ratio || 0}">${fmtInt(forecastData.certificate_income_ratio || 0)}</span>%</div></div>
                <div>
                    <div class="kpi-label" data-i18n="monthly_expenses">Monthly Expenses</div>
                    <div class="kpi-value num-fmtpresent" data-value="${forecastData.avg_monthly_expenses || 0}">
                        ${fmtpresent(forecastData.avg_monthly_expenses || 0)}
                    </div>
                </div>
                <div>
                    <div class="kpi-label" data-i18n="cash_coverage">Cash Coverage</div>
                    <div class="kpi-value">
                        <span class="num-fmt" data-value="${forecastData.cash_coverage_months || 0}">${fmt(forecastData.cash_coverage_months || 0)}</span>
                        <span data-i18n="months">months</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="certificate_forecast">Certificate Forecast</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-top:20px;">
                <div><div class="kpi-label" data-i18n="next_30_days">Next 30 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.forecast_30 || 0}">${fmtpresent(forecastData.forecast_30 || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="next_90_days">Next 90 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.forecast_90 || 0}">${fmtpresent(forecastData.forecast_90 || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="next_180_days">Next 180 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.forecast_180 || 0}">${fmtpresent(forecastData.forecast_180 || 0)}</div></div>
            </div>
        </div>

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="future_cash_position">Future Cash Position</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-top:20px;">
                <div><div class="kpi-label" data-i18n="current_cash">Current Cash</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.cash_balance || 0}">${fmtpresent(forecastData.cash_balance || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="cash_after_30_days">Cash After 30 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.future_cash_30 || 0}">${fmtpresent(forecastData.future_cash_30 || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="cash_after_90_days">Cash After 90 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.future_cash_90 || 0}">${fmtpresent(forecastData.future_cash_90 || 0)}</div></div>
                <div><div class="kpi-label" data-i18n="cash_after_180_days">Cash After 180 Days</div><div class="kpi-value num-fmtpresent" data-value="${forecastData.future_cash_180 || 0}">${fmtpresent(forecastData.future_cash_180 || 0)}</div></div>
            </div>
        </div>

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="investment_recommendations">Investment Recommendations</div>
            <div style="margin-top:15px">
                ${investmentDetails.map((item) => {
                    const itemKey = item.key;
                    const itemParams = item.params || {};
                    const resolvedText = resolveI18nTemplate(itemKey, itemKey, itemParams);
                    const reasonText = item.reason_key
                        ? resolveI18nTemplate(item.reason_key, item.reason_key, item.reason_params || {})
                        : '';
                    const itemParamsEncoded = encodeI18nParams(itemParams);
                    const reasonParamsEncoded = encodeI18nParams(item.reason_params || {});

                    return `<div style="padding:10px; margin-bottom:8px; border-radius:8px; background:var(--bg-secondary); border:1px solid var(--border-color);">
                        <div data-i18n-key="${itemKey}" data-i18n-params="${itemParamsEncoded}">${resolvedText}</div>
                        ${reasonText ? `<div data-i18n-key="${item.reason_key}" data-i18n-params="${reasonParamsEncoded}" style="margin-top:6px;color:var(--text-muted);font-size:12px">${reasonText}</div>` : ''}
                    </div>`;
                }).join('')}
            </div>
        </div>

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="recommended_action">Recommended Action</div>
            ${actionReasonText ? `<div data-i18n-key="${forecastData.action_plan.reason_key}" data-i18n-params="${encodeI18nParams(forecastData.action_plan.reason_params || {})}" style="margin-top:12px;color:var(--text-muted);font-size:13px">${actionReasonText}</div>` : ''}
            <div data-i18n-key="${forecastData.action_plan?.key || ''}"
                 data-gold-amount="${forecastData.action_plan?.gold_amount || 0}"
                 data-cash-amount="${forecastData.action_plan?.cash_amount || 0}"
                 data-certificate-amount="${forecastData.action_plan?.certificate_amount || 0}"
                 style="margin-top:15px;font-weight:600;">
                ${
                    forecastData.action_plan?.key
                        ? (_t[forecastData.action_plan.key] || forecastData.action_plan.key)
                            .replace('{gold_amount}', fmtpresent(forecastData.action_plan.gold_amount || 0))
                            .replace('{cash_amount}', fmtpresent(forecastData.action_plan.cash_amount || 0))
                            .replace('{certificate_amount}', fmtpresent(forecastData.action_plan.certificate_amount || 0))
                        : ''
                }
            </div>
        </div>

        ${forecastData.upcoming?.length ? `
            <div class="kpi-label" data-i18n="upcoming_certificate_maturities" style="margin-top: 24px; font-weight: 600;">${t('upcoming_certificate_maturities', 'Upcoming Certificate Maturities')}</div>
            <div class="table-container" style="margin-top:15px; margin-bottom: 24px;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="bank_name">Bank</th>
                            <th data-i18n="expiry_date">Expiry Date</th>
                            <th data-i18n="days_left">Days Left</th>
                            <th data-i18n="certificate_value">Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${forecastData.upcoming.map((c) => `
                            <tr>
                                <td>${c.bank}</td>
                                <td class="local-date-field" data-expiry="${c.expiry_date}"></td>
                                <td>
                                    <span style="color:${c.days_left <= 30 ? 'var(--accent-red)' : c.days_left <= 90 ? 'orange' : 'var(--text-primary)'}; font-weight:600;">
                                        ${c.days_left}
                                    </span>
                                </td>
                                <td class="num-fmtpresent" data-value="${c.amount}">${fmtpresent(c.amount)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>` : ''
        }

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="asset_allocation">Asset Allocation</div>
            ${renderAllocationBar('type_cash', cashAllocationValue, netWorth)}
            ${renderAllocationBar('bank_certificates', allocationValues.bank_certificates || 0, netWorth)}
            ${renderAllocationBar('type_gold', allocationValues.type_gold || goldValue, netWorth)}
            ${renderAllocationBar('type_real_estate', allocationValues.type_real_estate || 0, netWorth)}
            ${renderAllocationBar('type_vehicles', allocationValues.type_vehicles || 0, netWorth)}
            ${renderAllocationBar('type_other_assets', allocationValues.type_other_assets || 0, netWorth)}
        </div>

        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="financial_recommendations">Financial Recommendations</div>
            <div style="margin-top:15px">
                ${financialDetails.map((item) => {
                    const text = resolveI18nTemplate(item.key, item.key, item.params || {});
                    const reasonText = item.reason_key
                        ? resolveI18nTemplate(item.reason_key, item.reason_key, item.reason_params || {})
                        : '';
                    const itemParamsEncoded = encodeI18nParams(item.params || {});
                    const reasonParamsEncoded = encodeI18nParams(item.reason_params || {});

                    return `
                        <div data-i18n-key="${item.key}" data-i18n-params="${itemParamsEncoded}" style="padding:12px; margin-bottom:10px; background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:10px;">
                            <div>${text}</div>
                            ${reasonText ? `<div data-i18n-key="${item.reason_key}" data-i18n-params="${reasonParamsEncoded}" style="margin-top:6px;color:var(--text-muted);font-size:12px">${reasonText}</div>` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;overflow:visible">
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="balance_title">${titleLabel}</th>
                            <th data-i18n="balance_type">${typeLabel}</th>
                            <th data-i18n="balance_bank">${bankLabel}</th>
                            <th data-i18n="balance_currency">${currencyLabel}</th>
                            <th data-i18n="purity">${t('purity', 'Purity')}</th>
                            <th class="text-end" data-i18n="balance_amount">${amountLabel}</th>
                            <th data-i18n="actions">${actionsLabel}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>
    `;

    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// MODAL MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════

async function showBalanceModal(entryId) {
    let entry = null;
    if (entryId) {
        const res = await fetch('/api/balance/');
        const data = await res.json();
        entry = data.entries.find((e) => e.id === entryId);
    }
    
    const [purityRes] = await Promise.all([
        fetch('/api/settings/gold-purities/'),
    ]);
    const purityData = await purityRes.json();

    const bankOpts = _banks.map((b) => `<option value="${b.id}" ${entry && entry.bank_id === b.id ? 'selected' : ''}>${b.name}</option>`).join('');
    const curOpts = _currencies.map((c) => {
        // Match your existing JSON translation keys
        const key = c.code === 'Gold' ? 'type_gold' : c.code;
        
        // Get the translated name or fallback to the currency name
        let translatedName = _t && _t[key] ? _t[key] : `${c.code} - ${c.name}`;
        
        // Clean up any double emojis if your 'type_gold' translation already includes one (e.g., "🪙 Gold")
        if (c.code === 'Gold' && _t && _t['type_gold']) {
            translatedName = _t['type_gold'].replace(/[\u{1F300}-\u{1F9FF}]/gu, '').trim();
        }

        // Combine the flag/emoji with the translated currency label
        const displayName = `${c.flag || '💵'} ${translatedName}`;

        return `<option value="${c.id}" data-i18n="${key}" ${entry && entry.currency_id === c.id ? 'selected' : ''}>${displayName}</option>`;
    }).join('');

    const typeOpts = `
        <option value="cash" data-i18n="type_cash" ${entry && entry.balance_type === 'cash' ? 'selected' : ''}>${t('type_cash', '💵 Cash')}</option>
        <option value="bank" data-i18n="type_bank" ${entry && entry.balance_type === 'bank' ? 'selected' : ''}>${t('type_bank', '🏦 Bank Account')}</option>
        <option value="gold" data-i18n="type_gold" ${entry && entry.balance_type === 'gold' ? 'selected' : ''}>${t('type_gold', '🪙 Gold')}</option>
        <option value="certificate" data-i18n="type_certificate" ${entry && entry.balance_type === 'certificate' ? 'selected' : ''}>${t('type_certificate', '📜 Certificate')}</option>
    `;

    const titleText = entry ? t('title_edit_balance', 'Edit Balance Entry') : t('title_add_balance', 'Add Balance Entry');
    const balanceTitleLabel = t('balance_title', 'Title');
    const balanceTypeLabel = t('balance_type', 'Balance Type');
    const balanceBankLabel = t('balance_bank', 'Bank');
    const balanceCurrencyLabel = t('balance_currency', 'Currency');
    const balanceAmountLabel = t('balance_amount', 'Amount');
    const notesLabel = t('notes', 'Notes');
    const purityLabel = t('purity', 'Purity');
    const selectTypeText = t('select_type', '— Select Type —');
    const noneOptionText = t('none_option', '— None —');
    const cancelText = t('btn_cancel', 'Cancel');
    const saveText = t('btn_save', 'Save');

    const purityOpts = (purityData.items || [])
        .filter(p => p.is_active)
        .map((p) => `<option value="${p.key}" ${entry && String(entry.purity || '').toLowerCase() === String(p.key || '').toLowerCase() ? 'selected' : ''}>${p.label || p.key}</option>`)
        .join('');

    const html = `
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${entry ? 'title_edit_balance' : 'title_add_balance'}">
                ${titleText}
            </h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-12"><label data-i18n="balance_title">${balanceTitleLabel}</label><input type="text" class="form-control" id="bTitle" value="${entry ? entry.title : ''}"></div>
                <div class="col-12"><label data-i18n="balance_type">${balanceTypeLabel}</label><select class="form-select" id="bbalance_type"><option value="" data-i18n="select_type">${selectTypeText}</option>${typeOpts}</select></div>
                <div class="col-6"><label data-i18n="balance_bank">${balanceBankLabel}</label><select class="form-select" id="bBank"><option value="" data-i18n="none_option">${noneOptionText}</option>${bankOpts}</select></div>
                <div class="col-3"><label data-i18n="balance_currency">${balanceCurrencyLabel}</label><select class="form-select" id="bCurrency">${curOpts}</select></div>
                <div class="col-3"><label data-i18n="balance_amount">${balanceAmountLabel}</label><input type="number" step="0.01" class="form-control" id="bAmount" value="${entry ? entry.amount : ''}"></div>
                <div class="col-4" id="bPurityWrap"><label data-i18n="purity">${purityLabel}</label><select class="form-select" id="bPurity"><option value="">--</option>${purityOpts}</select></div>
                <div class="col-12"><label data-i18n="notes">${notesLabel}</label><input type="text" class="form-control" id="bNotes" value="${entry ? entry.notes : ''}"></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${cancelText}</button>
            <button class="btn-primary-custom" onclick="saveBalanceEntry(${entryId})" data-i18n="btn_save">${saveText}</button>
        </div>
    `;

    showModal(html);

    const typeEl = document.getElementById('bbalance_type');
    const purityWrap = document.getElementById('bPurityWrap');
    const currencyEl = document.getElementById('bCurrency');

    function toggleGoldFields() {
        const isGold = typeEl && typeEl.value === 'gold';
        if (purityWrap) purityWrap.style.display = isGold ? '' : 'none';

        if (isGold && currencyEl) {
            const goldOption = Array.from(currencyEl.options).find(opt => (opt.textContent || '').toLowerCase().includes('gold'));
            if (goldOption) currencyEl.value = goldOption.value;
        }
    }

    if (typeEl) typeEl.addEventListener('change', toggleGoldFields);
    toggleGoldFields();

    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// SAVE & DELETE
// ════════════════════════════════════════════════════════════════════════════

async function saveBalanceEntry(entryId) {
    const bankVal = document.getElementById('bBank').value;
    const typeVal = document.getElementById('bbalance_type').value;

    const body = {
        title: document.getElementById('bTitle').value,
        balance_type: typeVal || null,
        bank_id: bankVal ? parseInt(bankVal) : null,
        currency_id: parseInt(document.getElementById('bCurrency').value) || 1,
        purity: (typeVal === 'gold' ? (document.getElementById('bPurity')?.value || '') : ''),
        amount: parseFloat(document.getElementById('bAmount').value) || 0,
        notes: document.getElementById('bNotes').value,
    };

    const url = entryId ? `/api/balance/${entryId}/` : '/api/balance/';
    const method = entryId ? 'PUT' : 'POST';
    const res = await fetch(url, { 
        method, 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(body) 
    });

    if (res.ok) {
        closeModal();
        showToast(t('balance_entry_saved', 'Balance entry saved ✓'), 'success');
        renderBalance();
    } else {
        showToast(t('error_saving_entry', 'Error saving entry'), 'error');
    }
}

async function deleteBalanceEntry(entryId) {
    if (!confirm(t('confirm_delete_entry', 'Delete this entry?'))) return;
    const res = await fetch(`/api/balance/${entryId}/`, { method: 'DELETE' });
    if (res.ok) {
        showToast(t('entry_deleted', 'Entry deleted'), 'success');
        renderBalance();
    }
}

// ════════════════════════════════════════════════════════════════════════════
// ALLOCATION BAR HELPER
// ════════════════════════════════════════════════════════════════════════════

function renderAllocationBar(labelKey, value, total) {
    const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
    
    // Normalize key to lowercase for insensitive lookup
    const lookupKey = labelKey.toLowerCase();
    let finalKey = labelKey;
    let translatedText = t(labelKey, labelKey); // Default fallback

    // Find the actual case-sensitive key used inside the JSON translation dictionary
    if (_t) {
        const matchedKey = Object.keys(_t).find(k => k.toLowerCase() === lookupKey);
        if (matchedKey) {
            finalKey = matchedKey;
            translatedText = _t[matchedKey];
        }
    }

    return `
        <div style="margin-top:14px">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;">
                <span data-i18n="${finalKey}">${translatedText}</span>
                <span>${pct}%</span>
            </div>
            <div style="height:12px;background:var(--bg-tertiary);border-radius:999px;overflow:hidden;">
                <div style="width:${pct}%;height:100%;background:var(--accent-primary);"></div>
            </div>
        </div>
    `;
}