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

const _GATEWAY_REGION_CODES = ["SAR", "AED"];

function _regionFieldHtml(code, field, labelKey, labelDefault, value, secret) {
  const id = `paymobRegion_${code}_${field}`;
  return `<div class="col-6">
                    <label data-i18n="${labelKey}">${t(labelKey, labelDefault)}</label>
                    <input type="text" class="form-control" id="${id}" value="${value || ""}" autocomplete="off"${secret ? "" : ""}>
                </div>`;
}

function _regionsHtml(g) {
  const regions = g.regions || {};
  const blocks = _GATEWAY_REGION_CODES
    .map((code) => {
      const r = regions[code] || {};
      const live = r.is_configured
        ? `<span class="wf-gateway-badge wf-gateway-badge-live" data-i18n="payment_gateway_live_badge">${t("payment_gateway_live_badge", "Live")}</span>`
        : `<span class="wf-gateway-badge wf-gateway-badge-test" data-i18n="payment_gateway_region_not_set">${t("payment_gateway_region_not_set", "Not configured")}</span>`;
      return `<div style="margin-top:12px;border-top:1px solid var(--border-color);padding-top:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <div style="font-weight:600;color:var(--text-secondary)">${code}</div>${live}
            </div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                <button type="button" class="btn btn-outline-secondary btn-sm" data-paymob-test="${code}" onclick="testGatewayRegion('${code}')" data-i18n="paymob_test_btn">${t("paymob_test_btn", "Test connection")}</button>
                <small id="paymobTestResult_${code}" class="text-muted" role="status"></small>
            </div>
            <div class="row g-3">
                ${_regionFieldHtml(code, "base_url", "paymob_region_host", "Paymob host (e.g. ksa.paymob.com)", r.base_url)}
                ${_regionFieldHtml(code, "api_key", "paymob_api_key", "Paymob API Key", r.api_key, true)}
                ${_regionFieldHtml(code, "hmac_secret", "paymob_hmac_secret", "Paymob HMAC Secret", r.hmac_secret, true)}
                ${_regionFieldHtml(code, "integration_id", "paymob_integration_id", "Integration ID", r.integration_id)}
                ${_regionFieldHtml(code, "iframe_id", "paymob_iframe_id", "Iframe ID", r.iframe_id)}
            </div>
        </div>`;
    })
    .join("");
  return `<div style="margin-top:14px;">
            <div style="font-weight:600;color:var(--text-secondary)" data-i18n="payment_gateway_gulf_title">${t("payment_gateway_gulf_title", "Gulf accounts (SAR / AED)")}</div>
            <div style="margin:4px 0;color:var(--text-muted);font-size:12px;" data-i18n="payment_gateway_gulf_hint">${t("payment_gateway_gulf_hint", "Each Paymob region has its own account. Fill a currency in only if you have a Paymob account for it; otherwise that currency cannot be paid online.")}</div>
            <div class="col-6" style="margin-top:6px;">
                <label data-i18n="paymob_default_currencies">${t("paymob_default_currencies", "Currencies served by the main account")}</label>
                <input type="text" class="form-control" id="paymobDefaultCurrencies" value="${g.paymob_default_currencies || "EGP"}" autocomplete="off">
            </div>
            ${blocks}
        </div>`;
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
            ${_regionsHtml(g)}
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
    paymob_default_currencies: document.getElementById("paymobDefaultCurrencies").value.trim(),
    regions: {},
  };
  _GATEWAY_REGION_CODES.forEach((code) => {
    body.regions[code] = {};
    ["base_url", "api_key", "hmac_secret", "integration_id", "iframe_id"].forEach((field) => {
      body.regions[code][field] = document
        .getElementById(`paymobRegion_${code}_${field}`)
        .value.trim();
    });
  });

  const res = await fetch("/api/settings/billing/gateway/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    showToast(t("gateway_settings_saved", "Payment gateway settings saved ✓"), "success");
    renderGatewaySettingsCard();
  } else {
    showToast(t("error_saving_gateway_settings", "Error saving payment gateway settings"), "error");
  }
}

async function testGatewayRegion(code) {
  const out = document.getElementById(`paymobTestResult_${code}`);
  const btn = document.querySelector(`[data-paymob-test="${code}"]`);
  if (!out) return;
  if (btn) btn.disabled = true;
  out.textContent = "…";
  out.className = "text-muted";
  try {
    const res = await fetch("/api/settings/billing/gateway/test/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
      body: JSON.stringify({ currency: code }),
    });
    const data = await res.json().catch(() => ({}));
    const key = data.error_key || "paymob_test_failed";
    let msg = t(key, key).replace("{host}", data.host || "");
    if (!data.ok && data.detail) msg += ` (${data.detail})`;
    out.textContent = msg;
    out.className = data.ok ? "text-success" : "text-danger";
  } catch (e) {
    out.textContent = t("paymob_test_failed", "Could not reach the server to run the test.");
    out.className = "text-danger";
  } finally {
    if (btn) btn.disabled = false;
  }
}

window.testGatewayRegion = testGatewayRegion;
window.renderGatewaySettingsCard = renderGatewaySettingsCard;
window.saveGatewaySettings = saveGatewaySettings;
