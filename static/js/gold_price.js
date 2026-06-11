"use strict";

const CARAT_META = {
  carat_24k: {
    label_key: "label_24k",
    label: "عيار 24",
    label_en: "24K",
    color: "#ffd166",
    purity: "99.9%",
  },
  carat_22k: {
    label_key: "label_22k",
    label: "عيار 22",
    label_en: "22K",
    color: "#f5c518",
    purity: "91.7%",
  },
  carat_21k: {
    label_key: "label_21k",
    label: "عيار 21",
    label_en: "21K",
    color: "#e8b000",
    purity: "87.5%",
  },
  carat_18k: {
    label_key: "label_18k",
    label: "عيار 18",
    label_en: "18K",
    color: "#c49a00",
    purity: "75.0%",
  },
};

async function renderGoldPrice() {
  const mc = document.getElementById("main-content");
  mc.innerHTML = `<div class="spinner-overlay">
    <div class="spinner-border text-primary"></div>
    <span data-i18n="loading_gold">Loading gold prices...</span></div>`;

  let data;
  try {
    const res = await fetch("/api/gold/");
    data = await res.json();
  } catch (e) {
    mc.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div>
      <div class="empty-title" data-i18n="error_loading_gold">Error loading gold price.</div></div>`;
    return;
  }

  const gd = data.gold;
  const hasData = !!gd;

  const caratCards = hasData
    ? Object.entries(CARAT_META)
        .map(([key, meta]) => {
          return `
    <div class="col-6 col-md-3">
      <div class="kpi-card" style="--kpi-accent:${meta.color};--kpi-bg:rgba(255,209,102,0.08);text-align:center;border-color:${meta.color}44">
        <div style="font-size:28px;margin-bottom:4px">🥇</div>
        <div class="kpi-label" style="color:${meta.color}">${meta.label_en} — ${meta.label}</div>
        <div style="font-size:10px;color:var(--text-muted);margin-bottom:2px" data-i18n="egp_per_gram">EGP / gram</div>
        <div style="display:flex;gap:10px;font-size:13px;margin-top:8px">
          <div style="flex:1;background:rgba(255,255,255,0.1);padding:6px;border-radius:4px;text-align:center">
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:2px" data-i18n="buy">BUY</div>
            <div style="font-weight:bold;color:${meta.color}">${fmt(gd[key + "_buy"])}</div>
          </div>
          <div style="flex:1;background:rgba(255,255,255,0.1);padding:6px;border-radius:4px;text-align:center">
            <div style="font-size:10px;color:var(--text-muted);margin-bottom:2px" data-i18n="sell">SELL</div>
            <div style="font-weight:bold;color:${meta.color}">${fmt(gd[key])}</div>
          </div>
        </div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:6px"><span data-i18n="purity">Purity</span>: ${meta.purity}</div>
      </div>
    </div>`;
        })
        .join("")
    : "";

  mc.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title" data-i18n="gold_prices">🥇 Gold Prices</div>
        <div class="page-subtitle">
          <span data-i18n="source">Source</span>: goldbullioneg.com + open.er-api.com
          ${hasData ? `· <strong>${gd.fetched_at}</strong>` : ""}
        </div>
      </div>
      <button class="btn-primary-custom" onclick="refreshGoldPrice()" id="btnRefreshGold">
        <i class="bi bi-arrow-clockwise"></i> <span data-i18n="refresh_prices">Refresh Prices</span>
      </button>
    </div>

    ${
      !hasData
        ? `
      <div class="empty-state">
        <div class="empty-icon">🥇</div>
        <div class="empty-title" data-i18n="no_gold_data">No gold price data yet.</div>
      </div>`
        : `

    <div class="row g-3 mb-4">${caratCards}</div>

    <div class="row g-3 mb-4">
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-label" data-i18n="gold_spot">Gold Spot (USD/oz)</div><div class="kpi-value">$${fmt(gd.usd_per_oz)}</div></div></div>
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-label" data-i18n="24k_per_gram">24K per gram (USD)</div><div class="kpi-value">$${Number(gd.usd_gram_24k).toFixed(4)}</div></div></div>
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-label" data-i18n="usd_egp_rate">USD → EGP rate</div><div class="kpi-value">${Number(gd.usd_to_egp).toFixed(2)}</div></div></div>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead><tr>
          <th data-i18n="carat">Carat</th>
          <th data-i18n="arabic_label">Arabic</th>
          <th data-i18n="purity">Purity</th>
          <th class="text-center" data-i18n="buy">BUY</th>
          <th class="text-center" data-i18n="sell">SELL</th>
          <th class="text-center" data-i18n="spread">Spread</th>
        </tr></thead>
        <tbody>
          ${Object.entries(CARAT_META)
            .map(([key, meta]) => {
              const egpBuy = Number(gd[key + "_buy"]);
              const egpSell = Number(gd[key]);
              const spread = egpBuy - egpSell;
              return `<tr>
              <td><strong style="color:${meta.color}">${meta.label_en}</strong></td>
              <td>${meta.label}</td>
              <td>${meta.purity}</td>
              <td class="text-center num-col" style="color:${meta.color}">${fmt(egpBuy)}</td>
              <td class="text-center num-col" style="color:${meta.color}">${fmt(egpSell)}</td>
              <td class="text-center num-col" style="color:var(--text-muted)">${fmt(spread)}</td>
            </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>`
    }

    <div style="margin-top:14px;font-size:12px;color:var(--text-muted)">
      <i class="bi bi-info-circle"></i> <span data-i18n="gold_disclaimer">Prices are directly from goldbullioneg.com. BUY = selling to the shop, SELL = buying from the shop.</span>
    </div>`;
  applyTranslations();
}

async function refreshGoldPrice() {
  const btn = document.getElementById("btnRefreshGold");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML =
      '<div class="spinner-border spinner-border-sm"></div> Fetching…';
  }
  try {
    const res = await fetch("/api/gold/refresh/", { method: "POST" });
    const data = await res.json();
    if (data.error) {
      showToast("Error: " + data.error, "error");
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh Prices';
      }
    } else {
      // Check if the translate helper is available
      const msg =
        typeof translate === "function"
          ? translate("gold_updated")
          : "Gold prices updated";
      showToast(msg, "success");
      renderGoldPrice();
    }
  } catch (e) {
    showToast("Network error: " + e.message, "error");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh Prices';
    }
  }
}
window.renderGoldPrice = renderGoldPrice;
window.refreshGoldPrice = refreshGoldPrice;
