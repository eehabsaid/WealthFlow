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

  const {
    categories,
    keyFindings,
    months,
    aiInsights,
    recommendedActions,
    headerHtml,
    avgMonthlyHtml,
    totalExpenses,
  } = _buildSpendingIntelligenceHeaderFragments(payload);

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

  const { categoryHtml, catLabels, catValues, donutHtml } = buildSpendingCategoryDonutHtml({
    categories,
    totalExpenses,
  });

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
                    label += fmt(Number(context.parsed).toFixed(2)) + " " + baseCurrencyCode();
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
