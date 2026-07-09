// exchange_rates.js — Exchange Rates Page
// Source: open.er-api.com (free, no key) → stored in Django DB
// CBE scrape runs locally via Python backend on user's machine

'use strict';

// ════════════════════════════════════════════════════════════════════════════
// CURRENCY METADATA
// ════════════════════════════════════════════════════════════════════════════

const CURRENCY_META = {
    USD: { flag: '🇺🇸', name: 'US Dollar' },
    EUR: { flag: '🇪🇺', name: 'Euro' },
    GBP: { flag: '🇬🇧', name: 'Pound Sterling' },
    SAR: { flag: '🇸🇦', name: 'Saudi Riyal' },
    AED: { flag: '🇦🇪', name: 'UAE Dirham' },
    KWD: { flag: '🇰🇼', name: 'Kuwaiti Dinar' },
    CAD: { flag: '🇨🇦', name: 'Canadian Dollar' },
    CHF: { flag: '🇨🇭', name: 'Swiss Franc' },
    JPY: { flag: '🇯🇵', name: 'Japanese Yen' },
    CNY: { flag: '🇨🇳', name: 'Chinese Yuan' },
    QAR: { flag: '🇶🇦', name: 'Qatari Riyal' },
    BHD: { flag: '🇧🇭', name: 'Bahraini Dinar' },
    OMR: { flag: '🇴🇲', name: 'Omani Riyal' },
    JOD: { flag: '🇯🇴', name: 'Jordanian Dinar' },
    NOK: { flag: '🇳🇴', name: 'Norwegian Krone' },
    SEK: { flag: '🇸🇪', name: 'Swedish Krona' },
    DKK: { flag: '🇩🇰', name: 'Danish Krone' },
    AUD: { flag: '🇦🇺', name: 'Australian Dollar' },
};

const TOP_CURRENCY_ORDER = [
    'USD',
    'EUR',
    'SAR',
    'AED',
    'QAR',
    'OMR',
    'BHD',
    'JOD',
    'KWD',
    'GBP',
];

// ════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ════════════════════════════════════════════════════════════════════════════

function sortRatesByPriority(rates) {
    const priority = new Map(
        TOP_CURRENCY_ORDER.map((code, index) => [code, index]),
    );
    return [...rates].sort((a, b) => {
        const aIndex = priority.has(a.currency_code)
            ? priority.get(a.currency_code)
            : TOP_CURRENCY_ORDER.length;
        const bIndex = priority.has(b.currency_code)
            ? priority.get(b.currency_code)
            : TOP_CURRENCY_ORDER.length;
        if (aIndex !== bIndex) return aIndex - bIndex;
        return a.currency_code.localeCompare(b.currency_code);
    });
}

function fmtRate(n) {
    const num = Number(n);
    if (!num) return '—';
    const decimals = num > 10 ? 4 : 6;
    return num.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

// ════════════════════════════════════════════════════════════════════════════
// EXCHANGE RATES RENDERING
// ════════════════════════════════════════════════════════════════════════════

async function renderExchangeRates() {
    const mc = document.getElementById('main-content');
    mc.innerHTML = `<div class="spinner-overlay">
        <div class="spinner-border text-primary"></div>
        <span data-i18n="loading_rates">${t('loading_rates', 'Loading rates...')}</span></div>`;

    let data;
    try {
        const res = await fetch('/api/rates/');
        data = await res.json();
    } catch (e) {
        mc.innerHTML = `<div class="empty-state">
            <div class="empty-icon">⚠️</div>
            <div class="empty-title" data-i18n="error_loading_rates">${t('error_loading_rates', 'Error loading exchange rates.')}</div></div>`;
        return;
    }

    const rates = data.rates || [];
    const fetchedAt = data.fetched_at;
    const hasData = rates.length > 0;
    const sortedRates = sortRatesByPriority(rates);

    const featuredRates = TOP_CURRENCY_ORDER.map((code) =>
        sortedRates.find((r) => r.currency_code === code),
    ).filter(Boolean);

    const buyText = t('buy', 'Buy');
    const sellText = t('sell', 'Sell');
    const egpPerText = t('egp_per_1', 'EGP per 1');

    const featuredCards = featuredRates
        .map((r) => {
            const meta = CURRENCY_META[r.currency_code] || {
                flag: '💱',
                name: r.currency_name,
            };
            return `
            <div class="col-6 col-md-4 col-xl-2">
                <div class="kpi-card" style="--kpi-accent:var(--accent-primary);text-align:center">
                    <div style="font-size:28px;margin-bottom:6px">${meta.flag}</div>
                    <div class="kpi-label">${r.currency_code}</div>
                    <div class="kpi-value" style="font-size:18px">${fmtRate(r.mid_rate)}</div>
                    <div class="kpi-sub" data-i18n="egp_per_1">${egpPerText} ${r.currency_code}</div>
                    <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:11px;color:var(--text-muted)">
                        <span style="display:flex; gap:4px;">
                            <span data-i18n="buy">${buyText}</span>
                            <span>${fmtRate(r.buy_rate)}</span>
                        </span>
                        <span style="display:flex; gap:4px;">
                            <span data-i18n="sell">${sellText}</span>
                            <span>${fmtRate(r.sell_rate)}</span>
                        </span>
                    </div>
                </div>
            </div>`;
        })
        .join('');

    const rows = sortedRates
        .map((r) => {
            const meta = CURRENCY_META[r.currency_code] || {
                flag: '💱',
                name: r.currency_name,
            };
            return `<tr>
                <td><span style="font-size:18px;margin-right:8px">${meta.flag}</span><strong>${r.currency_code}</strong></td>
                <td>${meta.name || r.currency_name}</td>
                <td class="text-end num-col">${fmtRate(r.buy_rate)}</td>
                <td class="text-end num-col" style="color:var(--accent-green)">${fmtRate(r.mid_rate)}</td>
                <td class="text-end num-col">${fmtRate(r.sell_rate)}</td>
            </tr>`;
        })
        .join('');

    const sourceText = t('source', 'Source');
    const lastUpdatedText = t('last_updated', 'Last updated');
    const refreshText = t('refresh_internet', 'Refresh from Internet');
    const noRatesText = t('no_rates_data', 'No exchange rate data yet.');
    const fetchNowText = t('fetch_now', 'Fetch Rates Now');
    const ratesVsText = t('rates_vs_egp', 'Rates are vs Egyptian Pound (EGP).');
    const disclaimerText = t('rate_disclaimer', 'Buy/Sell reflect a typical bank spread.');
    const cbeText = t('cbe_disclaimer', 'For official CBE rates visit:');
    const currencyHeader = t('currency', 'Currency');
    const nameHeader = t('name', 'Name');
    const buyEgpHeader = t('buy_egp', 'Buy (EGP)');
    const midRateHeader = t('mid_rate', 'Mid Rate');
    const sellEgpHeader = t('sell_egp', 'Sell (EGP)');

    mc.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title" data-i18n="exchange_rates">${t('exchange_rates', 'Exchange Rates')}</div>
                <div class="page-subtitle">
                    <span data-i18n="source">${sourceText}</span>: open.er-api.com &amp; CBE
                    ${fetchedAt ? `· <span data-i18n="last_updated">${lastUpdatedText}</span>: <strong>${fetchedAt}</strong>` : ''}
                </div>
            </div>
            <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
                <div id="ratesStatus"></div>
                <button class="btn-primary-custom" onclick="refreshExchangeRates()" id="btnRefreshRates">
                    <i class="bi bi-arrow-clockwise"></i> <span data-i18n="refresh_internet">${refreshText}</span>
                </button>
            </div>
        </div>

        ${
            !hasData
                ? `
                <div class="empty-state">
                    <div class="empty-icon">📊</div>
                    <div class="empty-title" data-i18n="no_rates_data">${noRatesText}</div>
                    <div class="empty-sub" style="margin-top:14px">
                        <button class="btn-primary-custom" onclick="refreshExchangeRates()">
                            <i class="bi bi-arrow-clockwise"></i> <span data-i18n="fetch_now">${fetchNowText}</span>
                        </button>
                    </div>
                </div>`
                : `
                <div class="row g-3 mb-4">${featuredCards}</div>

                <div style="background:var(--accent-blue-dim);border:1px solid rgba(26,110,245,0.3);border-radius:10px;padding:12px 18px;margin-bottom:20px;font-size:13px;color:var(--text-secondary)">
                    <i class="bi bi-info-circle" style="color:var(--accent-primary)"></i>
                    <strong data-i18n="rates_vs_egp">${ratesVsText}</strong>
                    <span data-i18n="rate_disclaimer">${disclaimerText}</span>
                </div>

                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th data-i18n="currency">${currencyHeader}</th>
                                <th data-i18n="name">${nameHeader}</th>
                                <th class="text-end" data-i18n="buy_egp">${buyEgpHeader}</th>
                                <th class="text-end" data-i18n="mid_rate">${midRateHeader}</th>
                                <th class="text-end" data-i18n="sell_egp">${sellEgpHeader}</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>`
        }

        <div style="margin-top:14px;font-size:12px;color:var(--text-muted)">
            <i class="bi bi-shield-check" style="color:var(--accent-green)"></i>
            <span data-i18n="cbe_disclaimer">${cbeText}</span>
            <a href="https://www.cbe.org.eg/en/economic-research/statistics/cbe-exchange-rates" target="_blank" style="color:var(--accent-primary)">cbe.org.eg</a>
        </div>`;
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// EXCHANGE RATES REFRESH
// ════════════════════════════════════════════════════════════════════════════

async function refreshExchangeRates() {
    const btn = document.getElementById('btnRefreshRates');
    const status = document.getElementById('ratesStatus');
    const fetchingText = t('fetching', 'Fetching…');
    const refreshText = t('refresh_internet', 'Refresh from Internet');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner-border spinner-border-sm"></div> ${fetchingText}`;
    }
    if (status) status.innerHTML = '';
    try {
        const res = await fetch('/api/rates/refresh/', { method: 'POST' });
        const data = await res.json();
        if (data.error) {
            const errorMsg = t('error_prefix', 'Error: ') + data.error;
            showToast(errorMsg, 'error');
        } else {
            const successMsg = t('rates_updated', 'Rates updated ✓');
            showToast(successMsg, 'success');
            renderExchangeRates();
            return;
        }
    } catch (e) {
        const networkMsg = t('network_error_prefix', 'Network error: ') + e.message;
        showToast(networkMsg, 'error');
    }
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i class="bi bi-arrow-clockwise"></i> ${refreshText}`;
    }
    applyTranslations();
}

// ════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.renderExchangeRates = renderExchangeRates;
window.refreshExchangeRates = refreshExchangeRates;
