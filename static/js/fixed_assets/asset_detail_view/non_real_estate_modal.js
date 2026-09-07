"use strict";
// Builds and shows the simpler asset-detail modal for non-real-estate asset
// types (vehicle, gold, other). Mirrors the original inline branch of
// showFixedAssetDetails (200-line rule split); calls hideLoading() itself,
// matching the original control flow (entry.js also runs its own
// try/finally hideLoading(), same as before the split).

function buildAndShowNonRealEstateModal(ctx) {
  const { asset, photos, sale, gainValue, gainClass } = ctx;
  const {
    coreTabLabel,
    coreTabPane,
    extraVehicleTabs,
    extraVehiclePanes,
    extraValuationTab,
    extraValuationPane,
  } = buildNonRealEstateCoreTabParts(ctx);

      const html = `
      <div class="modal-header border-0 pb-0">
          <h5 class="modal-title fixed-assets-heading" data-i18n="asset_details">Asset Details</h5>
          <button type="button" class="btn-close btn-close-white" onclick="handleAssetWindowClose()"></button>
      </div>
      <div class="modal-body asset-modal-body p-0">
        <div class="p-4">
          <div class="asset-detail-header mb-4">
            <h3 class="asset-title mb-1 fixed-assets-heading">${asset.name || "-"}</h3>
            <span class="badge rounded-pill asset-type-badge" data-i18n="${fixedAssetTypeToI18nKey(asset.asset_type)}">${asset.asset_type || "-"}</span>
          </div>
          <ul class="nav nav-pills nav-fill mb-4 asset-detail-tabs" role="tablist">
            <li class="nav-item" role="presentation"><button class="nav-link active" id="asset-general-tab" data-bs-toggle="tab" data-bs-target="#asset-general-pane" type="button" role="tab" data-i18n="general">General</button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-core-tab" data-bs-toggle="tab" data-bs-target="#asset-core-pane" type="button" role="tab">${coreTabLabel}</button></li>
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-photos-tab" data-bs-toggle="tab" data-bs-target="#asset-photos-pane" type="button" role="tab" data-i18n="photos">Photos</button></li>
            ${extraVehicleTabs}
            ${extraValuationTab}
            <li class="nav-item" role="presentation"><button class="nav-link" id="asset-sale-tab" data-bs-toggle="tab" data-bs-target="#asset-sale-pane" type="button" role="tab" data-i18n="sale">Sale</button></li>
          </ul>
          <div class="tab-content" id="assetDetailsTabsContent">
            <div class="tab-pane fade show active" id="asset-general-pane" role="tabpanel" aria-labelledby="asset-general-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                <div class="row g-3">
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_price_egp">Purchase Price</span><span class="value">${fmt(asset.purchase_price)}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="current_market_value">Current Market Value</span><span class="value ${gainClass}">${fmt(asset.current_market_value)}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="purchase_date">Purchase Date</span><span class="value">${formatDate(asset.purchase_date) || "-"}</span></div></div>
                  <div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="gain_loss">Gain / Loss</span><span class="value ${gainClass}">${fmt(gainValue)}</span></div></div>
                  <div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${asset.notes || "-"}</span></div></div>
                </div>
              </div></div>
            </div>
            <div class="tab-pane fade" id="asset-core-pane" role="tabpanel" aria-labelledby="asset-core-tab">${coreTabPane}</div>
            <div class="tab-pane fade" id="asset-photos-pane" role="tabpanel" aria-labelledby="asset-photos-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                <div id="assetMainPhotoContainer" class="asset-main-photo-container mb-3">
                  ${photos.length ? `<img id="assetMainPhoto" src="${photos[0].url}" alt="Asset photo" class="img-fluid" style="max-height:100%;max-width:100%;cursor:pointer;" />` : `<div class="text-center" data-i18n="no_property_photos">No photos available</div>`}
                </div>
                <div class="asset-photo-grid">${
                  photos.length
                    ? photos
                        .slice(1)
                        .map(
                          (photo, index) =>
                            `<button type="button" class="btn btn-sm asset-photo-thumbnail p-0" data-url="${photo.url}" aria-label="Photo ${index + 2}"><img src="${photo.url}" alt="Thumbnail ${index + 2}" /></button>`
                        )
                        .join("")
                    : ""
                }</div>
              </div></div>
            </div>
            ${extraVehiclePanes}
            ${extraValuationPane}
            <div class="tab-pane fade" id="asset-sale-pane" role="tabpanel" aria-labelledby="asset-sale-tab">
              <div class="card border-0 shadow-sm" style="background:var(--bg-secondary);"><div class="card-body p-4">
                ${sale ? `<div class="row g-3"><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="sale_date">Sale Date</span><span class="value">${formatDate(sale.sale_date) || "-"}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="sale_price_egp">Sale Price</span><span class="value">${fmt(sale.sale_price)}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="selling_expenses_egp">Selling Expenses</span><span class="value">${fmt(sale.selling_expenses)}</span></div></div><div class="col-md-6"><div class="asset-attribute-row"><span class="label" data-i18n="net_sale_amount">Net Sale Amount</span><span class="value">${fmt(sale.net_sale_amount)}</span></div></div><div class="col-12"><div class="asset-attribute-row"><span class="label" data-i18n="notes">Notes</span><span class="value">${sale.notes || "-"}</span></div></div></div>` : `<div class="text-center" data-i18n="no_data">No data available</div>`}
              </div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer"><button class="btn-secondary-custom" onclick="handleAssetWindowClose()" data-i18n="close">Close</button></div>
      <div id="assetPhotoOverlay" class="position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-90 d-none" style="z-index:2000;"><div class="d-flex h-100 align-items-center justify-content-center"><img id="assetFullscreenImage" src="" alt="Fullscreen asset photo" class="img-fluid rounded" style="max-height:90%; max-width:90%;" /></div></div>
      `;

      showModal(html);
      applyTranslations();

      const mainPhoto = document.getElementById("assetMainPhoto");
      const photoOverlay = document.getElementById("assetPhotoOverlay");
      const fullscreenImage = document.getElementById("assetFullscreenImage");
      if (mainPhoto) {
        mainPhoto.addEventListener("click", () => {
          fullscreenImage.src = mainPhoto.src;
          photoOverlay?.classList.remove("d-none");
        });
      }
      photoOverlay?.addEventListener("click", () => {
        photoOverlay.classList.add("d-none");
        fullscreenImage.src = "";
      });

      const assetPhotoThumbnails = document.querySelectorAll(".asset-photo-thumbnail");
      assetPhotoThumbnails.forEach((thumb) => {
        thumb.addEventListener("click", (e) => {
          const url = e.currentTarget.dataset.url;
          const mainImg = document.getElementById("assetMainPhoto");
          if (mainImg) mainImg.src = url;
          assetPhotoThumbnails.forEach((item) => item.classList.remove("active"));
          e.currentTarget.classList.add("active");
        });
      });
      hideLoading();
      return;
}
