"use strict";
// Real-estate asset detail modal: Furniture + Valuation History + Mortgage +
// Rental + Sale tab panes (orchestrator). Fragment builders split into
// tabs/furniture_pane.js, tabs/valuation_pane.js, tabs/mortgage_rental_panes.js,
// and tabs/sale_pane_and_footer.js (200-line rule). Do not edit directly.

function buildFurnitureValuationMortgageRentalSaleTabsHtml(ctx) {
  const { asset, furniture, valuationHistory, sale, mortgage, rental } = ctx;
  return `
                  ${buildFurniturePaneHtml(furniture, asset)}
                  ${buildValuationHistoryPaneHtml(valuationHistory)}
                  ${buildMortgageRentalPanesHtml(mortgage, rental)}${buildSalePaneAndFooterHtml(sale)}`;
}
