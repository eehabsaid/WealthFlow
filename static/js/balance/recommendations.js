'use strict';

// balance/recommendations.js — Recommendations tab renderer
// Renders: Investment Recommendations + Financial Recommendations + Recommended Action
// Called by index.js with pre-fetched data. Zero API calls here.
// ════════════════════════════════════════════════════════════════════════════

function renderBalanceRecommendations(data) {
    const pane = document.getElementById('bal-pane-recommendations');
    if (!pane) return;

    const {
        forecastData,
        investmentDetails, financialDetails,
        actionReasonText,
        goldRecommendationText,
        getRecommendationText, getReasonText, encodeI18nParams,
        trendMeta, localizedTrendLabel,
        netMonthlySurplus, diversificationLabel, financialHealth,
        netWorth, suggestedAllocations,
        labelGoldMarketAnalysis, labelTrend,
        labelSevenDayChange, labelThirtyDayChange, labelNinetyDayChange,
        labelMa7, labelMa30, labelMaGap,
        labelCurrentAllocation, labelRecommendation, labelSuggestedAllocation,
        labelFinancialHealth, labelFinancialHealthOverview,
        labelNetWorth, labelLiquidityCoverage, labelMonthlySurplus,
        labelDiversification, labelCash, labelCertificates, labelGold,
        labelFixedAssets, labelMonths, labelEgp,
    } = data;

    pane.innerHTML = `
        <div class="row g-3 mb-4 fi-top-grid">

            <!-- Investment Recommendations -->
            <div class="col-12 col-xl-4">
                <div class="kpi-card h-100 fi-boardroom-card fi-investment-card">
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
                            const resolvedText = getRecommendationText(item);
                            const itemParamsEncoded = encodeI18nParams(item.params || {});
                            return `<div class="fi-note-card"><div ${item.key ? `data-i18n-key="${item.key}" data-i18n-params="${itemParamsEncoded}"` : ''}>${resolvedText}</div></div>`;
                        }).join('')}
                    </div>
                </div>
            </div>

            <!-- Financial Recommendations -->
            <div class="col-12 col-xl-4">
                <div class="kpi-card h-100 fi-boardroom-card fi-financial-card">
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
                    <div class="fi-info-box">${data.financialParagraph || t('recommend_asset_allocation_balanced', 'Financial position is balanced with healthy liquidity and diversified assets.')}</div>
                    <div class="fi-list-compact" style="margin-top:12px">
                        ${financialDetails.slice(1, 4).map((item) => {
                            const text = getRecommendationText(item);
                            const encoded = encodeI18nParams(item.params || {});
                            return `<div ${item.key ? `data-i18n-key="${item.key}" data-i18n-params="${encoded}"` : ''} class="fi-note-card">${text}</div>`;
                        }).join('')}
                    </div>
                </div>
            </div>

            <!-- Recommended Action -->
            <div class="col-12 col-xl-4">
                <div class="kpi-card h-100 fi-boardroom-card fi-action-card">
                    <div class="kpi-label" data-i18n="recommended_action">Recommended Action</div>
                    <div class="row g-3 fi-card-grid">
                        <div class="col-12">
                            <div class="fi-sub-card">
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
                        <div class="col-12">
                            <div class="fi-sub-card">
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
                                        </div>`).join('')}
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
                        ${forecastData.action_plan?.key
                            ? (_t[forecastData.action_plan.key] || forecastData.action_plan.key)
                                .replace('{gold_amount}',        fmtpresent(forecastData.action_plan.gold_amount || 0))
                                .replace('{cash_amount}',        fmtpresent(forecastData.action_plan.cash_amount || 0))
                                .replace('{certificate_amount}', fmtpresent(forecastData.action_plan.certificate_amount || 0))
                            : ''}
                    </div>
                </div>
            </div>

        </div>
    `;
}
