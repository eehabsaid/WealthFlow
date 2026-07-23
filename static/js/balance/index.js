'use strict';

// balance/index.js — Page coordinator
// Fetches all APIs once on load, builds the tab shell, delegates rendering
// to the individual tab files. Tab switching never re-calls any API.
// ════════════════════════════════════════════════════════════════════════════


async function renderBalance() {
    const mc = document.getElementById('main-content');
    if (!mc) return;
    mc.innerHTML = '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

    // ── 1. Fetch all data once ───────────────────────────────────────────────
    const [bRes, bankRes, currRes, forecastRes, transfersRes] = await Promise.all([
        fetch('/api/balance/'),
        fetch('/api/banks/'),
        fetch('/api/currencies/'),
        fetch('/api/certificate-forecast/'),
        fetch('/api/balance-transfers/'),
    ]);
    const bData        = await bRes.json();
    const bankData     = await bankRes.json();
    const currData     = await currRes.json();
    const forecastData = await forecastRes.json();
    const transfersData = await transfersRes.json();

    // ── 2. Store module-level state ──────────────────────────────────────────
    _balanceEntries = bData.entries;
    window.entries  = _balanceEntries;     // backward-compat
    _banks          = bankData.banks;      // global app var
    _currencies     = currData.currencies || []; // global app var

    // ── 3. Pre-compute derived values (done once, passed to all tab renderers)
    const summary          = bData.summary || {};
    const totals           = summary.totals_by_currency || {};
    const totalEGP         = totals.EGP || 0;
    const cashEGP          = summary.liquid_egp_cash ?? summary.cash_egp ?? 0;
    const usdAmount        = totals.USD  || 0;
    const eurAmount        = totals.EUR  || 0;
    const sarAmount        = totals.SAR  || 0;
    const usdRate          = summary.usd_rate   || 0;
    const eurRate          = summary.eur_rate   || 0;
    const sarRate          = summary.sar_rate   || 0;
    const goldValue        = summary.gold_value || 0;
    const grandTotal       = summary.grand_total || 0;
    const netWorth         = summary.net_worth  || grandTotal || 0;
    const allocationValues = summary.allocation_values || {};
    const cashAllocationValue = (allocationValues.type_cash || 0) + (allocationValues.type_bank || 0);

    // ── 4. i18n helpers ──────────────────────────────────────────────────────
    const resolveI18nTemplate = (key, fallback, params = {}) => {
        let text = t(key, fallback || key);
        Object.entries(params || {}).forEach(([k, raw]) => {
            let val = raw;
            const n = Number(raw);
            if (Number.isFinite(n)) {
                if (/days/i.test(k))                         val = fmtInt(n);
                else if (/(ratio|trend|signal|gap|coverage|pct)/i.test(k)) val = fmt(n);
                else                                          val = fmtpresent(n);
            }
            text = text.split(`{${k}}`).join(String(val));
        });
        return text;
    };
    const encodeI18nParams = (params = {}) => encodeURIComponent(JSON.stringify(params || {}));
    const getRecommendationText = (item) => {
        if (!item) return '';
        return item.key ? resolveI18nTemplate(item.key, item.text || item.key, item.params || {}) : (item.text || '');
    };
    const getReasonText = (item) => {
        if (!item) return '';
        return item.reason_key ? resolveI18nTemplate(item.reason_key, item.reason_text || item.reason_key, item.reason_params || {}) : (item.reason_text || '');
    };

    // ── 5. Recommendation data ───────────────────────────────────────────────
    const investmentDetails = (forecastData.investment_recommendation_details || []).length
        ? (forecastData.investment_recommendation_details || [])
        : (forecastData.investment_recommendations || []).map((r) => {
            const key    = typeof r === 'object' && r.key ? r.key : r;
            const params = typeof r === 'object' && r.days_left != null ? { days_left: r.days_left } : {};
            return { key, params, reason_key: '', reason_params: {} };
        });

    const financialDetails = (forecastData.financial_recommendation_details || []).length
        ? (forecastData.financial_recommendation_details || [])
        : (forecastData.financial_recommendations || []).map((key) => ({ key, params: {}, reason_key: '', reason_params: {} }));

    const actionReasonText = forecastData.action_plan?.reason_text
        ? (forecastData.action_plan?.reason_key
            ? resolveI18nTemplate(forecastData.action_plan.reason_key, forecastData.action_plan.reason_text, forecastData.action_plan.reason_params || {})
            : forecastData.action_plan.reason_text)
        : (forecastData.action_plan?.reason_key
            ? resolveI18nTemplate(forecastData.action_plan.reason_key, forecastData.action_plan.reason_key, forecastData.action_plan.reason_params || {})
            : '');

    const goldDetail             = investmentDetails.find((i) => String(i.key || '').toLowerCase().includes('gold')) || null;
    const goldRecommendationText = goldDetail ? getRecommendationText(goldDetail) : '';

    // ── 6. Gold trend ────────────────────────────────────────────────────────
    const inferredTrend = (() => {
        const t90 = Number(forecastData.gold_trend_90 || 0);
        const gap = Number(forecastData.gold_ma_gap_pct || 0);
        const v   = Math.abs(Number(forecastData.gold_signal || 0));
        if (v >= 3 && Number(forecastData.gold_trend_7 || 0) >= 0 && Number(forecastData.gold_trend_30 || 0) >= 0 && t90 >= 0 && gap >= 0)
            return v >= 8 ? 'Strong Uptrend' : 'Moderate Uptrend';
        if (v >= 3 && Number(forecastData.gold_trend_7 || 0) <= 0 && Number(forecastData.gold_trend_30 || 0) <= 0 && t90 <= 0 && gap <= 0)
            return v >= 8 ? 'Strong Downtrend' : 'Moderate Downtrend';
        if (v < 3 && Math.abs(Number(forecastData.gold_trend_30 || 0)) < 4 && Math.abs(t90) < 8)
            return 'Sideways';
        if (Math.abs(Number(forecastData.gold_trend_7 || 0)) > 3 && Math.abs(Number(forecastData.gold_trend_30 || 0)) < 3)
            return 'High Volatility';
        if (v >= 8 && t90 > 0 && gap > 0)  return 'Strong Uptrend';
        if (v >= 3 && t90 > 0 && gap >= 0) return 'Moderate Uptrend';
        if (v >= 8 && t90 < 0 && gap < 0)  return 'Strong Downtrend';
        if (v >= 3 && t90 < 0 && gap <= 0) return 'Moderate Downtrend';
        return 'Sideways';
    })();

    const trendLabelKey = (() => {
        const tr = String(inferredTrend || '').toLowerCase();
        if (tr.includes('strong uptrend'))    return 'trend_strong_uptrend';
        if (tr.includes('moderate uptrend'))  return 'trend_moderate_uptrend';
        if (tr.includes('strong downtrend'))  return 'trend_strong_downtrend';
        if (tr.includes('moderate downtrend')) return 'trend_moderate_downtrend';
        if (tr.includes('high volatility'))   return 'trend_high_volatility';
        return 'trend_sideways';
    })();
    const localizedTrendLabel = t(trendLabelKey, inferredTrend || 'Sideways');
    const trendMeta = (() => {
        const tr = inferredTrend;
        if (/strong\s*up|moderate\s*up/i.test(tr))     return { icon: '📈', cls: 'fi-positive' };
        if (/strong\s*down|moderate\s*down/i.test(tr)) return { icon: '📉', cls: 'fi-negative' };
        if (/volatility/i.test(tr))                    return { icon: '⚠️', cls: 'fi-warning' };
        return { icon: '➖', cls: 'fi-neutral' };
    })();

    // ── 7. Financial health ──────────────────────────────────────────────────
    const netMonthlySurplus = Number(forecastData.total_monthly_income || 0) - Number(forecastData.avg_monthly_expenses || 0);
    const diversificationLabel = (() => {
        const ratios = [forecastData.cash_ratio, forecastData.certificate_ratio, forecastData.gold_ratio, forecastData.fixed_assets_ratio].map(Number);
        const max = Math.max(...ratios);
        if (max <= 45) return t('diversification_balanced', 'Balanced');
        if (max <= 60) return t('diversification_moderate_concentration', 'Moderate Concentration');
        return t('diversification_high_concentration', 'High Concentration');
    })();
    const priorityRank  = { high: 3, medium: 2, low: 1 };
    const worstPriority = (financialDetails || []).reduce((acc, i) =>
        Math.max(acc, priorityRank[String(i.priority || '').toLowerCase()] || 0), 0);
    const hasBalancedKey = (financialDetails || []).some((i) => String(i.key || '') === 'recommend_asset_allocation_balanced');
    const financialHealth = (() => {
        if (worstPriority >= 3) return { label: t('status_critical', 'Critical'), icon: '🔴', cls: 'fi-negative' };
        if (worstPriority === 2) return { label: t('status_warning', 'Warning'), icon: '🟠', cls: 'fi-warning' };
        if (hasBalancedKey && (forecastData.cash_coverage_months || 0) >= 6 && netMonthlySurplus >= 0)
            return { label: t('status_excellent', 'Excellent'), icon: '🟢', cls: 'fi-positive' };
        return { label: t('status_good', 'Good'), icon: '🟦', cls: 'fi-neutral' };
    })();

    const topFinancialItem   = [...(financialDetails || [])].sort((a, b) =>
        (priorityRank[String(b.priority || '').toLowerCase()] || 0) - (priorityRank[String(a.priority || '').toLowerCase()] || 0))[0] || null;
    const financialParagraph = topFinancialItem ? getRecommendationText(topFinancialItem) : '';

    const suggestedAllocations = [
        { icon: '🥇', label: t('gold_value', 'Gold'),         value: Number(forecastData.action_plan?.gold_amount        || 0) },
        { icon: '🏦', label: t('certificate_investments', 'Certificates'), value: Number(forecastData.action_plan?.certificate_amount || 0) },
        { icon: '💰', label: t('liquid_cash', 'Cash'),        value: Number(forecastData.action_plan?.cash_amount        || 0) },
    ].filter((r) => r.value > 0 || forecastData.action_plan?.key === 'action_gold_cash');

    // ── 8. Shared labels (passed once, used by tab renderers) ────────────────
    const labels = {
        labelGoldMarketAnalysis:    t('gold_market_analysis',       'Gold Market Analysis'),
        labelTrend:                 t('trend_label',                'Trend'),
        labelSevenDayChange:        t('seven_day_change',           '7-Day Change'),
        labelThirtyDayChange:       t('thirty_day_change',          '30-Day Change'),
        labelNinetyDayChange:       t('ninety_day_change',          '90-Day Change'),
        labelMa7:                   t('ma_short_label',             'MA(7)'),
        labelMa30:                  t('ma_long_label',              'MA(30)'),
        labelMaGap:                 t('ma_gap_label',               'MA Gap'),
        labelCurrentAllocation:     t('current_allocation',         'Current Allocation'),
        labelRecommendation:        t('recommendation_label',       'Recommendation'),
        labelSuggestedAllocation:   t('suggested_allocation',       'Suggested Allocation'),
        labelFinancialHealth:       t('financial_health_label',     'Financial Health'),
        labelFinancialHealthOverview: t('financial_health_overview','Financial Health Overview'),
        labelNetWorth:              t('net_worth',                  'Net Worth'),
        labelLiquidityCoverage:     t('liquidity_coverage',         'Liquidity Coverage'),
        labelMonthlySurplus:        t('monthly_surplus',            'Monthly Surplus'),
        labelDiversification:       t('diversification_label',      'Diversification'),
        labelCash:                  t('label_cash',                 'Cash'),
        labelCertificates:          t('label_certificates',         'Certificates'),
        labelGold:                  t('label_gold',                 'Gold'),
        labelFixedAssets:           t('label_fixed_assets',         'Fixed Assets'),
        labelMonths:                t('months',                     'months'),
        labelEgp:                   t('EGP',                        'EGP'),
        grandTotalLabel:            t('grand_total',                'Total All Balances (EGP equiv.)'),
        formulaDesc:                t('balance_formula_desc',       '= EGP + (USD x rate) + (EUR x rate) + (SAR x rate) + Sum(Gold amount x (purity sell price + purity cashback))'),
    };

    // ── 9. Single data bundle for all tab renderers ──────────────────────────
    const tabData = {
        // raw API responses
        forecastData, entries: _balanceEntries,
        transfers: transfersData.transfers || [],
        // summary values
        totals, totalEGP, cashEGP, usdAmount, eurAmount, sarAmount,
        usdRate, eurRate, sarRate, goldValue, grandTotal, netWorth,
        allocationValues, cashAllocationValue,
        // recommendation data
        investmentDetails, financialDetails, actionReasonText,
        goldRecommendationText, financialParagraph, suggestedAllocations,
        // helpers (functions)
        getRecommendationText, getReasonText, encodeI18nParams,
        // trend
        trendMeta, localizedTrendLabel,
        // health
        netMonthlySurplus, diversificationLabel, financialHealth,
        // spread labels
        ...labels,
    };

    // ── 10. Resolve active tab ───────────────────────────────────────────────
    const saved       = sessionStorage.getItem(BALANCE_ACTIVE_TAB_KEY) || 'overview';
    const activeTabId = BALANCE_TABS.some((tab) => tab.id === saved) ? saved : 'overview';

    // ── 11. Build tab nav buttons ─────────────────────────────────────────────
    const tabsNav = BALANCE_TABS.map((tab) => `
        <button
          class="wf-tab ${tab.id === activeTabId ? 'active' : ''}"
          id="bal-tab-${tab.id}"
          data-bs-toggle="pill"
          data-bs-target="#bal-pane-${tab.id}"
          type="button"
          role="tab"
          aria-controls="bal-pane-${tab.id}"
          aria-selected="${tab.id === activeTabId ? 'true' : 'false'}"
          data-i18n="${tab.key}"
        ></button>`).join('');

    // ── 12. Build tab pane shells ────────────────────────────────────────────
    const tabPanes = BALANCE_TABS.map((tab) => `
        <div class="tab-pane fade ${tab.id === activeTabId ? 'show active' : ''}"
             id="bal-pane-${tab.id}"
             role="tabpanel"
             aria-labelledby="bal-tab-${tab.id}"
             tabindex="0">
        </div>`).join('');

    const activeTabObj = BALANCE_TABS.find(t => t.id === activeTabId) || BALANCE_TABS[0];
    const activeKey = activeTabObj.key;

    // ── 13. Inject page shell ────────────────────────────────────────────────
    mc.innerHTML = `
        <div class="page-header balance-page-header">
            <div><div class="page-title" data-i18n="${activeKey}">${t(activeKey)}</div></div>
        </div>
        <div class="card border-0 balance-page-card" style="background:var(--bg-primary);border:1px solid var(--border-color);">
            <div class="card-body" style="padding:16px;">
                <div class="wf-tabs-shell">
                    <div class="wf-tabs-row" id="balanceTabs" role="tablist">
                        ${tabsNav}
                    </div>
                </div>
                <div class="tab-content" id="balanceTabsContent" style="padding-top:16px;">
                    ${tabPanes}
                </div>
            </div>
        </div>
    `;

    applyTranslations();

    if (typeof window.initTabsWithMoreMenu === 'function') {
        window.initTabsWithMoreMenu({
            containerId: 'balanceTabs',
            visibleCount: 4,
            moreLabel: typeof t === 'function' ? t('financial_advisor_tab_more', 'More') : 'More',
        });
    }

    // ── 14. Render all tab panes immediately (all data is already in memory) ─
    renderBalanceOverview(tabData);
    renderBalanceAllocation(tabData);
    renderBalanceForecasts(tabData);
    renderBalanceRecommendations(tabData);
    renderBalanceAccounts(tabData);
    if (typeof renderBalanceTransfers === 'function') {
        renderBalanceTransfers(tabData);
    }

    applyTranslations();

    // ── 15. Wire tab events — session storage persistence & Add button ───────
    if (_balanceTabEventsAbortController) {
        _balanceTabEventsAbortController.abort();
    }
    _balanceTabEventsAbortController = new AbortController();
    const signal = _balanceTabEventsAbortController.signal;
    
    const updateAddBtn = (tabId) => {
        const btn = document.getElementById('addEntryBtn');
        if (btn) btn.style.display = tabId === 'accounts' ? 'inline-block' : 'none';
    };
    updateAddBtn(activeTabId);

    const tabsContainer = document.getElementById('balanceTabs');
    if (tabsContainer) {
        tabsContainer.querySelectorAll('[data-bs-toggle="pill"]').forEach((btn) => {
            btn.addEventListener('shown.bs.tab', (e) => {
                const target = e.target;
                if (!(target instanceof HTMLElement)) return;
                const tabId = target.id.replace('bal-tab-', '');
                if (tabId) {
                    sessionStorage.setItem(BALANCE_ACTIVE_TAB_KEY, tabId);
                    updateAddBtn(tabId);
                    const activeTabObj = BALANCE_TABS.find(t => t.id === tabId) || BALANCE_TABS[0];
                    const activeKey = activeTabObj.key;
                    const titleEl = document.querySelector('.balance-page-header .page-title');
                    if (titleEl) {
                        titleEl.setAttribute('data-i18n', activeKey);
                        titleEl.textContent = t(activeKey);
                    }
                }
            }, { signal });
        });
    }
}

// ════════════════════════════════════════════════════════════════════════════
// GLOBAL EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.renderBalance      = renderBalance;
window.showBalanceModal   = showBalanceModal;
window.saveBalanceEntry   = saveBalanceEntry;
window.deleteBalanceEntry = deleteBalanceEntry;