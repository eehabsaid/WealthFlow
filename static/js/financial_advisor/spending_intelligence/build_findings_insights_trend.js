"use strict";
// Spending intelligence: key findings + AI insights + recommended actions +
// monthly trend HTML builder.
// Relies on _buildKeyFindingsHtml, defined in the sibling
// spending_intelligence_render.js (already under 200 lines, untouched).

function buildSpendingFindingsInsightsTrendHtml(ctx) {
  const { payload, keyFindings, aiInsights, recommendedActions } = ctx;
  // 4. Key Findings
  let findingsHtml = _buildKeyFindingsHtml(keyFindings);

  // 5. AI Insights & 6. Recommended Actions
  let aiHtml = `
    <div class="row mb-5">
      <div class="col-md-6 mb-5 mb-md-0 d-flex flex-column fade-in-up delay-2">
        <h3 style="font-size:18px; font-weight:700; margin-bottom:16px; color:var(--text-primary);" data-i18n="spending_intelligence_ai_insights"></h3>
        <div class="card border-0 flex-grow-1" si-modern-card>
          <div class="card-body d-flex flex-column justify-content-center" style="padding:32px; gap:20px;">
  `;
  if (aiInsights.length > 0) {
    aiInsights.forEach((insight) => {
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
    if (priority === "High") {
      colorClass = "bg-danger";
      key = "spending_intelligence_priority_high";
    } else if (priority === "Medium") {
      colorClass = "bg-warning text-dark";
      key = "spending_intelligence_priority_medium";
    }

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
      const pMap = { High: 3, Medium: 2, Low: 1 };
      return (pMap[b.priority] || 1) - (pMap[a.priority] || 1);
    });

    sortedRecs.forEach((rec) => {
      const catNameHtml = rec.params.category ? `<b>${rec.params.category}</b>` : undefined;
      let newParams = { ...rec.params };
      if (catNameHtml) newParams.category = catNameHtml;
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
  registeredCategories.forEach((cat) => {
    catSelectOptions += `<option value="${cat.id}">${cat.icon ? cat.icon + " " : ""}${cat.name}</option>`;
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
  return { findingsHtml, aiHtml, recHtml, trendHtml };
}
