"use strict";
// Billing Plans settings — Payment Gateway (Paymob) configuration card.
// Entirely UI-configured; no gateway credentials are ever hardcoded.
// This file is part of the settings module. Do not edit directly.

let _gatewaySettings = null;

async function _fetchGatewaySettings() {
  const res = await fetch("/api/settings/billing/gateway/");
  if (!res.ok) return null;
  return res.json();
}

function _gatewayCardHtml(g) {
  const badge = g.is_configured
    ? `<span class="wf-gateway-badge wf-gateway-badge-live" data-i18n="payment_gateway_live_badge">${t("payment_gateway_live_badge", "Live")}</span>`
    : `<span class="wf-gateway-badge wf-gateway-badge-test" data-i18n="payment_gateway_test_mode_badge">${t("payment_gateway_test_mode_badge", "Test Mode — no real charges")}</span>`;

  return `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="payment_gateway">${t("payment_gateway", "Payment Gateway")}</div>
                ${badge}
            </div>
            <div style="margin-bottom:10px;color:var(--text-muted);font-size:12px;" data-i18n="payment_gateway_hint">
                ${t("payment_gateway_hint", "Configure Paymob to accept real payments. Until this is filled in, checkout runs in test mode so trial users aren't blocked.")}
            </div>
            <div class="row g-3">
                <div class="col-6">
                    <label data-i18n="paymob_api_key">${t("paymob_api_key", "Paymob API Key")}</label>
                    <input type="text" class="form-control" id="paymobApiKey" value="${g.paymob_api_key || ""}" autocomplete="off">
                </div>
                <div class="col-6">
                    <label data-i18n="paymob_hmac_secret">${t("paymob_hmac_secret", "Paymob HMAC Secret")}</label>
                    <input type="text" class="form-control" id="paymobHmacSecret" value="${g.paymob_hmac_secret || ""}" autocomplete="off">
                </div>
                <div class="col-6">
                    <label data-i18n="paymob_integration_id">${t("paymob_integration_id", "Integration ID")}</label>
                    <input type="text" class="form-control" id="paymobIntegrationId" value="${g.paymob_integration_id || ""}">
                </div>
                <div class="col-6">
                    <label data-i18n="paymob_iframe_id">${t("paymob_iframe_id", "Iframe ID")}</label>
                    <input type="text" class="form-control" id="paymobIframeId" value="${g.paymob_iframe_id || ""}">
                </div>
            </div>
            <div style="margin-top:10px;text-align:right;">
                <button class="btn-primary-custom btn-sm" onclick="saveGatewaySettings()" data-i18n="btn_save">${t("btn_save", "Save")}</button>
            </div>
        </div>`;
}

async function renderGatewaySettingsCard() {
  const mount = document.getElementById("gatewaySettingsMount");
  if (!mount) return;
  _gatewaySettings = await _fetchGatewaySettings();
  if (!_gatewaySettings) return;
  mount.innerHTML = _gatewayCardHtml(_gatewaySettings);
  applyTranslations();
}

async function saveGatewaySettings() {
  const body = {
    paymob_api_key: document.getElementById("paymobApiKey").value.trim(),
    paymob_hmac_secret: document.getElementById("paymobHmacSecret").value.trim(),
    paymob_integration_id: document.getElementById("paymobIntegrationId").value.trim(),
    paymob_iframe_id: document.getElementById("paymobIframeId").value.trim(),
  };

  const res = await fetch("/api/settings/billing/gateway/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    showToast(t("gateway_settings_saved", "Payment gateway settings saved ✓"), "success");
    renderGatewaySettingsCard();
  } else {
    showToast(t("error_saving_gateway_settings", "Error saving payment gateway settings"), "error");
  }
}

window.renderGatewaySettingsCard = renderGatewaySettingsCard;
window.saveGatewaySettings = saveGatewaySettings;
