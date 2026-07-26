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
    <div class="d-flex justify-content-between align-items-center mb-4 mt-2">
      <div style="font-size:15px; color:var(--text-secondary); line-height:1.6;" data-i18n="spending_intelligence_subtitle"></div>
    </div>
  `;

  // 1. Executive Summary (Main hero card)
  const totalExpenses = payload?.total_expenses_recorded || 0;
  const totalTx = payload?.total_transactions || 0;
  const monthsHistory = payload?.months_history || 0;
  const avgTxMonth = payload?.avg_transactions_per_month || 0;
  
  const periodStrObj = { months: monthsHistory };
  
  let avgMonthlyHtml = `
    <div class="card border-0 mb-5 fade-in-up" si-modern-card>
      <div class="card-body" style="padding:32px;">
        <div class="row align-items-center text-center text-md-start">
          
          <div class="col-6 col-md-3 mb-4 mb-md-0 border-end border-md-end-0 border-bottom-md-0 d-flex flex-column justify-content-center" style="border-color:var(--border-color) !important;" tabindex="0" title="Average amount spent per month">
            <div style="font-size:12px; font-weight:600; color:rgba(123,147,201,0.8); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;" data-i18n="spending_intelligence_avg_monthly"></div>
            <div style="font-size:32px; font-weight:800; color:var(--text-primary); margin-bottom:4px; letter-spacing:-0.5px;">${fmt(Number(payload?.avg_monthly_expenses || 0).toFixed(2))} <span style="font-size:14px; font-weight:600; color:var(--text-secondary);">EGP</span></div>
          </div>
          
          <div class="col-6 col-md-3 mb-4 mb-md-0 border-end border-md-end-0 border-bottom-md-0 d-none d-md-flex flex-column justify-content-center" style="border-color:var(--border-color) !important; border-left: 1px solid var(--border-color);" tabindex="0" title="Total accumulated expenses recorded">
            <div style="padding-left:16px;">
              <div style="font-size:12px; font-weight:600; color:rgba(123,147,201,0.8); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;" data-i18n="spending_intelligence_total_expenses"></div>
              <div style="font-size:28px; font-weight:700; color:var(--text-primary); margin-bottom:4px; letter-spacing:-0.5px;">${fmt(Number(totalExpenses).toFixed(2))} <span style="font-size:14px; font-weight:600; color:var(--text-secondary);">EGP</span></div>
            </div>
          </div>
          
          <!-- Mobile layout alternative -->
          <div class="col-6 d-md-none mb-4 d-flex flex-column justify-content-center" style="border-color:var(--border-color) !important;" tabindex="0" title="Total accumulated expenses recorded">
            <div style="font-size:12px; font-weight:600; color:rgba(123,147,201,0.8); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;" data-i18n="spending_intelligence_total_expenses"></div>
            <div style="font-size:24px; font-weight:700; color:var(--text-primary); margin-bottom:4px; letter-spacing:-0.5px;">${fmt(Number(totalExpenses).toFixed(2))} <span style="font-size:14px; font-weight:600; color:var(--text-secondary);">EGP</span></div>
          </div>

          <div class="col-6 col-md-3 border-end border-md-end-0 d-flex flex-column justify-content-center" style="border-color:var(--border-color) !important; border-left: 1px solid var(--border-color);" tabindex="0" title="Total number of recorded transactions">
            <div style="padding-left:16px;">
              <div style="font-size:12px; font-weight:600; color:rgba(123,147,201,0.8); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;" data-i18n="spending_intelligence_total_transactions"></div>
              <div style="font-size:28px; font-weight:700; color:var(--text-primary); margin-bottom:4px; letter-spacing:-0.5px;">${totalTx} <span style="font-size:14px; font-weight:600; color:var(--text-secondary);" data-i18n="spending_intelligence_tx"></span></div>
            </div>
          </div>
          
          <div class="col-6 col-md-3 d-flex flex-column justify-content-center" style="border-left: 1px solid var(--border-color);" tabindex="0" title="Average transactions recorded per month">
            <div style="padding-left:16px;">
              <div style="font-size:12px; font-weight:600; color:rgba(123,147,201,0.8); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;" data-i18n="spending_intelligence_avg_tx_per_month"></div>
              <div style="font-size:28px; font-weight:700; color:var(--text-primary); margin-bottom:4px; letter-spacing:-0.5px;">${fmt(Number(avgTxMonth).toFixed(1))} <span style="font-size:14px; font-weight:600; color:var(--text-secondary);" data-i18n="spending_intelligence_tx"></span></div>
              <div style="font-size:12px; color:var(--text-secondary); margin-top:4px;"><span data-i18n-key="spending_intelligence_period" data-i18n-params='${JSON.stringify(periodStrObj).replace(/'/g, "&apos;")}'></span></div>
          
        </div>
      </div>
    </div>
  `;

  // Add custom CSS for hover effects and animations if it doesn't exist
  if (!document.getElementById("si-custom-styles")) {
    const style = document.createElement("style");
    style.id = "si-custom-styles";
    style.innerHTML = `
      [si-modern-card] {
        background: var(--bg-secondary) !important;
        border: 1px solid rgba(123, 147, 201, 0.15) !important;
        border-radius: 16px !important;
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(8px);
      }
      .si-cat-row { transition: background-color 0.2s ease, transform 0.2s ease; border-radius: 8px; padding: 16px 12px; margin: 0 -12px; }
      .si-cat-row:hover { background-color: rgba(13, 110, 253, 0.03); transform: translateX(4px); }
      .fade-in-up { animation: fadeInUp 0.5s ease forwards; opacity: 0; transform: translateY(10px); }
      .delay-1 { animation-delay: 0.1s; }
      .delay-2 { animation-delay: 0.2s; }
      .delay-3 { animation-delay: 0.3s; }
      @keyframes fadeInUp { to { opacity: 1; transform: translateY(0); } }
    `;
    document.head.appendChild(style);
  }

  // Empty state handling for entire page
  if (categories.length === 0) {
    pane.innerHTML = `
      <div class="container-fluid" style="max-width:1200px;">
        ${headerHtml}
        ${avgMonthlyHtml}
        <div class="card border-0 mb-4 fade-in-up delay-1" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px; padding:64px 24px; text-align:center;">
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
    <h3 style="font-size:18px; font-weight:700; margin-top:24px; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_category_breakdown"></h3>
    <div class="card border-0 mb-4 flex-grow-1 fade-in-up delay-1" si-modern-card>
      <div class="card-body" style="padding:32px;">
  `;

  let catLabels = [];
  let catValues = [];
  let catPercentages = [];

  categories.forEach((cat, index) => {
    catLabels.push(cat.name); // Not translating category names in chart
    catValues.push(cat.amount_egp);
    catPercentages.push(cat.percentage.toFixed(1));

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
      <div class="si-cat-row d-flex align-items-start ${mbClass}" tabindex="0">
        <div style="width:40px; height:40px; border-radius:10px; background:rgba(123,147,201,0.05); border:1px solid rgba(123,147,201,0.1); display:flex; align-items:center; justify-content:center; font-size:20px; color:var(--text-primary); margin-right:20px;">
          <i class="bi ${biIcon}"></i>
        </div>
        <div class="flex-grow-1">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span style="font-weight:700; font-size:15px; color:var(--text-primary);">${cat.name}</span>
            <span style="font-weight:800; font-size:15px; color:var(--text-primary); text-align:right;">${fmt(Number(cat.amount_egp).toFixed(2))} EGP</span>
          </div>
          <div style="width:100%; height:6px; background:rgba(123,147,201,0.1); border-radius:3px; margin-bottom:10px; overflow:hidden;">
            <div class="cat-progress-bar" style="height:100%; width:0%; background:${barColor}; border-radius:3px; transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);" data-target-width="${cat.percentage}%"></div>
          </div>
          <div class="d-flex justify-content-between align-items-center">
            <div style="font-size:14px; font-weight:800; color:var(--text-secondary); opacity:1;">${cat.percentage.toFixed(1)}% <span style="font-weight:600; font-size:13px; color:var(--text-secondary); opacity:0.9; margin-left:8px;">&bull; ${cat.count} <span data-i18n="spending_intelligence_tx"></span></span></div>
            <div style="font-size:13px; font-weight:500; color:var(--text-secondary); opacity:1;"><span data-i18n="spending_intelligence_avg_per_tx"></span>: ${fmt(Number(catAvg).toFixed(2))} EGP</div>
          </div>
        </div>
      </div>
    `;
  });
  categoryHtml += `</div></div>`;

  // 3. Spending Distribution (Donut Chart)
  let donutHtml = `
    <h3 style="font-size:18px; font-weight:700; margin-top:24px; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_distribution"></h3>
    <div class="card border-0 mb-4 flex-grow-1 fade-in-up delay-1" si-modern-card>
      <div class="card-body d-flex flex-column" style="padding:32px;">
        <div style="position:relative; height:360px; width:100%; display:flex; justify-content:center; margin-bottom:48px;">
          <canvas id="spendingDonutChart" aria-label="Spending Distribution Chart" role="img"></canvas>
          <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); text-align:center; pointer-events:none;">
            <div style="font-size:14px; font-weight:600; color:var(--text-secondary); margin-bottom:4px; text-transform:uppercase; letter-spacing:0.5px;" data-i18n="spending_intelligence_total_spending"></div>
            <div style="font-size:24px; font-weight:800; color:var(--text-primary);">${fmt(Number(totalExpenses).toFixed(2))} <span style="font-size:16px;">EGP</span></div>
          </div>
        </div>
        <div class="row" style="margin-top:auto;">
  `;
  
  // Custom legend (2 columns)
  const colors = ["#0d6efd", "#198754", "#ffc107", "#dc3545", "#6f42c1", "#0dcaf0", "#fd7e14", "#20c997", "#6610f2", "#d63384"];
  catLabels.forEach((label, idx) => {
      if(idx > 7) return; 
      const color = colors[idx % colors.length];
      const pct = catPercentages[idx];
      donutHtml += `
        <div class="col-6 col-sm-6 mb-3">
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:14px; font-weight:500; color:var(--text-primary);" tabindex="0">
            <div style="display:flex; align-items:center; overflow:hidden;">
              <div style="min-width:12px; height:12px; border-radius:50%; background:${color}; margin-right:10px;"></div>
              <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${label}</span>
            </div>
            <span style="font-weight:800; color:var(--text-secondary); margin-left:8px;">${pct}%</span>
          </div>
        </div>
      `;
  });
  if (catLabels.length > 8) {
      donutHtml += `
        <div class="col-6 col-sm-6 mb-3">
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:14px; font-weight:500; color:var(--text-primary);" tabindex="0">
            <div style="display:flex; align-items:center; overflow:hidden;">
              <div style="min-width:12px; height:12px; border-radius:50%; background:#adb5bd; margin-right:10px;"></div>
              <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Others</span>
            </div>
          </div>
        </div>
      `;
  }
  donutHtml += `</div></div></div>`;

  // 4. Key Findings
  let findingsHtml = `
    <h3 style="font-size:18px; font-weight:700; margin-top:16px; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_key_findings"></h3>
    <div class="card border-0 mb-5 fade-in-up delay-2" si-modern-card>
      <div class="card-body d-flex flex-column justify-content-center" style="padding:32px; gap:20px;">
  `;

  if (keyFindings.most_frequent) {
    const mf = keyFindings.most_frequent;
    const catAvg = mf.count > 0 ? (mf.avg_per_tx) : 0;
    const catNameHtml = `<b>${mf.name}</b>`;
    const paramsObj = { category: catNameHtml, count: mf.count, avg: `<b>${fmt(Number(catAvg).toFixed(2))}</b>` };
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
    const dateHtml = `<b>${le.date}</b>`;
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

  // 5. AI Insights & 6. Recommended Actions
  let aiHtml = `
    <div class="row mb-5">
      <div class="col-md-6 mb-5 mb-md-0 d-flex flex-column fade-in-up delay-2">
        <h3 style="font-size:18px; font-weight:700; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_ai_insights"></h3>
        <div class="card border-0 flex-grow-1" si-modern-card>
          <div class="card-body d-flex flex-column justify-content-center" style="padding:32px; gap:20px;">
  `;
  if (aiInsights.length > 0) {
    aiInsights.forEach(insight => {
        aiHtml += `
          <div style="display:flex; gap:16px; align-items:flex-start; padding-bottom:16px; border-bottom:1px solid rgba(123,147,201,0.1);">
            <div style="background:rgba(111, 66, 193, 0.1); width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                <i class="bi bi-stars" style="color:var(--bs-purple, #6f42c1); font-size:14px;"></i>
            </div>
            <div style="font-size:14px; color:var(--text-primary); line-height:1.6; margin-top:4px;">
              <span data-i18n-key="${insight.key}" data-i18n-params='${JSON.stringify(insight.params).replace(/'/g, "&apos;")}'></span>
            </div>
          </div>
        `;
    });
  } else {
    aiHtml += `
      <div style="font-size:14px; color:rgba(123,147,201,0.6); line-height:1.6; text-align:center;">
        <i class="bi bi-stars mb-3" style="font-size:28px; display:block; opacity:0.5;"></i>
        <span data-i18n="spending_intelligence_ai_insufficient"></span>
      </div>
    `;
  }
  aiHtml += `</div></div></div>`;

  // Priority Badges Helper
  const getPriorityBadgeHtml = (priority) => {
      let colorClass = "bg-secondary";
      let key = "spending_intelligence_priority_low";
      if(priority === "High") { colorClass = "bg-danger"; key = "spending_intelligence_priority_high"; }
      else if(priority === "Medium") { colorClass = "bg-warning text-dark"; key = "spending_intelligence_priority_medium"; }
      
      return `<span class="badge ${colorClass}" style="font-size:10px; font-weight:600; padding:4px 8px; border-radius:4px;" data-i18n="${key}"></span>`;
  };

  let recHtml = `
      <div class="col-md-6 d-flex flex-column fade-in-up delay-2">
        <h3 style="font-size:18px; font-weight:700; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_recommended_actions"></h3>
        <div class="card border-0 flex-grow-1" si-modern-card>
          <div class="card-body d-flex flex-column justify-content-center" style="padding:32px; gap:20px;">
  `;
  if (recommendedActions.length > 0) {
    // Sort recommendations by priority (High -> Medium -> Low)
    const sortedRecs = [...recommendedActions].sort((a, b) => {
        const pMap = { "High": 3, "Medium": 2, "Low": 1 };
        return (pMap[b.priority] || 1) - (pMap[a.priority] || 1);
    });

    sortedRecs.forEach(rec => {
        const catNameHtml = rec.params.category ? `<b>${rec.params.category}</b>` : undefined;
        let newParams = {...rec.params};
        if(catNameHtml) newParams.category = catNameHtml;
        const priorityBadge = getPriorityBadgeHtml(rec.priority || "Low");

        recHtml += `
          <div style="display:flex; flex-direction:column; gap:8px; padding-bottom:16px; border-bottom:1px solid rgba(123,147,201,0.1);">
            <div class="d-flex justify-content-between align-items-center">
                <div style="display:flex; gap:12px; align-items:center;">
                    <i class="bi bi-check-circle-fill" style="color:var(--bs-success, #198754); font-size:16px;"></i>
                    <span style="font-size:12px; font-weight:700; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Action Item</span>
                </div>
                ${priorityBadge}
            </div>
            <div style="font-size:14px; color:var(--text-primary); line-height:1.6; padding-left:28px;">
              <span data-i18n-html-key="${rec.key}" data-i18n-params='${JSON.stringify(newParams).replace(/'/g, "&apos;")}'></span>
            </div>
          </div>
        `;
    });
  } else {
    recHtml += `
      <div style="font-size:14px; color:rgba(123,147,201,0.6); line-height:1.6; text-align:center;">
        <i class="bi bi-check-circle mb-3" style="font-size:28px; display:block; opacity:0.5;"></i>
        <span data-i18n="spending_intelligence_ai_insufficient"></span>
      </div>
    `;
  }
  recHtml += `</div></div></div></div>`;

  // 7. Monthly Trend
  const registeredCategories = payload?.registered_categories || [];
  const hasUncategorized = payload?.has_uncategorized || false;

  let catSelectOptions = `<option value="all" data-i18n="all_categories">All Categories</option>`;
  registeredCategories.forEach(cat => {
    catSelectOptions += `<option value="${cat.id}">${cat.icon ? cat.icon + ' ' : ''}${cat.name}</option>`;
  });
  if (hasUncategorized) {
    catSelectOptions += `<option value="uncategorized" data-i18n="spending_intelligence_uncategorized">Uncategorized</option>`;
  }

  let trendHtml = `
    <div class="d-flex justify-content-between align-items-center mt-4 mb-3 flex-wrap gap-2">
      <h3 style="font-size:18px; font-weight:700; margin:0; color:var(--text-primary);" data-i18n="spending_intelligence_monthly_trend"></h3>
      <div style="min-width:200px;">
        <select id="si-monthly-trend-category-filter" class="form-select form-select-sm" style="background:var(--bg-secondary); color:var(--text-primary); border:1px solid var(--border-color); border-radius:8px; font-size:13px; font-weight:500; cursor:pointer;">
          ${catSelectOptions}
        </select>
      </div>
    </div>
    <div class="card border-0 mb-5 fade-in-up delay-3" si-modern-card>
      <div class="card-body" style="padding:32px;" id="si-monthly-trend-card-body">
      </div>
    </div>
  `;

  pane.innerHTML = `
    <div class="container-fluid" style="max-width:1200px;">
      ${headerHtml}
      ${avgMonthlyHtml}
      <div class="row">
        <div class="col-lg-7 mb-4 d-flex flex-column">
          <div class="flex-grow-1 d-flex flex-column">
             ${categoryHtml}
          </div>
        </div>
        <div class="col-lg-5 mb-4 d-flex flex-column">
          <div class="flex-grow-1 d-flex flex-column">
             ${donutHtml}
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-lg-12">
            ${findingsHtml}
        </div>
      </div>
      ${aiHtml}
      ${recHtml}
      <div class="row">
        <div class="col-12">
            ${trendHtml}
        </div>
      </div>
    </div>
  `;
  
  if (typeof applyTranslations === "function") applyTranslations();

  _renderMonthlyTrendBars(payload, "all");

  const filterSelect = document.getElementById("si-monthly-trend-category-filter");
  if (filterSelect) {
    filterSelect.addEventListener("change", (e) => {
      _renderMonthlyTrendBars(payload, e.target.value);
    });
  }

  // Trigger progress bar animations
  setTimeout(() => {
      document.querySelectorAll('.cat-progress-bar').forEach(bar => {
          bar.style.width = bar.getAttribute('data-target-width');
      });
  }, 100);

  // Render Donut chart using the global helper defined in charts.js
  if (typeof window.Chart !== "undefined" && catLabels.length > 0) {
      const canvas = document.getElementById("spendingDonutChart");
      if (canvas) {
          // Disable default legend to use our custom HTML legend
          new window.Chart(canvas, {
              type: "doughnut",
              data: {
                  labels: catLabels,
                  datasets: [{
                      data: catValues,
                      backgroundColor: ["#0d6efd", "#198754", "#ffc107", "#dc3545", "#6f42c1", "#0dcaf0", "#fd7e14", "#20c997", "#6610f2", "#d63384"],
                      borderWidth: 0,
                      hoverOffset: 6
                  }]
              },
              options: {
                  responsive: true,
                  maintainAspectRatio: false,
                  cutout: '78%',
                  animation: {
                      animateScale: true,
                      animateRotate: true,
                      duration: 1000,
                      easing: 'easeOutQuart'
                  },
                  plugins: {
                      legend: { display: false },
                      tooltip: {
                          padding: 12,
                          titleFont: { size: 14, family: 'Inter, sans-serif' },
                          bodyFont: { size: 13, family: 'Inter, sans-serif', weight: 'bold' },
                          callbacks: {
                              label: function(context) {
                                  let label = context.label || '';
                                  if (label) label += ': ';
                                  if (context.parsed !== null) label += fmt(Number(context.parsed).toFixed(2)) + ' EGP';
                                  return label;
                              }
                          }
                      }
                  }
              }
          });
      }
  }
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
    catMonths.forEach(m => {
      catMonthMap[`${m.year}-${m.month}`] = m;
    });

    barsData = months.map(m => {
      const match = catMonthMap[`${m.year}-${m.month}`];
      return {
        year: m.year,
        month: m.month,
        total_egp: match ? match.total_egp : 0.0,
        count: match ? match.count : 0
      };
    });
  }

  let html = '';

  if (monthlyComparison.insufficient_history && months.length < 3) {
    html += `
      <div style="background:rgba(123,147,201,0.05); border:1px solid rgba(123,147,201,0.1); border-radius:8px; padding:16px; font-size:13px; color:var(--text-secondary); margin-bottom:32px; line-height:1.6; text-align:center;">
        <i class="bi bi-info-circle me-1" style="font-size:16px;"></i> <span data-i18n="spending_intelligence_insufficient_history"></span>
      </div>
    `;
  }

  if (barsData.length > 0) {
    const maxAmount = Math.max(...barsData.map(m => m.total_egp));

    let barsHtml = '';
    barsData.forEach((m, idx) => {
      const heightPct = maxAmount > 0 ? (m.total_egp / maxAmount) * 100 : 0;
      const monthName = new Date(m.year, m.month - 1).toLocaleString('en-US', { month: 'short' });

      let diffHtml = '';
      if (idx > 0 && barsData.length >= 3) {
        const prevAmount = barsData[idx - 1].total_egp;
        if (prevAmount > 0) {
          const diffPct = ((m.total_egp - prevAmount) / prevAmount) * 100.0;
          const isIncrease = diffPct > 0;
          const color = isIncrease ? 'var(--bs-danger)' : 'var(--bs-success)';
          const icon = isIncrease ? '▲' : '▼';
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
          <div style="height:36px; display:flex; align-items:flex-end; justify-content:center;">
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
