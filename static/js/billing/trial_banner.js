"use strict";
// App-wide trial/subscription banner — shown under the topbar.
// This file is part of the billing module. Do not edit directly.

const TRIAL_BANNER_DISMISS_KEY = "wf_trial_banner_dismissed_session";

async function checkBillingStatus() {
  try {
    const res = await fetch("/api/billing/status/");
    if (!res.ok) return;
    const data = await res.json();
    _renderTrialBanner(data.subscription, data.pending_upgrade_request);
  } catch (e) {}
}

function _clearTrialBanner() {
  const mount = document.getElementById("trial-banner-mount");
  if (mount) mount.innerHTML = "";
}

function _renderTrialBanner(subscription, pendingRequest) {
  const mount = document.getElementById("trial-banner-mount");
  if (!mount || !subscription) return;

  if (subscription.status === "trialing" && subscription.has_access) {
    if (sessionStorage.getItem(TRIAL_BANNER_DISMISS_KEY)) return;
    return _paintTrialBanner(mount, subscription, pendingRequest);
  }

  if (!subscription.has_access) {
    return _paintExpiredBanner(mount, subscription, pendingRequest);
  }

  if (subscription.status === "past_due") {
    return _paintPastDueBanner(mount);
  }

  _clearTrialBanner();
}

function _paintTrialBanner(mount, subscription, pendingRequest) {
  const days = subscription.trial_days_remaining ?? 0;
  const label =
    days <= 0
      ? t("trial_banner_last_day", "Last day of your free trial")
      : t("trial_banner_days_left", "{days} days left in your free trial").replace("{days}", days);

  mount.innerHTML = `
        <div class="wf-billing-banner wf-billing-banner-trial">
            <span>🎁 ${label}</span>
            <div style="display:flex;align-items:center;gap:8px;">
                ${_upgradeCta(pendingRequest, "light")}
                <button class="wf-billing-banner-dismiss" onclick="dismissTrialBanner()" aria-label="Dismiss">×</button>
            </div>
        </div>`;
}

function _paintExpiredBanner(mount, subscription, pendingRequest) {
  const label =
    subscription.status === "canceled"
      ? t("subscription_canceled_banner", "Your subscription has ended.")
      : t("trial_expired_banner", "Your trial has ended. Upgrade to keep using WealthFlow.");

  mount.innerHTML = `
        <div class="wf-billing-banner wf-billing-banner-expired">
            <span>⚠️ ${label}</span>
            ${_upgradeCta(pendingRequest, "solid")}
        </div>`;
}

function _paintPastDueBanner(mount) {
  mount.innerHTML = `
        <div class="wf-billing-banner wf-billing-banner-pastdue">
            <span>⚠️ ${t("subscription_past_due_banner", "There was a problem with your last payment. Please update your billing.")}</span>
            <button class="wf-billing-banner-btn" onclick="navigate('billing-plans')" data-i18n="trial_banner_upgrade_btn">
                ${t("trial_banner_upgrade_btn", "Upgrade")}
            </button>
        </div>`;
}

function _upgradeCta(pendingRequest, variant) {
  if (pendingRequest) {
    return `<span class="wf-billing-banner-pending" data-i18n="upgrade_request_pending">${t("upgrade_request_pending", "Request Pending")}</span>`;
  }
  const cls = variant === "solid" ? "wf-billing-banner-btn" : "wf-billing-banner-btn light";
  return `<button class="${cls}" onclick="navigate('billing-plans')" data-i18n="trial_banner_upgrade_btn">
        ${t("trial_banner_upgrade_btn", "Upgrade")}
    </button>`;
}

function dismissTrialBanner() {
  sessionStorage.setItem(TRIAL_BANNER_DISMISS_KEY, "1");
  _clearTrialBanner();
}

window.checkBillingStatus = checkBillingStatus;
window.dismissTrialBanner = dismissTrialBanner;
