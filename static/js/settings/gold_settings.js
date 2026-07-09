"use strict";
// Gold settings (types and purities) management
// This file is part of the settings module. Do not edit directly.

async function renderGoldSettings() {
    const [typesRes, puritiesRes, settingsRes] = await Promise.all([
        fetch('/api/settings/gold-types/'),
        fetch('/api/settings/gold-purities/'),
        fetch('/api/settings/'),
    ]);

    const typeData = await typesRes.json();
    const purityData = await puritiesRes.json();
    const settingsData = await settingsRes.json();

    const types = typeData.items || [];
    const purities = purityData.items || [];
    const currentRateMap = settingsData?.settings?.property_valuation_rate_map || '';
    const providerOrder = settingsData?.settings?.property_valuation_provider_order || 'external_api,configured_market_rate';
    const externalEnabled = (settingsData?.settings?.property_valuation_external_enabled || 'false') === 'true';
    const externalUrl = settingsData?.settings?.property_valuation_external_url || '';
    const externalResultPath = settingsData?.settings?.property_valuation_external_result_path || 'estimated_price';
    const externalTimeout = settingsData?.settings?.property_valuation_external_timeout_secs || '8';
    const externalHeaders = settingsData?.settings?.property_valuation_external_headers || '';

    const typeRows = types.map(item => `
        <tr>
            <td>${item.name}</td>
            <td>${item.order ?? 0}</td>
            <td><span style="color:${item.is_active ? 'var(--accent-green)' : 'var(--accent-red)'}" data-i18n="${item.is_active ? 'active' : 'inactive'}">${item.is_active ? t('active', 'Active') : t('inactive', 'Inactive')}</span></td>
            <td>
                <button class="btn-icon" onclick="showGoldTypeModal(${item.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="disableGoldType(${item.id})"><i class="bi bi-slash-circle"></i></button>
            </td>
        </tr>
    `).join('');

    const purityRows = purities.map(item => `
        <tr>
            <td>${item.key}</td>
            <td>${item.label}</td>
            <td class="num-fmt" data-value="${item.cashback_per_gram || 0}">${fmt(item.cashback_per_gram || 0)}</td>
            <td>${item.order ?? 0}</td>
            <td><span style="color:${item.is_active ? 'var(--accent-green)' : 'var(--accent-red)'}" data-i18n="${item.is_active ? 'active' : 'inactive'}">${item.is_active ? t('active', 'Active') : t('inactive', 'Inactive')}</span></td>
            <td>
                <button class="btn-icon" onclick="showGoldPurityModal(${item.id})"><i class="bi bi-pencil"></i></button>
                <button class="btn-icon del" onclick="disableGoldPurity(${item.id})"><i class="bi bi-slash-circle"></i></button>
            </td>
        </tr>
    `).join('');

    document.getElementById('settingsContent').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-weight:700;color:var(--text-primary)" data-i18n="tab_gold_settings">${t('tab_gold_settings', 'Gold Settings')}</div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="gold_types">${t('gold_types', 'Gold Types')}</div>
                <button class="btn-primary-custom" onclick="showGoldTypeModal(null)" data-i18n="add_gold_type">${t('add_gold_type', 'Add Gold Type')}</button>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="gold_type">${t('gold_type', 'Gold Type')}</th>
                            <th data-i18n="order">${t('order', 'Order')}</th>
                            <th data-i18n="active">${t('active', 'Active')}</th>
                            <th data-i18n="actions">${t('actions', 'Actions')}</th>
                        </tr>
                    </thead>
                    <tbody>${typeRows}</tbody>
                </table>
            </div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="gold_purities">${t('gold_purities', 'Gold Purities')}</div>
                <button class="btn-primary-custom" onclick="showGoldPurityModal(null)" data-i18n="add_gold_purity">${t('add_gold_purity', 'Add Gold Purity')}</button>
            </div>
            <div style="margin-bottom:8px;color:var(--text-muted);font-size:12px;" data-i18n="gold_purities_cashback_hint">${t('gold_purities_cashback_hint', 'Cashback per gram here is used in all gold valuation calculations across the app.')}</div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th data-i18n="gold_purity_key">${t('gold_purity_key', 'Purity Key')}</th>
                            <th data-i18n="gold_purity_label">${t('gold_purity_label', 'Purity Label')}</th>
                            <th data-i18n="cashback_per_gram">${t('cashback_per_gram', 'Cashback per Gram')}</th>
                            <th data-i18n="order">${t('order', 'Order')}</th>
                            <th data-i18n="active">${t('active', 'Active')}</th>
                            <th data-i18n="actions">${t('actions', 'Actions')}</th>
                        </tr>
                    </thead>
                    <tbody>${purityRows}</tbody>
                </table>
            </div>
        </div>

        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-top:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:12px;flex-wrap:wrap;">
                <div>
                    <div style="font-weight:600;color:var(--text-secondary)" data-i18n="property_valuation_settings">${t('property_valuation_settings', 'Property Valuation Settings')}</div>
                    <div style="font-size:12px;color:var(--text-muted)" data-i18n="property_valuation_rate_map_hint">${t('property_valuation_rate_map_hint', 'Provide JSON with by_city, by_governorate, and optional default EGP-per-square-meter rates.')}</div>
                </div>
                <button class="btn-primary-custom" onclick="savePropertyValuationSettings()" data-i18n="save_property_valuation_settings">${t('save_property_valuation_settings', 'Save Valuation Settings')}</button>
            </div>
            <div class="row g-3" style="margin-bottom:12px;">
                <div class="col-md-4">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="property_valuation_provider_order">${t('property_valuation_provider_order', 'Provider Order')}</label>
                    <select id="propertyValuationProviderOrder" class="form-select">
                        <option value="external_api,configured_market_rate" ${providerOrder === 'external_api,configured_market_rate' ? 'selected' : ''}>${t('provider_order_external_first', 'External API then Configured Rate')}</option>
                        <option value="configured_market_rate,external_api" ${providerOrder === 'configured_market_rate,external_api' ? 'selected' : ''}>${t('provider_order_configured_first', 'Configured Rate then External API')}</option>
                        <option value="configured_market_rate" ${providerOrder === 'configured_market_rate' ? 'selected' : ''}>${t('provider_order_configured_only', 'Configured Rate Only')}</option>
                        <option value="external_api" ${providerOrder === 'external_api' ? 'selected' : ''}>${t('provider_order_external_only', 'External API Only')}</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="property_valuation_external_enabled">${t('property_valuation_external_enabled', 'External Enabled')}</label>
                    <select id="propertyValuationExternalEnabled" class="form-select">
                        <option value="true" ${externalEnabled ? 'selected' : ''}>${t('yes', 'Yes')}</option>
                        <option value="false" ${!externalEnabled ? 'selected' : ''}>${t('no', 'No')}</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="property_valuation_external_timeout">${t('property_valuation_external_timeout', 'External Timeout (seconds)')}</label>
                    <input id="propertyValuationExternalTimeout" class="form-control" type="number" min="1" step="1" value="${externalTimeout}">
                </div>
                <div class="col-md-3">
                    <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="property_valuation_external_result_path">${t('property_valuation_external_result_path', 'External Result Path')}</label>
                    <input id="propertyValuationExternalResultPath" class="form-control" type="text" value="${externalResultPath}" placeholder="estimated_price">
                </div>
            </div>
            <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="property_valuation_external_url">${t('property_valuation_external_url', 'External API URL Template')}</label>
            <input id="propertyValuationExternalUrl" class="form-control" type="text" value="${externalUrl}" placeholder="https://api.example.com/valuation?city={city}&area={area_m2}">

            <label style="display:block;margin-top:12px;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="property_valuation_external_headers">${t('property_valuation_external_headers', 'External Headers (JSON)')}</label>
            <textarea id="propertyValuationExternalHeaders" class="form-control" rows="4" spellcheck="false" placeholder='{"Authorization":"Bearer token"}'>${externalHeaders}</textarea>

            <label style="display:block;margin-bottom:8px;color:var(--text-secondary);font-weight:600;" data-i18n="property_valuation_rate_map">${t('property_valuation_rate_map', 'Property Valuation Rate Map')}</label>
            <textarea id="propertyValuationRateMap" class="form-control" rows="8" spellcheck="false" placeholder='{"by_city":{"Cairo":42000},"by_governorate":{"Giza":35000},"default":30000}'>${currentRateMap}</textarea>
        </div>
    `;

    applyTranslations();
}

async function showGoldTypeModal(itemId) {
    let item = null;
    if (itemId) {
        const res = await fetch('/api/settings/gold-types/');
        const data = await res.json();
        item = (data.items || []).find(x => x.id === itemId) || null;
    }

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${item ? 'edit_gold_type' : 'add_gold_type'}">${item ? t('edit_gold_type', 'Edit Gold Type') : t('add_gold_type', 'Add Gold Type')}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-7"><label data-i18n="gold_type">${t('gold_type', 'Gold Type')}</label><input type="text" class="form-control" id="gstName" value="${item?.name || ''}"></div>
                <div class="col-3"><label data-i18n="order">${t('order', 'Order')}</label><input type="number" class="form-control" id="gstOrder" value="${item?.order ?? 0}"></div>
                <div class="col-2"><label data-i18n="active">${t('active', 'Active')}</label><select class="form-select" id="gstActive"><option value="true" ${item == null || item.is_active ? 'selected' : ''}>${t('yes', 'Yes')}</option><option value="false" ${item && !item.is_active ? 'selected' : ''}>${t('no', 'No')}</option></select></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t('btn_cancel', 'Cancel')}</button>
            <button class="btn-primary-custom" onclick="saveGoldType(${itemId || 'null'})" data-i18n="btn_save">${t('btn_save', 'Save')}</button>
        </div>
    `);
    applyTranslations();
}

async function saveGoldType(itemId) {
    const body = {
        name: document.getElementById('gstName').value.trim(),
        order: parseInt(document.getElementById('gstOrder').value) || 0,
        is_active: document.getElementById('gstActive').value === 'true',
    };

    if (!body.name) {
        showToast(t('gold_type_required', 'Gold type name is required'), 'error');
        return;
    }

    const url = itemId ? `/api/settings/gold-types/${itemId}/` : '/api/settings/gold-types/';
    const method = itemId ? 'PUT' : 'POST';
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (res.ok) {
        closeModal();
        showToast(t('gold_type_saved', 'Gold type saved ✓'), 'success');
        renderGoldSettings();
    } else {
        showToast(t('error_saving_gold_type', 'Error saving gold type'), 'error');
    }
}

async function disableGoldType(itemId) {
    if (!confirm(t('confirm_disable_gold_type', 'Disable this gold type?'))) return;
    const res = await fetch(`/api/settings/gold-types/${itemId}/`, { method: 'DELETE' });
    if (res.ok) {
        showToast(t('gold_type_disabled', 'Gold type disabled'), 'success');
        renderGoldSettings();
    } else {
        showToast(t('error_disabling_gold_type', 'Error disabling gold type'), 'error');
    }
}

async function showGoldPurityModal(itemId) {
    let item = null;
    if (itemId) {
        const res = await fetch('/api/settings/gold-purities/');
        const data = await res.json();
        item = (data.items || []).find(x => x.id === itemId) || null;
    }

    showModal(`
        <div class="modal-header">
            <h5 class="modal-title" data-i18n="${item ? 'edit_gold_purity' : 'add_gold_purity'}">${item ? t('edit_gold_purity', 'Edit Gold Purity') : t('add_gold_purity', 'Add Gold Purity')}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <div class="row g-3">
                <div class="col-3"><label data-i18n="gold_purity_key">${t('gold_purity_key', 'Purity Key')}</label><input type="text" class="form-control" id="gspKey" value="${item?.key || ''}" placeholder="24k"></div>
                <div class="col-3"><label data-i18n="gold_purity_label">${t('gold_purity_label', 'Purity Label')}</label><input type="text" class="form-control" id="gspLabel" value="${item?.label || ''}" placeholder="24K"></div>
                <div class="col-3"><label data-i18n="cashback_per_gram">${t('cashback_per_gram', 'Cashback per Gram')}</label><input type="number" step="0.0001" class="form-control" id="gspCashback" value="${item?.cashback_per_gram ?? 0}"></div>
                <div class="col-2"><label data-i18n="order">${t('order', 'Order')}</label><input type="number" class="form-control" id="gspOrder" value="${item?.order ?? 0}"></div>
                <div class="col-1"><label data-i18n="active">${t('active', 'Active')}</label><select class="form-select" id="gspActive"><option value="true" ${item == null || item.is_active ? 'selected' : ''}>${t('yes', 'Yes')}</option><option value="false" ${item && !item.is_active ? 'selected' : ''}>${t('no', 'No')}</option></select></div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary-custom" data-bs-dismiss="modal" data-i18n="btn_cancel">${t('btn_cancel', 'Cancel')}</button>
            <button class="btn-primary-custom" onclick="saveGoldPurity(${itemId || 'null'})" data-i18n="btn_save">${t('btn_save', 'Save')}</button>
        </div>
    `);
    applyTranslations();
}

async function saveGoldPurity(itemId) {
    const body = {
        key: document.getElementById('gspKey').value.trim().toLowerCase(),
        label: document.getElementById('gspLabel').value.trim(),
        cashback_per_gram: parseFloat(document.getElementById('gspCashback').value) || 0,
        order: parseInt(document.getElementById('gspOrder').value) || 0,
        is_active: document.getElementById('gspActive').value === 'true',
    };

    if (!body.key) {
        showToast(t('gold_purity_key_required', 'Purity key is required'), 'error');
        return;
    }

    if (!body.label) {
        body.label = body.key.toUpperCase();
    }

    const url = itemId ? `/api/settings/gold-purities/${itemId}/` : '/api/settings/gold-purities/';
    const method = itemId ? 'PUT' : 'POST';
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (res.ok) {
        closeModal();
        showToast(t('gold_purity_saved', 'Gold purity saved ✓'), 'success');
        renderGoldSettings();
    } else {
        showToast(t('error_saving_gold_purity', 'Error saving gold purity'), 'error');
    }
}

async function disableGoldPurity(itemId) {
    if (!confirm(t('confirm_disable_gold_purity', 'Disable this gold purity?'))) return;
    const res = await fetch(`/api/settings/gold-purities/${itemId}/`, { method: 'DELETE' });
    if (res.ok) {
        showToast(t('gold_purity_disabled', 'Gold purity disabled'), 'success');
        renderGoldSettings();
    } else {
        showToast(t('error_disabling_gold_purity', 'Error disabling gold purity'), 'error');
    }
}

// ════════════════════════════════════════════════════════════════════════════
// LANGUAGE SETTINGS TAB
// ════════════════════════════════════════════════════════════════════════════

