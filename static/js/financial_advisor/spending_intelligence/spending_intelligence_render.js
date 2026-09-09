"use strict";

const _emojiToBiMap = {
  "💰": "bi-cash-stack",
  "🏠": "bi-house-door",
  "🚗": "bi-car-front",
  "🛒": "bi-cart3",
  "🍽️": "bi-cup-hot",
  "👨‍👩‍👧": "bi-people",
  "👨‍👩‍👦": "bi-people",
  "🚬": "bi-wind",
  "🚌": "bi-bus-front",
  "🎓": "bi-mortarboard",
  "💡": "bi-lightbulb",
  "🧼": "bi-droplet",
  "🛍️": "bi-bag",
  "✈️": "bi-airplane",
  "🏥": "bi-hospital",
  "📱": "bi-phone",
  "🍔": "bi-cup-hot",
  "👕": "bi-shop",
};

function _getIconClass(emojiStr) {
  if (!emojiStr) return "bi-tag";
  for (let key in _emojiToBiMap) {
    if (emojiStr.includes(key)) return _emojiToBiMap[key];
  }
  return "bi-tag";
}

function _renderMonthlyTrendBars(payload, selectedCatId = "all") {
  const container = document.getElementById("si-monthly-trend-card-body");
  if (!container) return;

  const monthlyComparison = payload?.monthly_comparison || {};
  const months = monthlyComparison.months || [];
  const byCategory = monthlyComparison.by_category || {};

  let barsData = [];
  if (selectedCatId === "all") {
    barsData = months;
  } else {
    const catMonths = byCategory[selectedCatId] || [];
    const catMonthMap = {};
    catMonths.forEach((m) => {
      catMonthMap[`${m.year}-${m.month}`] = m;
    });

    barsData = months.map((m) => {
      const match = catMonthMap[`${m.year}-${m.month}`];
      return {
        year: m.year,
        month: m.month,
        total_egp: match ? match.total_egp : 0.0,
        count: match ? match.count : 0,
      };
    });
  }

  let html = "";

  if (monthlyComparison.insufficient_history && months.length < 3) {
    html += `
      <div style="background:rgba(123,147,201,0.05); border:1px solid rgba(123,147,201,0.1); border-radius:8px; padding:16px; font-size:13px; color:var(--text-secondary); margin-bottom:32px; line-height:1.6; text-align:center;">
        <i class="bi bi-info-circle me-1" style="font-size:16px;"></i> <span data-i18n="spending_intelligence_insufficient_history"></span>
      </div>
    `;
  }

  if (barsData.length > 0) {
    const maxAmount = Math.max(...barsData.map((m) => m.total_egp));

    let barsHtml = "";
    barsData.forEach((m, idx) => {
      const heightPct = maxAmount > 0 ? (m.total_egp / maxAmount) * 100 : 0;
      const monthKey = `month_short_${m.month}`;
      const monthName =
        typeof t === "function"
          ? t(monthKey)
          : new Date(m.year, m.month - 1).toLocaleString("en-US", { month: "short" });

      let diffHtml = "";
      if (idx > 0 && barsData.length >= 3) {
        const prevAmount = barsData[idx - 1].total_egp;
        if (prevAmount > 0) {
          const diffPct = ((m.total_egp - prevAmount) / prevAmount) * 100.0;
          const isIncrease = diffPct > 0;
          const color = isIncrease ? "var(--bs-danger)" : "var(--bs-success)";
          const icon = isIncrease ? "▲" : "▼";
          diffHtml = `
            <div style="text-align:center;">
              <div style="font-size:12px; color:${color}; font-weight:700;" title="Change from previous month">${icon} ${Math.abs(diffPct).toFixed(1)}%</div>
              <div style="font-size:10px; color:rgba(123,147,201,0.7); margin-top:2px;" data-i18n="spending_intelligence_compared_prev"></div>
            </div>
          `;
        }
      }

      barsHtml += `
        <div class="d-flex flex-column align-items-center" style="width:100px;">
          <div style="min-height:50px; height:auto; display:flex; align-items:flex-end; justify-content:center;">
             ${diffHtml}
          </div>
          <div style="width:100%; height:160px; display:flex; align-items:flex-end; margin-top:8px; margin-bottom:16px;">
            <div style="width:100%; height:${heightPct}%; background:var(--bs-primary, #0d6efd); border-radius:8px 8px 0 0; transition:height 0.6s cubic-bezier(0.4, 0, 0.2, 1);"></div>
          </div>
          <div style="font-size:13px; font-weight:600; color:rgba(123,147,201,0.8); margin-bottom:4px; text-align:center;">${monthName} ${m.year}</div>
          <div style="font-size:15px; font-weight:800; color:var(--text-primary); text-align:center; margin-bottom:2px;">${fmt(Number(m.total_egp).toFixed(2))}</div>
          <div style="font-size:11px; color:rgba(123,147,201,0.6); text-align:center;">${m.count} <span data-i18n="spending_intelligence_tx"></span></div>
        </div>
      `;
    });

    html += `
      <div class="d-flex justify-content-center" style="gap:32px; overflow-x:auto; padding-bottom:8px;">
        ${barsHtml}
      </div>
    `;
  } else {
    html += `
      <div style="text-align:center; padding:32px 0; color:var(--text-secondary); font-size:14px; line-height:1.6;" data-i18n="spending_intelligence_no_data"></div>
    `;
  }

  container.innerHTML = html;
  if (typeof applyTranslations === "function") applyTranslations();
}

function _buildKeyFindingsHtml(keyFindings) {
  let findingsHtml = `
    <h3 style="font-size:18px; font-weight:700; margin-top:16px; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_key_findings"></h3>
    <div class="card border-0 mb-5 fade-in-up delay-2" si-modern-card>
      <div class="card-body d-flex flex-column justify-content-center" style="padding:32px; gap:20px;">
  `;

  if (keyFindings.most_frequent) {
    const mf = keyFindings.most_frequent;
    const catAvg = mf.count > 0 ? mf.avg_per_tx : 0;
    const catNameHtml = `<b>${mf.name}</b>`;
    const paramsObj = {
      category: catNameHtml,
      count: mf.count,
      avg: `<b>${fmt(Number(catAvg).toFixed(2))}</b>`,
    };
    findingsHtml += `
      <div style="background:rgba(13,110,253,0.05); border:1px solid rgba(13,110,253,0.15); border-radius:8px; padding:20px; display:flex; gap:16px; align-items:flex-start;">
        <i class="bi bi-info-circle-fill" style="color:#0d6efd; font-size:18px; margin-top:2px;"></i>
        <div style="font-size:14px; color:var(--text-primary); line-height:1.6;">
          <span data-i18n-html-key="spending_intelligence_kf_frequent" data-i18n-params='${JSON.stringify(paramsObj).replace(/'/g, "&apos;")}'></span>
        </div>
      </div>
    `;
  }

  if (keyFindings.largest_expense) {
    const le = keyFindings.largest_expense;
    const amtStr = `<b>${fmt(Number(le.amount_egp).toFixed(2))}</b>`;
    const dateHtml = `<b>${formatDate(le.date)}</b>`;
    if (le.description) {
      const paramsObj = { amount: amtStr, description: le.description, date: dateHtml };
      findingsHtml += `
          <div style="background:rgba(255,193,7,0.08); border:1px solid rgba(255,193,7,0.3); border-radius:8px; padding:20px; display:flex; gap:16px; align-items:flex-start;">
            <i class="bi bi-exclamation-triangle-fill" style="color:#e0a800; font-size:18px; margin-top:2px;"></i>
            <div style="font-size:14px; color:var(--text-primary); line-height:1.6;">
              <span data-i18n-html-key="spending_intelligence_kf_largest_with_desc" data-i18n-params='${JSON.stringify(paramsObj).replace(/'/g, "&apos;")}'></span>
            </div>
          </div>
        `;
    } else {
      const paramsObj = { amount: amtStr, date: dateHtml };
      findingsHtml += `
          <div style="background:rgba(255,193,7,0.08); border:1px solid rgba(255,193,7,0.3); border-radius:8px; padding:20px; display:flex; gap:16px; align-items:flex-start;">
            <i class="bi bi-exclamation-triangle-fill" style="color:#e0a800; font-size:18px; margin-top:2px;"></i>
            <div style="font-size:14px; color:var(--text-primary); line-height:1.6;">
              <span data-i18n-html-key="spending_intelligence_kf_largest_no_desc" data-i18n-params='${JSON.stringify(paramsObj).replace(/'/g, "&apos;")}'></span>
            </div>
          </div>
        `;
    }
  }

  if (!keyFindings.most_frequent && !keyFindings.largest_expense) {
    findingsHtml += `
        <div style="font-size:14px; color:rgba(123,147,201,0.6); line-height:1.6; text-align:center; padding:24px 0;">
          <i class="bi bi-info-circle mb-3" style="font-size:28px; display:block;"></i>
          <span data-i18n="spending_intelligence_ai_insufficient"></span>
        </div>
      `;
  }

  findingsHtml += `</div></div>`;
  return findingsHtml;
}

window._emojiToBiMap = _emojiToBiMap;
window._getIconClass = _getIconClass;
window._renderMonthlyTrendBars = _renderMonthlyTrendBars;
window._buildKeyFindingsHtml = _buildKeyFindingsHtml;
