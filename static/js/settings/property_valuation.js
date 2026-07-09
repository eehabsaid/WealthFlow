"use strict";
// Property valuation settings management
// This file is part of the settings module. Do not edit directly.

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

    const responses = await Promise.all(settingsToSave.map(([key, value]) => fetch('/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value }),
    })));

    if (responses.every(r => r.ok)) {
        showToast(t('property_valuation_settings_saved', 'Property valuation settings saved.'), 'success');
    } else {
        showToast(t('error_saving_property_valuation_settings', 'Failed to save property valuation settings.'), 'error');
    }
}

