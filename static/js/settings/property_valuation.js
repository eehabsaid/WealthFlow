"use strict";
// Property valuation settings management
// This file is part of the settings module. Do not edit directly.

async function renderPropertyValuationSettings() {
    const settingsRes = await fetch('/api/settings/');
    const settingsData = await settingsRes.json();

    const currentRateMap = settingsData?.settings?.property_valuation_rate_map || '';
    const providerOrder = settingsData?.settings?.property_valuation_provider_order || 'external_api,configured_market_rate';
    const externalEnabled = (settingsData?.settings?.property_valuation_external_enabled || 'false') === 'true';
    const externalUrl = settingsData?.settings?.property_valuation_external_url || '';
    const externalResultPath = settingsData?.settings?.property_valuation_external_result_path || 'estimated_price';
    const externalTimeout = settingsData?.settings?.property_valuation_external_timeout_secs || '8';
    const externalHeaders = settingsData?.settings?.property_valuation_external_headers || '';

    document.getElementById('settingsContent').innerHTML = `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:12px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:12px;color:var(--text-muted)" data-i18n="property_valuation_rate_map_hint">${t('property_valuation_rate_map_hint', 'Provide JSON with by_city, by_governorate, and optional default EGP-per-square-meter rates.')}</div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                    <button id="btnScrapeAqarmap" class="btn-secondary-custom" onclick="scrapePropertyRates(false)" data-i18n="scrape_property_rates" title="${t('scrape_property_rates_hint', 'Auto-fetch Cairo district rates from Aqarmap')}"><i class="bi bi-cloud-download"></i> ${t('scrape_property_rates', 'Scrape from Aqarmap')}</button>
                    <button class="btn-secondary-custom" onclick="scrapePropertyRates(true)" data-i18n="load_baseline_rates" title="${t('load_baseline_rates_hint', 'Load hardcoded baseline rates instantly')}"><i class="bi bi-database"></i> ${t('load_baseline_rates', 'Load Baseline')}</button>
                    <span id="scrapeStatusBadge" style="font-size:12px;"></span>
                    <button class="btn-primary-custom" onclick="savePropertyValuationSettings()" data-i18n="save_property_valuation_settings">${t('save_property_valuation_settings', 'Save Valuation Settings')}</button>
                </div>
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

async function savePropertyValuationSettings() {
    const textarea = document.getElementById('propertyValuationRateMap');
    const raw = textarea?.value?.trim() || '';
    const providerOrder = document.getElementById('propertyValuationProviderOrder')?.value || 'external_api,configured_market_rate';
    const externalEnabled = document.getElementById('propertyValuationExternalEnabled')?.value || 'false';
    const externalUrl = document.getElementById('propertyValuationExternalUrl')?.value?.trim() || '';
    const externalResultPath = document.getElementById('propertyValuationExternalResultPath')?.value?.trim() || 'estimated_price';
    const externalTimeout = document.getElementById('propertyValuationExternalTimeout')?.value?.trim() || '8';
    const externalHeadersRaw = document.getElementById('propertyValuationExternalHeaders')?.value?.trim() || '';

    if (raw) {
        try {
            JSON.parse(raw);
        } catch (error) {
            showToast(t('invalid_property_valuation_rate_map', 'Property valuation rate map must be valid JSON.'), 'error');
            return;
        }
    }

    if (externalEnabled === 'true' && !externalUrl) {
        showToast(t('invalid_property_valuation_external_url', 'External URL is required when external valuation is enabled.'), 'error');
        return;
    }

    if (externalHeadersRaw) {
        try {
            const parsedHeaders = JSON.parse(externalHeadersRaw);
            if (!parsedHeaders || Array.isArray(parsedHeaders) || typeof parsedHeaders !== 'object') {
                throw new Error('invalid_headers');
            }
        } catch (error) {
            showToast(t('invalid_property_valuation_external_headers', 'External headers must be a valid JSON object.'), 'error');
            return;
        }
    }

    if (!Number.isFinite(Number(externalTimeout)) || Number(externalTimeout) <= 0) {
        showToast(t('invalid_property_valuation_external_timeout', 'External timeout must be a positive number.'), 'error');
        return;
    }

    const settingsToSave = [
        ['property_valuation_rate_map', raw],
        ['property_valuation_provider_order', providerOrder],
        ['property_valuation_external_enabled', externalEnabled],
        ['property_valuation_external_url', externalUrl],
        ['property_valuation_external_result_path', externalResultPath],
        ['property_valuation_external_timeout_secs', String(externalTimeout)],
        ['property_valuation_external_headers', externalHeadersRaw],
    ];

    try {
        const res = await fetch('/api/settings/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ settings: Object.fromEntries(settingsToSave) }),
        });

        if (res.ok) {
            showToast(t('property_valuation_settings_saved', 'Property valuation settings saved.'), 'success');
        } else {
            showToast(t('error_saving_property_valuation_settings', 'Failed to save property valuation settings.'), 'error');
        }
    } catch {
        showToast(t('error_saving_property_valuation_settings', 'Failed to save property valuation settings.'), 'error');
    }
}


async function scrapePropertyRates(baselineOnly = false) {
    const btn = document.getElementById('btnScrapeAqarmap');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>${t('scraping_property_rates', 'Scraping…')}`;
    }

    try {
        const res = await fetch('/api/settings/scrape-property-rates/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ baseline_only: baselineOnly, timeout: 30 }),
        });

        const data = await res.json();

        const badge = document.getElementById('scrapeStatusBadge');
        if (res.ok && data.ok) {
            const textarea = document.getElementById('propertyValuationRateMap');
            if (textarea) textarea.value = data.rate_map_json;

            const liveSuccess = data.source === 'aqarmap_live+baseline';
            if (badge) {
                if (liveSuccess) {
                    badge.innerHTML = `<span style="color:var(--accent-green)"><i class="bi bi-check-circle-fill"></i> Aqarmap live &mdash; ${data.districts} districts</span>`;
                } else {
                    badge.innerHTML = `<span style="color:var(--accent-yellow,#f5a623)"><i class="bi bi-exclamation-triangle-fill"></i> Scrape failed &mdash; baseline used (${data.districts} districts)</span>`;
                }
            }
            showToast(
                liveSuccess
                    ? `Rates fetched from Aqarmap - ${data.districts} districts`
                    : `Aqarmap unreachable - loaded ${data.districts} baseline districts`,
                liveSuccess ? 'success' : 'warning'
            );
        } else {
            const badge = document.getElementById('scrapeStatusBadge');
            if (badge) badge.innerHTML = `<span style="color:var(--accent-red)"><i class="bi bi-x-circle-fill"></i> ${t('error_scraping_property_rates', 'Failed to fetch rates')}</span>`;
            showToast(t('error_scraping_property_rates', 'Failed to fetch rates'), 'error');
        }
    } catch {
        const badge = document.getElementById('scrapeStatusBadge');
        if (badge) badge.innerHTML = `<span style="color:var(--accent-red)"><i class="bi bi-x-circle-fill"></i> ${t('error_scraping_property_rates', 'Failed to fetch rates')}</span>`;
        showToast(t('error_scraping_property_rates', 'Failed to fetch rates'), 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="bi bi-cloud-download"></i> ${t('scrape_property_rates', 'Scrape from Aqarmap')}`;
        }
    }
}