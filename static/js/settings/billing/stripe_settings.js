"use strict";
// Billing Plans settings — Stripe gateway card (keys are entered here, never hardcoded).
// This file is part of the settings module. Do not edit directly.

async function _fetchStripeSettings() {
  const res = await fetch("/api/settings/billing/stripe/");
  if (!res.ok) return null;
  return res.json();
}

function _stripeBadgeHtml(live) {
  return live
    ? `<span class="wf-gateway-badge wf-gateway-badge-live" data-i18n="payment_gateway_live_badge">${t("payment_gateway_live_badge", "Live")}</span>`
    : `<span class="wf-gateway-badge wf-gateway-badge-test" data-i18n="payment_gateway_region_not_set">${t("payment_gateway_region_not_set", "Not configured")}</span>`;
}

function _stripeFieldHtml(id, labelKey, labelDefault, value) {
  return `<div class="col-6">
                    <label data-i18n="${labelKey}">${t(labelKey, labelDefault)}</label>
                    <input type="text" class="form-control" id="${id}" value="${value || ""}" autocomplete="off">
                </div>`;
}

function _stripeCardHtml(g) {
  return `
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:12px;padding:14px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <div style="font-weight:600;color:var(--text-secondary)" data-i18n="stripe_gateway">${t("stripe_gateway", "Stripe (card payments)")}</div>
                ${_stripeBadgeHtml(g.is_configured)}
            </div>
            <div style="margin-bottom:10px;color:var(--text-muted);font-size:12px;" data-i18n="stripe_gateway_hint">
                ${t("stripe_gateway_hint", "Used for currencies Paymob does not serve. In the Stripe dashboard add a webhook endpoint for checkout.session events pointing to your site at the path below, then paste its signing secret here.")}
            </div>
            <div style="margin-bottom:10px;font-family:monospace;font-size:12px;" id="stripeWebhookPath">${g.webhook_path}</div>
            <div class="row g-3">
                ${_stripeFieldHtml("stripeSecretKey", "stripe_secret_key", "Stripe Secret Key", g.stripe_secret_key)}
                ${_stripeFieldHtml("stripeWebhookSecret", "stripe_webhook_secret", "Webhook Signing Secret", g.stripe_webhook_secret)}
                ${_stripeFieldHtml("stripeCurrencies", "stripe_currencies", "Currencies charged through Stripe", g.stripe_currencies)}
            </div>
            <div style="margin-top:10px;text-align:right;">
                <button class="btn-primary-custom btn-sm" id="stripeSaveBtn" onclick="saveStripeSettings()" data-i18n="btn_save">${t("btn_save", "Save")}</button>
            </div>
        </div>`;
}

async function renderStripeSettingsCard() {
  const mount = document.getElementById("stripeSettingsMount");
  if (!mount) return;
  const settings = await _fetchStripeSettings();
  if (!settings) return;
  mount.innerHTML = _stripeCardHtml(settings);
  applyTranslations();
}

async function saveStripeSettings() {
  const body = {
    stripe_secret_key: document.getElementById("stripeSecretKey").value.trim(),
    stripe_webhook_secret: document.getElementById("stripeWebhookSecret").value.trim(),
    stripe_currencies: document.getElementById("stripeCurrencies").value.trim(),
  };
  const res = await fetch("/api/settings/billing/stripe/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    showToast(t("gateway_settings_saved", "Payment gateway settings saved ✓"), "success");
    renderStripeSettingsCard();
  } else {
    showToast(t("error_saving_gateway_settings", "Error saving payment gateway settings"), "error");
  }
}

window.renderStripeSettingsCard = renderStripeSettingsCard;
window.saveStripeSettings = saveStripeSettings;
