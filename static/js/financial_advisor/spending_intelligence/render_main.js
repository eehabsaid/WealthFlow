"use strict";
// Spending intelligence: main render orchestrator. Split from the former
// monolithic spending_intelligence.js (200-line rule). Sibling files:
// - render_loading_error.js         Loading/error placeholder renderers
// - build_category_donut.js         Category breakdown + donut chart HTML
// - build_findings_insights_trend.js  Key findings + AI insights + monthly trend HTML
// - render_template.js              Final pane HTML assembly
// - loader.js                       loadSpendingIntelligence data fetch + dispatch
// Note: relies on _buildKeyFindingsHtml, defined in the sibling
// spending_intelligence_render.js (already under 200 lines, untouched).

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

  const { categoryHtml, catLabels, catValues, catPercentages, donutHtml } =
    buildSpendingCategoryDonutHtml({ categories, totalExpenses });

  const { findingsHtml, aiHtml, recHtml, trendHtml } = buildSpendingFindingsInsightsTrendHtml({
    payload,
    keyFindings,
    aiInsights,
    recommendedActions,
    months,
  });

  pane.innerHTML = buildSpendingIntelligencePaneHtml({
    headerHtml,
    avgMonthlyHtml,
    categoryHtml,
    donutHtml,
    findingsHtml,
    aiHtml,
    recHtml,
    trendHtml,
  });

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
    document.querySelectorAll(".cat-progress-bar").forEach((bar) => {
      bar.style.width = bar.getAttribute("data-target-width");
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
          datasets: [
            {
              data: catValues,
              backgroundColor: [
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
              ],
              borderWidth: 0,
              hoverOffset: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "78%",
          animation: {
            animateScale: true,
            animateRotate: true,
            duration: 1000,
            easing: "easeOutQuart",
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              padding: 12,
              titleFont: { size: 14, family: "Inter, sans-serif" },
              bodyFont: { size: 13, family: "Inter, sans-serif", weight: "bold" },
              callbacks: {
                label: function (context) {
                  let label = context.label || "";
                  if (label) label += ": ";
                  if (context.parsed !== null)
                    label += fmt(Number(context.parsed).toFixed(2)) + " EGP";
                  return label;
                },
              },
            },
          },
        },
      });
    }
  }
}
