/* ============================================================
   exchange_rates.js — Exchange Rates Page
   Source: open.er-api.com (free, no key) → stored in Django DB
   CBE scrape runs locally via Python backend on user's machine
   ============================================================ */
'use strict';

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

const TOP_CURRENCY_ORDER = ['USD','EUR','SAR','AED','QAR','OMR','BHD','JOD','KWD','GBP'];

function sortRatesByPriority(rates) {
  const priority = new Map(TOP_CURRENCY_ORDER.map((code, index) => [code, index]));
  return [...rates].sort((a, b) => {
    const aIndex = priority.has(a.currency_code) ? priority.get(a.currency_code) : TOP_CURRENCY_ORDER.length;
    const bIndex = priority.has(b.currency_code) ? priority.get(b.currency_code) : TOP_CURRENCY_ORDER.length;
    if (aIndex !== bIndex) return aIndex - bIndex;
    return a.currency_code.localeCompare(b.currency_code);
  });
}

async function renderExchangeRates() {
  const mc = document.getElementById('main-content');
  mc.innerHTML = `<div class="spinner-overlay">
    <div class="spinner-border text-primary"></div>
    <span>Loading rates...</span></div>`;

  let data;
  try {
    const res = await fetch('/api/rates/');
    data = await res.json();
  } catch (e) {
    mc.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div>
      <div class="empty-title">Error loading exchange rates.</div></div>`;
    return;
  }

  const rates    = data.rates || [];
  const fetchedAt = data.fetched_at;
  const hasData  = rates.length > 0;

  const sortedRates = sortRatesByPriority(rates);

  /* ── Highlight cards for top currencies ── */
  const featuredRates = TOP_CURRENCY_ORDER
    .map(code => sortedRates.find(r => r.currency_code === code))
    .filter(Boolean);

  const featuredCards = featuredRates.map(r => {
    const meta = CURRENCY_META[r.currency_code] || { flag: '💱', name: r.currency_name };
    return `
      <div class="col-6 col-md-4 col-xl-2">
        <div class="kpi-card" style="--kpi-accent:var(--accent-primary);text-align:center">
          <div style="font-size:28px;margin-bottom:6px">${meta.flag}</div>
          <div class="kpi-label">${r.currency_code}</div>
          <div class="kpi-value" style="font-size:18px">${fmtRate(r.mid_rate)}</div>
          <div class="kpi-sub">EGP per 1 ${r.currency_code}</div>
          <div style="display:flex;justify-content:space-between;margin-top:8px;
                      font-size:11px;color:var(--text-muted)">
            <span>Buy: ${fmtRate(r.buy_rate)}</span>
            <span>Sell: ${fmtRate(r.sell_rate)}</span>
          </div>
        </div>
      </div>`;
  }).join('');

  /* ── Full table ── */
  const rows = sortedRates.map(r => {
    const meta = CURRENCY_META[r.currency_code] || { flag: '💱', name: r.currency_name };
    return `<tr>
      <td><span style="font-size:18px;margin-right:8px">${meta.flag}</span>
          <strong>${r.currency_code}</strong></td>
      <td>${meta.name || r.currency_name}</td>
      <td class="text-end num-col">${fmtRate(r.buy_rate)}</td>
      <td class="text-end num-col" style="color:var(--accent-green)">${fmtRate(r.mid_rate)}</td>
      <td class="text-end num-col">${fmtRate(r.sell_rate)}</td>
    </tr>`;
  }).join('');

  mc.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">Exchange Rates</div>
        <div class="page-subtitle">
          Source: <a href="https://open.er-api.com" target="_blank" style="color:var(--accent-primary)">
            open.er-api.com
          </a> &amp;
          <a href="https://www.cbe.org.eg/en/economic-research/statistics/cbe-exchange-rates"
             target="_blank" style="color:var(--accent-primary)">CBE</a>
          ${fetchedAt ? `· Last updated: <strong>${fetchedAt}</strong>` : ''}
        </div>
      </div>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <div id="ratesStatus"></div>
        <button class="btn-primary-custom" onclick="refreshExchangeRates()" id="btnRefreshRates">
          <i class="bi bi-arrow-clockwise"></i> Refresh from Internet
        </button>
      </div>
    </div>

    ${!hasData ? `
      <div class="empty-state">
        <div class="empty-icon">📊</div>
        <div class="empty-title">No exchange rate data yet.</div>
        <div class="empty-sub" style="margin-top:14px">
          <button class="btn-primary-custom" onclick="refreshExchangeRates()">
            <i class="bi bi-arrow-clockwise"></i> Fetch Rates Now
          </button>
        </div>
      </div>` : `

    <div class="row g-3 mb-4">${featuredCards}</div>

    <div style="background:var(--accent-blue-dim);border:1px solid rgba(26,110,245,0.3);
                border-radius:10px;padding:12px 18px;margin-bottom:20px;font-size:13px;
                color:var(--text-secondary)">
      <i class="bi bi-info-circle" style="color:var(--accent-primary)"></i>
      <strong style="color:var(--text-primary)">Rates are vs Egyptian Pound (EGP).</strong>
      Buy/Sell reflect a typical ±0.5% bank spread around the mid rate.
      Click <strong>Refresh</strong> to fetch the latest rates directly from the internet.
      Rates update once per day on the free tier.
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead><tr>
          <th>Currency</th>
          <th>Name</th>
          <th class="text-end">Buy (EGP)</th>
          <th class="text-end">Mid Rate</th>
          <th class="text-end">Sell (EGP)</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`}

    <div style="margin-top:14px;font-size:12px;color:var(--text-muted)">
      <i class="bi bi-shield-check" style="color:var(--accent-green)"></i>
      For official CBE rates visit:
      <a href="https://www.cbe.org.eg/en/economic-research/statistics/cbe-exchange-rates"
         target="_blank" style="color:var(--accent-primary)">cbe.org.eg</a>
    </div>`;
}

async function refreshExchangeRates() {
  const btn    = document.getElementById('btnRefreshRates');
  const status = document.getElementById('ratesStatus');
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner-border spinner-border-sm"></div> Fetching…'; }
  if (status) status.innerHTML = '';

  try {
    const res  = await fetch('/api/rates/refresh/', { method: 'POST' });
    const data = await res.json();
    if (data.error) {
      showToast('Error: ' + data.error, 'error');
    } else {
      showToast(data.message + ' ✓', 'success');
      renderExchangeRates();
      return;
    }
  } catch (e) {
    showToast('Network error: ' + e.message, 'error');
  }
  if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh from Internet'; }
}

function fmtRate(n) {
  const num = Number(n);
  if (!num) return '—';
  // Use more decimals for rates like KWD that are > 100 EGP
  const decimals = num > 10 ? 4 : 6;
  return num.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

window.renderExchangeRates  = renderExchangeRates;
window.refreshExchangeRates = refreshExchangeRates;
