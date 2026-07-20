"use strict";
// Spending intelligence module
// This file is part of the financial_advisor module. Do not edit directly.

function _renderSpendingIntelligenceLoading() {
  const pane = document.getElementById("fa-pane-spending-intelligence");
  if (!pane) return;
  pane.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:24px; color:var(--text-secondary);" data-i18n="spending_intelligence_loading"></div>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

function _renderSpendingIntelligenceError() {
  const pane = document.getElementById("fa-pane-spending-intelligence");
  if (!pane) return;
  pane.innerHTML = `
    <div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);">
      <span data-i18n="spending_intelligence_error"></span>
    </div>
  `;
  if (typeof applyTranslations === "function") applyTranslations();
}

const _emojiToBiMap = {
  '💰': 'bi-cash-stack',
  '🏠': 'bi-house-door',
  '🚗': 'bi-car-front',
  '🛒': 'bi-cart3',
  '🍽️': 'bi-cup-hot',
  '👨‍👩‍👧': 'bi-people',
  '👨‍👩‍👦': 'bi-people',
  '🚬': 'bi-wind',
  '🚌': 'bi-bus-front',
  '🎓': 'bi-mortarboard',
  '💡': 'bi-lightbulb',
  '🧼': 'bi-droplet',
  '🛍️': 'bi-bag',
  '✈️': 'bi-airplane',
  '🏥': 'bi-hospital',
  '📱': 'bi-phone',
  '🍔': 'bi-cup-hot',
  '🛒': 'bi-basket',
  '👕': 'bi-shop'
};

function _getIconClass(emojiStr) {
  if (!emojiStr) return 'bi-tag';
  for (let key in _emojiToBiMap) {
    if (emojiStr.includes(key)) return _emojiToBiMap[key];
  }
  return 'bi-tag';
}

function _renderSpendingIntelligence(payload) {
  const pane = document.getElementById("fa-pane-spending-intelligence");
  if (!pane) return;

  const categories = payload?.categories || [];
  const keyFindings = payload?.key_findings || {};
  const monthlyComparison = payload?.monthly_comparison || {};
  const months = monthlyComparison.months || [];
  const aiInsights = payload?.ai_insights || [];
  const recommendedActions = payload?.recommended_actions || [];
  
  // Header block
  let headerHtml = `
    <div class="d-flex justify-content-between align-items-center mb-4">
      <div style="font-size:14px; color:var(--text-secondary);" data-i18n="spending_intelligence_subtitle"></div>
    </div>
  `;

  // 1. Average Monthly Expenses
  let avgMonthlyHtml = `
    <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
      <div class="card-body" style="padding:24px;">
        <div style="font-size:11px; font-weight:600; color:rgba(123,147,201,0.8); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;" data-i18n="spending_intelligence_avg_monthly"></div>
        <div style="font-size:36px; font-weight:800; color:var(--text-primary); margin-bottom:4px; letter-spacing:-0.5px;">${fmt(Number(payload?.avg_monthly_expenses || 0).toFixed(2))} EGP</div>
        <div style="font-size:12px; color:rgba(123,147,201,0.6);" data-i18n="spending_intelligence_based_on"></div>
      </div>
    </div>
  `;

  // Empty state handling
  if (categories.length === 0) {
    pane.innerHTML = `
      <div style="max-width:1200px;">
        ${headerHtml}
        ${avgMonthlyHtml}
        <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:48px 24px; text-align:center;">
          <i class="bi bi-wallet2" style="font-size:48px; color:var(--text-muted); margin-bottom:16px;"></i>
          <h4 style="color:var(--text-primary); font-weight:600; font-size:18px; margin-bottom:8px;" data-i18n="spending_intelligence_no_history"></h4>
          <p style="color:var(--text-secondary); font-size:14px; margin:0;" data-i18n="spending_intelligence_start_recording"></p>
        </div>
      </div>
    `;
    if (typeof applyTranslations === "function") applyTranslations();
    return;
  }

  // 2. Category Breakdown
  let categoryHtml = `
    <h3 style="font-size:16px; font-weight:700; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_category_breakdown"></h3>
    <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
      <div class="card-body" style="padding:24px;">
  `;

  let catLabels = [];
  let catValues = [];

  categories.forEach((cat, index) => {
    catLabels.push(cat.name); // Not translating category names in chart
    catValues.push(cat.amount_egp);

    const isLast = index === categories.length - 1;
    const mbClass = isLast ? "" : "mb-4";
    const biIcon = _getIconClass(cat.icon);
    
    // Calculate average
    const catAvg = cat.count > 0 ? (cat.amount_egp / cat.count) : 0;
    
    // Dynamic color for progress bar
    let barColor = "var(--bs-primary)";
    if (cat.percentage <= 10) barColor = "var(--bs-secondary)";
    else if (cat.percentage < 30) barColor = "var(--bs-success)";

    categoryHtml += `
      <div class="d-flex align-items-start ${mbClass}">
        <div style="width:36px; height:36px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:20px; color:var(--text-primary); margin-right:16px;">
          <i class="bi ${biIcon}"></i>
        </div>
        <div class="flex-grow-1">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span style="font-weight:700; font-size:14px; color:var(--text-primary);">${cat.name}</span>
            <span style="font-weight:800; font-size:14px; color:var(--text-primary);">${fmt(Number(cat.amount_egp).toFixed(2))} EGP</span>
          </div>
          <div style="width:100%; height:6px; background:rgba(123,147,201,0.1); border-radius:3px; margin-bottom:6px; overflow:hidden;">
            <div style="height:100%; width:${cat.percentage}%; background:${barColor}; border-radius:3px;"></div>
          </div>
          <div class="d-flex justify-content-between align-items-center">
            <div style="font-size:11px; color:var(--text-secondary);">${cat.percentage.toFixed(1)}% &nbsp;&bull;&nbsp; ${cat.count} <span data-i18n="spending_intelligence_tx">transactions</span></div>
            <div style="font-size:11px; color:var(--text-secondary);"><span data-i18n="spending_intelligence_avg_per_tx">Average</span>: ${fmt(Number(catAvg).toFixed(2))} EGP</div>
          </div>
        </div>
      </div>
    `;
  });
  categoryHtml += `</div></div>`;

  // 3. Spending Distribution (Donut Chart)
  let donutHtml = `
    <div class="card border-0 mb-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
      <div class="card-body" style="padding:24px;">
        <h4 style="font-size:14px; font-weight:600; color:var(--text-primary); margin-bottom:16px; text-align:center;" data-i18n="spending_intelligence_distribution"></h4>
        <div style="position:relative;height:240px">
          <canvas id="spendingDonutChart"></canvas>
        </div>
      </div>
    </div>
  `;

  // 4. Key Findings
  let findingsHtml = `
    <h3 style="font-size:16px; font-weight:700; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_key_findings"></h3>
    <div class="d-flex flex-column gap-3 mb-4">
  `;

  if (keyFindings.most_frequent) {
    const mf = keyFindings.most_frequent;
    const catAvg = mf.count > 0 ? (mf.avg_per_tx) : 0;
    const paramsObj = { category: mf.name, count: mf.count, avg: fmt(Number(catAvg).toFixed(2)) };
    findingsHtml += `
      <div style="background:rgba(13,110,253,0.05); border:1px solid rgba(13,110,253,0.2); border-radius:8px; padding:16px; display:flex; gap:12px; align-items:flex-start;">
        <i class="bi bi-info-square-fill" style="color:#0d6efd; font-size:14px; margin-top:2px;"></i>
        <div style="font-size:13px; color:var(--text-primary); line-height:1.5;">
          <span data-i18n-key="spending_intelligence_kf_frequent" data-i18n-params='${JSON.stringify(paramsObj).replace(/'/g, "&apos;")}'></span>
        </div>
      </div>
    `;
  }

  if (keyFindings.largest_expense) {
    const le = keyFindings.largest_expense;
    const amtStr = fmt(Number(le.amount_egp).toFixed(2));
    if (le.description) {
        const paramsObj = { amount: amtStr, description: le.description, date: le.date };
        findingsHtml += `
          <div style="background:rgba(255,193,7,0.05); border:1px solid rgba(255,193,7,0.2); border-radius:8px; padding:16px; display:flex; gap:12px; align-items:flex-start;">
            <i class="bi bi-exclamation-triangle-fill" style="color:#ffc107; font-size:14px; margin-top:2px;"></i>
            <div style="font-size:13px; color:var(--text-primary); line-height:1.5;">
              <span data-i18n-key="spending_intelligence_kf_largest_with_desc" data-i18n-params='${JSON.stringify(paramsObj).replace(/'/g, "&apos;")}'></span>
            </div>
          </div>
        `;
    } else {
        const paramsObj = { amount: amtStr, date: le.date };
        findingsHtml += `
          <div style="background:rgba(255,193,7,0.05); border:1px solid rgba(255,193,7,0.2); border-radius:8px; padding:16px; display:flex; gap:12px; align-items:flex-start;">
            <i class="bi bi-exclamation-triangle-fill" style="color:#ffc107; font-size:14px; margin-top:2px;"></i>
            <div style="font-size:13px; color:var(--text-primary); line-height:1.5;">
              <span data-i18n-key="spending_intelligence_kf_largest_no_desc" data-i18n-params='${JSON.stringify(paramsObj).replace(/'/g, "&apos;")}'></span>
            </div>
          </div>
        `;
    }
  }
  findingsHtml += `</div>`;

  // 5. AI Insights
  let aiHtml = `
      <h3 style="font-size:16px; font-weight:700; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_ai_insights"></h3>
      <div class="d-flex flex-column gap-2 mb-4">
  `;
  if (aiInsights.length > 0) {
    aiInsights.forEach(insight => {
        aiHtml += `
          <div style="display:flex; gap:12px; align-items:flex-start;">
            <i class="bi bi-stars" style="color:var(--bs-purple, #6f42c1); font-size:14px; margin-top:2px;"></i>
            <div style="font-size:13px; color:var(--text-primary); line-height:1.5;">
              <span data-i18n-key="${insight.key}" data-i18n-params='${JSON.stringify(insight.params).replace(/'/g, "&apos;")}'></span>
            </div>
          </div>
        `;
    });
  } else {
    aiHtml += `
      <div style="font-size:12px; color:rgba(123,147,201,0.6); line-height:1.5;">
        <i class="bi bi-info-circle me-1"></i> <span data-i18n="spending_intelligence_ai_insufficient"></span>
      </div>
    `;
  }
  aiHtml += `</div>`;

  // 6. Recommended Actions
  let recHtml = `
      <h3 style="font-size:16px; font-weight:700; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_recommended_actions"></h3>
      <div class="d-flex flex-column gap-2 mb-4">
  `;
  if (recommendedActions.length > 0) {
    recommendedActions.forEach(rec => {
        recHtml += `
          <div style="display:flex; gap:12px; align-items:flex-start;">
            <i class="bi bi-check-circle-fill" style="color:var(--bs-success, #198754); font-size:14px; margin-top:2px;"></i>
            <div style="font-size:13px; color:var(--text-primary); line-height:1.5;">
              <span data-i18n-key="${rec.key}" data-i18n-params='${JSON.stringify(rec.params).replace(/'/g, "&apos;")}'></span>
            </div>
          </div>
        `;
    });
  } else {
    recHtml += `
      <div style="font-size:12px; color:rgba(123,147,201,0.6); line-height:1.5;">
        <i class="bi bi-info-circle me-1"></i> <span data-i18n="spending_intelligence_ai_insufficient"></span>
      </div>
    `;
  }
  recHtml += `</div>`;

  // 7. Monthly Trend
  let trendHtml = `
    <h3 style="font-size:16px; font-weight:700; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_monthly_trend"></h3>
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
      <div class="card-body" style="padding:24px;">
  `;

  if (monthlyComparison.insufficient_history && months.length < 3) {
    trendHtml += `
      <div style="font-size:12px; color:rgba(123,147,201,0.6); margin-bottom:24px; line-height:1.5;">
        <i class="bi bi-info-circle me-1"></i> <span data-i18n="spending_intelligence_insufficient_history"></span>
      </div>
    `;
  }

  if (months.length > 0) {
    const maxAmount = Math.max(...months.map(m => m.total_egp));
    
    let barsHtml = '';
    months.forEach((m, idx) => {
      const heightPct = maxAmount > 0 ? (m.total_egp / maxAmount) * 100 : 0;
      const monthName = new Date(m.year, m.month - 1).toLocaleString('en-US', { month: 'short' });
      
      let diffHtml = '';
      if (idx > 0 && (!monthlyComparison.insufficient_history || months.length >= 3)) {
          const prevAmount = months[idx-1].total_egp;
          if (prevAmount > 0) {
              const diffPct = ((m.total_egp - prevAmount) / prevAmount) * 100.0;
              const isIncrease = diffPct > 0;
              const color = isIncrease ? 'var(--bs-danger)' : 'var(--bs-success)';
              const icon = isIncrease ? '▲' : '▼';
              diffHtml = `
                <div style="text-align:center;">
                  <div style="font-size:11px; color:${color}; font-weight:700;">${icon} ${Math.abs(diffPct).toFixed(1)}%</div>
                  <div style="font-size:9px; color:rgba(123,147,201,0.7); margin-top:2px;" data-i18n="spending_intelligence_compared_prev"></div>
                </div>
              `;
          }
      }

      barsHtml += `
        <div class="d-flex flex-column align-items-center" style="width:80px;">
          <div style="height:32px; display:flex; align-items:flex-end; justify-content:center;">
             ${diffHtml}
          </div>
          <div style="width:100%; height:120px; display:flex; align-items:flex-end; margin-top:4px; margin-bottom:12px;">
            <div style="width:100%; height:${heightPct}%; background:var(--bs-primary, #0d6efd); border-radius:6px 6px 0 0; transition:height 0.3s ease;"></div>
          </div>
          <div style="font-size:12px; color:rgba(123,147,201,0.8); margin-bottom:4px; text-align:center;">${monthName} ${m.year}</div>
          <div style="font-size:13px; font-weight:800; color:var(--text-primary); text-align:center; margin-bottom:2px;">${fmt(Number(m.total_egp).toFixed(2))}</div>
          <div style="font-size:10px; color:rgba(123,147,201,0.6); text-align:center;">${m.count} entries</div>
        </div>
      `;
    });
    
    trendHtml += `
      <div class="d-flex justify-content-center" style="gap:24px;">
        ${barsHtml}
      </div>
    `;
  } else {
    trendHtml += `<div style="text-align:center; padding:16px 0; color:var(--text-secondary);" data-i18n="spending_intelligence_no_data"></div>`;
  }
  
  trendHtml += `</div></div>`;

  pane.innerHTML = `
    <div style="max-width:1200px;">
      ${headerHtml}
      ${avgMonthlyHtml}
      <div class="row">
        <div class="col-md-7 mb-4">
          ${categoryHtml}
          ${donutHtml}
        </div>
        <div class="col-md-5 mb-4">
          ${findingsHtml}
          ${aiHtml}
          ${recHtml}
          ${trendHtml}
        </div>
      </div>
    </div>
  `;
  
  if (typeof applyTranslations === "function") applyTranslations();

  // Render Donut chart using the global helper defined in charts.js
  // Data is inherently sorted descending by the backend via ordering '-amount_egp'
  if (typeof _drawPieChart === "function" && catLabels.length > 0) {
      _drawPieChart("spendingDonutChart", catLabels, catValues);
  }
}

let _spendingIntelligenceLoaded = false;
let _spendingIntelligenceData = null;

async function loadSpendingIntelligence(force = false) {
  if (_spendingIntelligenceData && !force) {
    _renderSpendingIntelligence(_spendingIntelligenceData);
    _spendingIntelligenceLoaded = true;
    return;
  }

  _renderSpendingIntelligenceLoading();
  try {
    const response = await fetch("/api/financial-advisor/spending-intelligence/");
    if (!response.ok) {
      throw new Error("spending_intelligence_fetch_failed");
    }
    const payload = await response.json();
    _spendingIntelligenceData = payload;
    _renderSpendingIntelligence(payload);
    _spendingIntelligenceLoaded = true;
  } catch (error) {
    console.error(error);
    _renderSpendingIntelligenceError();
  }
}

window.loadSpendingIntelligence = loadSpendingIntelligence;
