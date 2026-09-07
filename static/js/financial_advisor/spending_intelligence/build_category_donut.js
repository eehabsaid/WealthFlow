"use strict";
// Spending intelligence: category breakdown + donut chart HTML builder.

function buildSpendingCategoryDonutHtml(ctx) {
  const { categories, totalExpenses } = ctx;
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
    const catAvg = cat.count > 0 ? cat.amount_egp / cat.count : 0;

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
  const colors = [
    "#0d6efd",
    "#198754",
    "#ffc107",
    "#dc3545",
    "#6f42c1",
    "#0dcaf0",
    "#fd7e14",
    "#20c997",
    "#6610f2",
    "#d63384",
  ];
  catLabels.forEach((label, idx) => {
    if (idx > 7) return;
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
  return { categoryHtml, catLabels, catValues, catPercentages, donutHtml };
}
