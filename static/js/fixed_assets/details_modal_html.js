"use strict";
// Fixed asset modal — main HTML builder (header/body wrapper, tab nav
// assembly, tab-content panes, footer). Split out of details_modal.js
// (200-line backlog). Bare global.
// ════════════════════════════════════════════════════════════════════════════

function buildFixedAssetModalHtml(assetId, modalTitleKey, modalTitleDefault) {
  const html = `
        <div class="modal-header">
            <h5 class="modal-title fixed-assets-heading" data-i18n="${modalTitleKey}">${modalTitleDefault}</h5>
            <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
        </div>
        <div class="modal-body" style="max-height: 75vh; overflow-y: auto; overflow-x: hidden; padding: 1.5rem;">
          <form id="fixedAssetForm">

${buildFixedAssetModalTabsNavPart1()}
${buildFixedAssetModalTabsNavPart2()}
              <div class="tab-content" id="fixedAssetTabsContent">

                  ${renderGeneralTab()}

                  ${renderPropertyTab()}

                  ${renderVehicleTab()}

                  ${renderGoldTab()}

                  ${renderOtherDetailsTab()}

                  ${renderPhotosTab()}

                  ${renderRenovationTab()}

                    ${renderFurnitureTab()}

                    ${renderValuationTab()}

                    ${renderMaintenanceTab()}

                    ${renderInsuranceTab()}

                    ${renderMortgageTab()}

                    ${renderRentalTab()}

                    ${renderSaleTab()}

                    ${renderDocumentsTab()}

              </div> <!-- End Tab Content -->

          </form>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="cancel">Cancel</button>
            <button class="btn-primary-custom" onclick="saveFixedAsset(${assetId})" data-i18n="save">Save</button>
        </div>
    `;

  return html;
}
