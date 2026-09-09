"use strict";
// Spending intelligence: final pane HTML assembly (combines all the
// pre-built section HTML into the full page layout).

function buildSpendingIntelligencePaneHtml(ctx) {
  const {
    headerHtml,
    avgMonthlyHtml,
    categoryHtml,
    donutHtml,
    findingsHtml,
    aiHtml,
    recHtml,
    trendHtml,
  } = ctx;
  return `
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
}
