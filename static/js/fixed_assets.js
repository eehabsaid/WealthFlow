'use strict';

function renderFixedAssetsList(assets) {

    const container = document.getElementById("fixedAssetsContainer");

    if (!assets.length) {

        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-house-door" style="font-size:60px"></i>
                <h3 data-i18n="no_fixed_assets"></h3>
                <p data-i18n="no_fixed_assets_desc"></p>

                <button class="btn-primary-custom mt-3"
                        onclick="showFixedAssetModal()">
                    <i class="bi bi-plus-lg"></i>
                    <span data-i18n="add_first_property"></span>
                </button>
            </div>
        `;

        applyTranslations();
        return;
    }

    container.innerHTML = assets.map(asset => `

        <div class="kpi-card mb-3">

            <div style="display:flex;justify-content:space-between;align-items:center">

                <div>

                    <h5>${asset.name}</h5>

                    <small class="text-muted">
                        ${asset.asset_type}
                    </small>

                </div>

                <div>

                    <button class="btn btn-sm btn-outline-primary"
                            onclick="showFixedAssetModal(${asset.id})">

                        <i class="bi bi-pencil"></i>

                    </button>

                </div>

            </div>

            <hr>

            <div class="row">

                <div class="col-md-4">

                    <div class="kpi-label"
                         data-i18n="purchase_price">
                    </div>

                    <div class="kpi-value">
                        ${fmt(asset.purchase_price)}
                    </div>

                </div>

                <div class="col-md-4">

                    <div class="kpi-label"
                         data-i18n="current_market_value">
                    </div>

                    <div class="kpi-value">
                        ${fmt(asset.current_market_value)}
                    </div>

                </div>

                <div class="col-md-4">

                    <div class="kpi-label"
                         data-i18n="valuation_source">
                    </div>

                    <div class="kpi-value">
                        ${asset.valuation_source}
                    </div>

                </div>

            </div>

        </div>

    `).join("");

    applyTranslations();

}

function renderFixedAssetsList(assets) {
    const container = document.getElementById('fixedAssetsContainer');

    if (!assets.length) {
        container.innerHTML = `
            <div class="empty-state">
                <h4 data-i18n="no_fixed_assets"></h4>
            </div>
        `;
        applyTranslations();
        return;
    }

    container.innerHTML = "";
}

function showFixedAssetModal(id = null) {

    showToast("Coming next...");

}