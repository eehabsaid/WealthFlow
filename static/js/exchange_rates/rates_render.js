"use strict";
// rates_render.js — Exchange Rates page render (featured cards + full
// table). Split out of the former exchange_rates.js monolith; see
// exchange_rates.js header comment for the sibling list.

// ════════════════════════════════════════════════════════════════════════════
// EXCHANGE RATES RENDERING
// ════════════════════════════════════════════════════════════════════════════

async function renderExchangeRates() {
  const mc = document.getElementById("main-content");
  mc.innerHTML = `<div class="spinner-overlay">
        <div class="spinner-border text-primary"></div>
        <span data-i18n="loading_rates">${t("loading_rates", "Loading rates...")}</span></div>`;

  let data;
  try {
    const res = await fetch("/api/rates/");
    data = await res.json();
  } catch (e) {
    mc.innerHTML = `<div class="empty-state">
            <div class="empty-icon">⚠️</div>
            <div class="empty-title" data-i18n="error_loading_rates">${t("error_loading_rates", "Error loading exchange rates.")}</div></div>`;
    return;
  }

  const rates = data.rates || [];
  const fetchedAt = data.fetched_at;
  const hasData = rates.length > 0;
  const sortedRates = sortRatesByPriority(rates);
  const baseCode = baseCurrencyCode() || (window.WF_BASE && window.WF_BASE.pivot_currency) || "";

  // rates are stored pivot-relative (see core_exchangerate); re-express each
  // field in the viewer's own default currency. `field` is "buy_rate",
  // "mid_rate" or "sell_rate".
  function rateInBase(code, field) {
    const pivot = window.WF_BASE.pivot_currency;
    const quote = (c) => {
      if (c === pivot) return 1;
      const row = rates.find((r) => r.currency_code === c);
      return row ? Number(row[field]) || 0 : 0;
    };
    const base = quote(baseCode);
    return base > 0 ? quote(code) / base : 0;
  }

  const featuredRates = TOP_CURRENCY_ORDER.map((code) =>
    sortedRates.find((r) => r.currency_code === code)
  ).filter(Boolean);

  const buyText = t("buy", "Buy");
  const sellText = t("sell", "Sell");
  const perOneText = t("rate_per_1", "{base} per 1");

  const featuredCards = featuredRates
    .map((r) => {
      const meta = CURRENCY_META[r.currency_code] || {
        flag: "💱",
        name: r.currency_name,
      };
      return `
            <div class="col-6 col-md-4 col-xl-2">
                <div class="kpi-card" style="--kpi-accent:var(--accent-primary);text-align:center">
                    <div style="font-size:28px;margin-bottom:6px">${meta.flag}</div>
                    <div class="kpi-label">${r.currency_code}</div>
                    <div class="kpi-value" style="font-size:18px">${fmtRate(rateInBase(r.currency_code, "mid_rate"))}</div>
                    <div class="kpi-sub" data-i18n="rate_per_1">${perOneText} ${r.currency_code}</div>
                    <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:11px;color:var(--text-muted)">
                        <span style="display:flex; gap:4px;">
                            <span data-i18n="buy">${buyText}</span>
                            <span>${fmtRate(rateInBase(r.currency_code, "buy_rate"))}</span>
                        </span>
                        <span style="display:flex; gap:4px;">
                            <span data-i18n="sell">${sellText}</span>
                            <span>${fmtRate(rateInBase(r.currency_code, "sell_rate"))}</span>
                        </span>
                    </div>
                </div>
            </div>`;
    })
    .join("");

  const rows = sortedRates
    .map((r) => {
      const meta = CURRENCY_META[r.currency_code] || {
        flag: "💱",
        name: r.currency_name,
      };
      return `<tr>
                <td><span style="font-size:18px;margin-right:8px">${meta.flag}</span><strong>${r.currency_code}</strong></td>
                <td>${meta.name || r.currency_name}</td>
                <td class="text-end num-col">${fmtRate(rateInBase(r.currency_code, "buy_rate"))}</td>
                <td class="text-end num-col" style="color:var(--accent-green)">${fmtRate(rateInBase(r.currency_code, "mid_rate"))}</td>
                <td class="text-end num-col">${fmtRate(rateInBase(r.currency_code, "sell_rate"))}</td>
            </tr>`;
    })
    .join("");

  const sourceText = t("source", "Source");
  const lastUpdatedText = t("last_updated", "Last updated");
  const refreshText = t("refresh_internet", "Refresh from Internet");
  const noRatesText = t("no_rates_data", "No exchange rate data yet.");
  const fetchNowText = t("fetch_now", "Fetch Rates Now");
  const ratesVsText = t("rates_vs_base", "Rates are vs your default currency ({base}).");
  const disclaimerText = t("rate_disclaimer", "Buy/Sell reflect a typical bank spread.");
  const cbeText = t("cbe_disclaimer", "For official CBE rates visit:");
  const currencyHeader = t("currency", "Currency");
  const nameHeader = t("name", "Name");
  const buyBaseHeader = t("buy_base", "Buy ({base})");
  const midRateHeader = t("mid_rate", "Mid Rate");
  const sellBaseHeader = t("sell_base", "Sell ({base})");

  mc.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title" data-i18n="exchange_rates">${t("exchange_rates", "Exchange Rates")}</div>
                <div class="page-subtitle">
                    <span data-i18n="source">${sourceText}</span>: open.er-api.com &amp; CBE
                    ${fetchedAt ? `· <span data-i18n="last_updated">${lastUpdatedText}</span>: <strong>${formatDate(fetchedAt)}</strong>` : ""}
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
                    <strong data-i18n="rates_vs_base">${ratesVsText}</strong>
                    <span data-i18n="rate_disclaimer">${disclaimerText}</span>
                </div>

                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th data-i18n="currency">${currencyHeader}</th>
                                <th data-i18n="name">${nameHeader}</th>
                                <th class="text-end" data-i18n="buy_base">${buyBaseHeader}</th>
                                <th class="text-end" data-i18n="mid_rate">${midRateHeader}</th>
                                <th class="text-end" data-i18n="sell_base">${sellBaseHeader}</th>
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
