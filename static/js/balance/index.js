'use strict';

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

    const actionReasonText = forecastData.action_plan?.reason_text
        ? (forecastData.action_plan?.reason_key
            ? resolveI18nTemplate(
                forecastData.action_plan.reason_key,
                forecastData.action_plan.reason_text,
                forecastData.action_plan.reason_params || {},
            )
            : forecastData.action_plan.reason_text)
        : (forecastData.action_plan?.reason_key
            ? resolveI18nTemplate(
                forecastData.action_plan.reason_key,
                forecastData.action_plan.reason_key,
                forecastData.action_plan.reason_params || {},
            )
            : '');

    const goldDetail = investmentDetails.find((item) => {
        const key = String(item.key || '').toLowerCase();
        return key.includes('gold');
    }) || null;

    const getRecommendationText = (item) => {
        if (!item) return '';
        if (item.key) {
            return resolveI18nTemplate(item.key, item.text || item.key, item.params || {});
        }
        return item.text || '';
    };

    const getReasonText = (item) => {
        if (!item) return '';
        if (item.reason_key) {
            return resolveI18nTemplate(item.reason_key, item.reason_text || item.reason_key, item.reason_params || {});
        }
        return item.reason_text || '';
    };

    const goldRecommendationText = goldDetail
        ? getRecommendationText(goldDetail)
        : '';
    const goldReasonText = goldDetail
        ? getReasonText(goldDetail)
        : '';

    const inferredTrend = (() => {
        const t90 = Number(forecastData.gold_trend_90 || 0);
        const gap = Number(forecastData.gold_ma_gap_pct || 0);
        const v = Math.abs(Number(forecastData.gold_signal || 0));
        if (v >= 3 && Number(forecastData.gold_trend_7 || 0) >= 0 && Number(forecastData.gold_trend_30 || 0) >= 0 && t90 >= 0 && gap >= 0) {
            if (v >= 8) return 'Strong Uptrend';
            return 'Moderate Uptrend';
        }
        if (v >= 3 && Number(forecastData.gold_trend_7 || 0) <= 0 && Number(forecastData.gold_trend_30 || 0) <= 0 && t90 <= 0 && gap <= 0) {
            if (v >= 8) return 'Strong Downtrend';
            return 'Moderate Downtrend';
        }
        if (v < 3 && Math.abs(Number(forecastData.gold_trend_30 || 0)) < 4 && Math.abs(Number(forecastData.gold_trend_90 || 0)) < 8) {
            return 'Sideways';
        }
        if (Math.abs(Number(forecastData.gold_trend_7 || 0)) > 3 && Math.abs(Number(forecastData.gold_trend_30 || 0)) < 3) {
            return 'High Volatility';
        }
        if (v >= 8 && t90 > 0 && gap > 0) return 'Strong Uptrend';
        if (v >= 3 && t90 > 0 && gap >= 0) return 'Moderate Uptrend';
        if (v >= 8 && t90 < 0 && gap < 0) return 'Strong Downtrend';
        if (v >= 3 && t90 < 0 && gap <= 0) return 'Moderate Downtrend';
        return 'Sideways';
    })();

    const trendLabelKey = (() => {
        const trend = String(inferredTrend || '').toLowerCase();
        if (trend.includes('strong uptrend')) return 'trend_strong_uptrend';
        if (trend.includes('moderate uptrend')) return 'trend_moderate_uptrend';
        if (trend.includes('strong downtrend')) return 'trend_strong_downtrend';
        if (trend.includes('moderate downtrend')) return 'trend_moderate_downtrend';
        if (trend.includes('high volatility')) return 'trend_high_volatility';
        return 'trend_sideways';
    })();
    const localizedTrendLabel = t(trendLabelKey, inferredTrend || 'Sideways');

    const trendMeta = (() => {
        const trend = inferredTrend;
        if (/strong\s*up|moderate\s*up/i.test(trend)) return { icon: '📈', cls: 'fi-positive' };
        if (/strong\s*down|moderate\s*down/i.test(trend)) return { icon: '📉', cls: 'fi-negative' };
        if (/volatility/i.test(trend)) return { icon: '⚠️', cls: 'fi-warning' };
        return { icon: '➖', cls: 'fi-neutral' };
    })();

    const netMonthlySurplus = Number(forecastData.total_monthly_income || 0) - Number(forecastData.avg_monthly_expenses || 0);

    const diversificationLabel = (() => {
        const ratios = [
            Number(forecastData.cash_ratio || 0),
            Number(forecastData.certificate_ratio || 0),
            Number(forecastData.gold_ratio || 0),
            Number(forecastData.fixed_assets_ratio || 0),
        ];
        const maxWeight = Math.max(...ratios);
        if (maxWeight <= 45) return t('diversification_balanced', 'Balanced');
        if (maxWeight <= 60) return t('diversification_moderate_concentration', 'Moderate Concentration');
        return t('diversification_high_concentration', 'High Concentration');
    })();

    const priorityRank = { high: 3, medium: 2, low: 1 };
    const worstPriority = (financialDetails || []).reduce((acc, item) => {
        const p = priorityRank[String(item.priority || '').toLowerCase()] || 0;
        return Math.max(acc, p);
    }, 0);
    const hasBalancedKey = (financialDetails || []).some((item) => String(item.key || '') === 'recommend_asset_allocation_balanced');
    const financialHealth = (() => {
        if (worstPriority >= 3) return { label: t('status_critical', 'Critical'), icon: '🔴', cls: 'fi-negative' };
        if (worstPriority === 2) return { label: t('status_warning', 'Warning'), icon: '🟠', cls: 'fi-warning' };
        if (hasBalancedKey && (forecastData.cash_coverage_months || 0) >= 6 && netMonthlySurplus >= 0) {
            return { label: t('status_excellent', 'Excellent'), icon: '🟢', cls: 'fi-positive' };
        }
        return { label: t('status_good', 'Good'), icon: '🟦', cls: 'fi-neutral' };
    })();

    const labelGoldMarketAnalysis = t('gold_market_analysis', 'Gold Market Analysis');
    const labelTrend = t('trend_label', 'Trend');
    const labelSevenDayChange = t('seven_day_change', '7-Day Change');
    const labelThirtyDayChange = t('thirty_day_change', '30-Day Change');
    const labelNinetyDayChange = t('ninety_day_change', '90-Day Change');
    const labelMa7 = t('ma_short_label', 'MA(7)');
    const labelMa30 = t('ma_long_label', 'MA(30)');
    const labelMaGap = t('ma_gap_label', 'MA Gap');
    const labelCurrentAllocation = t('current_allocation', 'Current Allocation');
    const labelRecommendation = t('recommendation_label', 'Recommendation');
    const labelSuggestedAllocation = t('suggested_allocation', 'Suggested Allocation');
    const labelFinancialHealth = t('financial_health_label', 'Financial Health');
    const labelFinancialHealthOverview = t('financial_health_overview', 'Financial Health Overview');
    const labelNetWorth = t('net_worth', 'Net Worth');
    const labelLiquidityCoverage = t('liquidity_coverage', 'Liquidity Coverage');
    const labelMonthlySurplus = t('monthly_surplus', 'Monthly Surplus');
    const labelDiversification = t('diversification_label', 'Diversification');
    const labelCash = t('label_cash', 'Cash');
    const labelCertificates = t('label_certificates', 'Certificates');
    const labelGold = t('label_gold', 'Gold');
    const labelFixedAssets = t('label_fixed_assets', 'Fixed Assets');
    const labelMonths = t('months', 'months');
    const labelEgp = t('EGP', 'EGP');

    const topFinancialItem = [...(financialDetails || [])]
        .sort((a, b) => (priorityRank[String(b.priority || '').toLowerCase()] || 0) - (priorityRank[String(a.priority || '').toLowerCase()] || 0))[0] || null;
    const financialParagraph = topFinancialItem
        ? getRecommendationText(topFinancialItem)
        : '';
    const financialReason = topFinancialItem
        ? getReasonText(topFinancialItem)
        : '';

    const suggestedAllocations = [
        { icon: '🥇', label: t('gold_value', 'Gold'), value: Number(forecastData.action_plan?.gold_amount || 0) },
        { icon: '🏦', label: t('certificate_investments', 'Certificates'), value: Number(forecastData.action_plan?.certificate_amount || 0) },
        { icon: '💰', label: t('liquid_cash', 'Cash'), value: Number(forecastData.action_plan?.cash_amount || 0) },
    ].filter((row) => row.value > 0 || forecastData.action_plan?.key === 'action_gold_cash');

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

        <div class="kpi-card mb-4 fi-forecast-card">
            <div class="kpi-label" data-i18n="certificate_forecast">Certificate Forecast</div>
            <div class="fi-amount-grid fi-amount-grid-3">
                <div class="fi-amount-tile ${Number(forecastData.forecast_30 || 0) > 0 ? 'fi-up' : ''}">
                    <div class="fi-amount-caption" data-i18n="next_30_days">Next 30 Days</div>
                    <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.forecast_30 || 0}">${fmtpresent(forecastData.forecast_30 || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-amount-tile ${Number(forecastData.forecast_90 || 0) > 0 ? 'fi-up' : ''}">
                    <div class="fi-amount-caption" data-i18n="next_90_days">Next 90 Days</div>
                    <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.forecast_90 || 0}">${fmtpresent(forecastData.forecast_90 || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-amount-tile ${Number(forecastData.forecast_180 || 0) > 0 ? 'fi-up' : ''}">
                    <div class="fi-amount-caption" data-i18n="next_180_days">Next 180 Days</div>
                    <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.forecast_180 || 0}">${fmtpresent(forecastData.forecast_180 || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
            </div>
        </div>

        <div class="kpi-card mb-4 fi-cash-position-card">
            <div class="kpi-label" data-i18n="future_cash_position">Future Cash Position</div>
            <div class="fi-amount-grid fi-amount-grid-4">
                <div class="fi-amount-tile">
                    <div class="fi-amount-caption" data-i18n="current_cash">Current Cash</div>
                    <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.cash_balance || 0}">${fmtpresent(forecastData.cash_balance || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-amount-tile">
                    <div class="fi-amount-caption" data-i18n="cash_after_30_days">Cash After 30 Days</div>
                    <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.future_cash_30 || 0}">${fmtpresent(forecastData.future_cash_30 || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-amount-tile">
                    <div class="fi-amount-caption" data-i18n="cash_after_90_days">Cash After 90 Days</div>
                    <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.future_cash_90 || 0}">${fmtpresent(forecastData.future_cash_90 || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
                <div class="fi-amount-tile">
                    <div class="fi-amount-caption" data-i18n="cash_after_180_days">Cash After 180 Days</div>
                    <div class="fi-amount-value num-fmtpresent" data-value="${forecastData.future_cash_180 || 0}">${fmtpresent(forecastData.future_cash_180 || 0)}</div>
                    <div class="fi-metric-sub" data-i18n="EGP">EGP</div>
                </div>
            </div>
        </div>

        <div class="kpi-card mb-4 fi-boardroom-card fi-investment-card">
            <div class="kpi-label" data-i18n="investment_recommendations">Investment Recommendations</div>
            <div class="fi-emphasis-band fi-emphasis-gold"><span class="fi-band-icon">📊</span><span>${labelGoldMarketAnalysis}</span></div>
            <div class="fi-section-title">${labelGoldMarketAnalysis}</div>
            <div class="fi-metric-grid">
                <div class="fi-metric-row"><span class="fi-metric-label">${labelTrend}</span><span class="fi-trend-pill ${trendMeta.cls}">${trendMeta.icon} ${localizedTrendLabel}</span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelSevenDayChange}</span><span class="fi-metric-value num-fmt" data-value="${forecastData.gold_trend_7 || 0}">${fmt(forecastData.gold_trend_7 || 0)}%</span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelThirtyDayChange}</span><span class="fi-metric-value num-fmt" data-value="${forecastData.gold_trend_30 || 0}">${fmt(forecastData.gold_trend_30 || 0)}%</span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelNinetyDayChange}</span><span class="fi-metric-value num-fmt" data-value="${forecastData.gold_trend_90 || 0}">${fmt(forecastData.gold_trend_90 || 0)}%</span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelMa7}</span><span class="fi-metric-value num-fmt" data-value="${forecastData.gold_ma_short || 0}">${fmt(forecastData.gold_ma_short || 0)}</span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelMa30}</span><span class="fi-metric-value num-fmt" data-value="${forecastData.gold_ma_long || 0}">${fmt(forecastData.gold_ma_long || 0)}</span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelMaGap}</span><span class="fi-metric-value num-fmt" data-value="${forecastData.gold_ma_gap_pct || 0}">${fmt(forecastData.gold_ma_gap_pct || 0)}%</span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelCurrentAllocation}</span><span class="fi-metric-value fi-accent num-fmt" data-value="${forecastData.gold_ratio || 0}">${fmt(forecastData.gold_ratio || 0)}%</span></div>
            </div>
            <div class="fi-section-title">${labelRecommendation}</div>
            <div class="fi-info-box">${goldRecommendationText || t('recommend_gold_neutral', 'Keep current gold allocation and rebalance gradually as trends evolve.')}</div>
            <div style="margin-top:15px">
                ${investmentDetails.filter((item) => String(item.key || '') !== 'recommend_gold_dynamic').map((item) => {
                    const itemKey = item.key;
                    const itemParams = item.params || {};
                    const resolvedText = getRecommendationText(item);
                    const itemParamsEncoded = encodeI18nParams(itemParams);

                    return `<div class="fi-note-card">
                        <div ${item.key ? `data-i18n-key="${itemKey}" data-i18n-params="${itemParamsEncoded}"` : ''}>${resolvedText}</div>
                    </div>`;
                }).join('')}
            </div>
        </div>

        <div class="kpi-card mb-4 fi-boardroom-card fi-action-card">
            <div class="kpi-label" data-i18n="recommended_action">Recommended Action</div>
            <div class="row g-3 fi-card-grid">
                <div class="col-12 col-lg-6">
                    <div class="fi-sub-card h-100">
                        <div class="fi-emphasis-band fi-emphasis-neutral"><span class="fi-band-icon">🧭</span><span>${labelCurrentAllocation}</span></div>
                        <div class="fi-section-title">${labelCurrentAllocation}</div>
                        <div class="fi-metric-grid">
                            <div class="fi-metric-row"><span class="fi-metric-label fi-label-with-icon"><span>💰</span><span>${labelCash}</span></span><span class="fi-metric-value num-fmt" data-value="${forecastData.cash_ratio || 0}">${fmt(forecastData.cash_ratio || 0)}%</span></div>
                            <div class="fi-metric-row"><span class="fi-metric-label fi-label-with-icon"><span>🏦</span><span>${labelCertificates}</span></span><span class="fi-metric-value num-fmt" data-value="${forecastData.certificate_ratio || 0}">${fmt(forecastData.certificate_ratio || 0)}%</span></div>
                            <div class="fi-metric-row"><span class="fi-metric-label fi-label-with-icon"><span>🥇</span><span>${labelGold}</span></span><span class="fi-metric-value num-fmt" data-value="${forecastData.gold_ratio || 0}">${fmt(forecastData.gold_ratio || 0)}%</span></div>
                            <div class="fi-metric-row"><span class="fi-metric-label fi-label-with-icon"><span>🏠</span><span>${labelFixedAssets}</span></span><span class="fi-metric-value num-fmt" data-value="${forecastData.fixed_assets_ratio || 0}">${fmt(forecastData.fixed_assets_ratio || 0)}%</span></div>
                        </div>
                    </div>
                </div>
                <div class="col-12 col-lg-6">
                    <div class="fi-sub-card h-100">
                        <div class="fi-emphasis-band fi-emphasis-primary"><span class="fi-band-icon">🎯</span><span>${labelSuggestedAllocation}</span></div>
                        <div class="fi-section-title">${labelSuggestedAllocation}</div>
                        <div class="fi-highlight-stack">
                            ${suggestedAllocations.map((row) => `
                                <div class="fi-highlight-row">
                                    <div class="fi-metric-label fi-label-with-icon"><span>${row.icon}</span><span>${row.label}</span></div>
                                    <div class="fi-metric-value fi-accent fi-value-inline">
                                        <span class="num-fmtpresent" data-value="${row.value}">${fmtpresent(row.value)}</span>
                                        <span class="fi-value-unit" data-i18n="EGP">${labelEgp}</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
            ${actionReasonText ? `<div ${forecastData.action_plan?.reason_key ? `data-i18n-key="${forecastData.action_plan.reason_key}" data-i18n-params="${encodeI18nParams(forecastData.action_plan.reason_params || {})}"` : ''} class="fi-paragraph" style="margin-top:16px;">${actionReasonText}</div>` : ''}
            <div data-i18n-key="${forecastData.action_plan?.key || ''}"
                 data-gold-amount="${forecastData.action_plan?.gold_amount || 0}"
                 data-cash-amount="${forecastData.action_plan?.cash_amount || 0}"
                 data-certificate-amount="${forecastData.action_plan?.certificate_amount || 0}"
                 class="fi-allocation-sentence"
                 style="margin-top:10px;">
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

        <div class="kpi-card mb-4 fi-boardroom-card fi-financial-card">
            <div class="kpi-label" data-i18n="financial_recommendations">Financial Recommendations</div>
            <div class="fi-emphasis-band fi-emphasis-health"><span class="fi-band-icon">📌</span><span>${labelFinancialHealthOverview}</span></div>
            <div class="fi-section-title">${labelFinancialHealth}</div>
            <div class="fi-badge-row"><span class="fi-status-badge ${financialHealth.cls}">${financialHealth.icon} ${financialHealth.label}</span></div>
            <div class="fi-metric-grid">
                <div class="fi-metric-row"><span class="fi-metric-label">${labelNetWorth}</span><span class="fi-metric-value fi-accent fi-value-inline"><span class="num-fmtpresent" data-value="${netWorth}">${fmtpresent(netWorth)}</span><span class="fi-value-unit" data-i18n="EGP">${labelEgp}</span></span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelLiquidityCoverage}</span><span class="fi-metric-value fi-value-inline"><span class="num-fmt" data-value="${forecastData.cash_coverage_months || 0}">${fmt(forecastData.cash_coverage_months || 0)}</span><span class="fi-value-unit" data-i18n="months">${labelMonths}</span></span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelMonthlySurplus}</span><span class="fi-metric-value ${netMonthlySurplus >= 0 ? 'fi-positive' : 'fi-negative'} fi-value-inline"><span class="num-fmtpresent" data-value="${netMonthlySurplus}">${fmtpresent(netMonthlySurplus)}</span><span class="fi-value-unit" data-i18n="EGP">${labelEgp}</span></span></div>
                <div class="fi-metric-row"><span class="fi-metric-label">${labelDiversification}</span><span class="fi-metric-value">${diversificationLabel}</span></div>
            </div>
            <div class="fi-section-title">${labelRecommendation}</div>
            <div class="fi-info-box">${financialParagraph || t('recommend_asset_allocation_balanced', 'Financial position is balanced with healthy liquidity and diversified assets.')}</div>
            <div class="fi-list-compact" style="margin-top:12px">
                ${financialDetails.slice(1, 4).map((item) => {
                    const text = getRecommendationText(item);
                    const itemParamsEncoded = encodeI18nParams(item.params || {});
                    return `<div ${item.key ? `data-i18n-key="${item.key}" data-i18n-params="${itemParamsEncoded}"` : ''} class="fi-note-card">${text}</div>`;
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

    // Re-layout executive cards to match the target board layout without changing any calculations.
    const safeInsert = (parent, child, beforeNode = null) => {
        if (!parent || !child) return;
        if (parent === child || child.contains(parent)) return;
        if (beforeNode && beforeNode.parentNode === parent) {
            parent.insertBefore(child, beforeNode);
        } else {
            parent.appendChild(child);
        }
    };

    const financialIntelligenceCard = mc.querySelector('[data-i18n="financial_intelligence"]')?.closest('.kpi-card');
    const financialCard = mc.querySelector('.fi-financial-card');
    const actionCard = mc.querySelector('.fi-action-card');
    const investmentCard = mc.querySelector('.fi-investment-card');

    if (financialIntelligenceCard && financialCard && actionCard && investmentCard) {
        const topGridParent = financialIntelligenceCard.parentNode;
        const topGridAnchor = financialIntelligenceCard;
        const topGrid = document.createElement('div');
        topGrid.className = 'row g-3 mb-4 fi-top-grid';

        [financialCard, actionCard, investmentCard].forEach((card) => {
            const col = document.createElement('div');
            col.className = 'col-12 col-xl-4';
            card.classList.remove('mb-4');
            card.classList.add('h-100');
            col.appendChild(card);
            topGrid.appendChild(col);
        });

        safeInsert(topGridParent, topGrid, topGridAnchor);
    }

    const certificateForecastCard = mc.querySelector('[data-i18n="certificate_forecast"]')?.closest('.kpi-card');
    const futureCashCard = mc.querySelector('[data-i18n="future_cash_position"]')?.closest('.kpi-card');
    if (certificateForecastCard && futureCashCard) {
        const cashGridParent = certificateForecastCard.parentNode;
        const cashGridAnchor = futureCashCard.nextSibling;
        const cashGrid = document.createElement('div');
        cashGrid.className = 'row g-3 mb-4 fi-cash-grid';

        [certificateForecastCard, futureCashCard].forEach((card) => {
            const col = document.createElement('div');
            col.className = 'col-12 col-xl-6';
            card.classList.remove('mb-4');
            card.classList.add('h-100');
            col.appendChild(card);
            cashGrid.appendChild(col);
        });

        safeInsert(cashGridParent, cashGrid, cashGridAnchor);
    }

    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// MODAL MANAGEMENT
// ════════════════════════════════════════════════════════════════════════════