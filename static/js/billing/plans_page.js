"use strict";
// Customer-facing "choose your plan" page. Not the admin Billing Plans
// settings tab — that's static/js/settings/billing/.

let _plansPageCurrency = null;

async function renderBillingPlansPage() {
  const main = document.getElementById("main-content");
  if (!main) return;
  main.innerHTML = `<div id="wf-plans-page">${t("loading_ellipsis", "Loading…")}</div>`;

  try {
    const [plansRes, statusRes] = await Promise.all([
      fetch("/api/billing/plans/"),
      fetch("/api/billing/status/"),
    ]);
    const plansData = await plansRes.json();
    const statusData = await statusRes.json();
    _paintPlansPage(
      plansData.plans || [],
      statusData.subscription,
      statusData.pending_upgrade_request
    );
  } catch (e) {
    document.getElementById("wf-plans-page").innerHTML =
      `<p>${t("error_loading_plans", "Couldn't load plans. Please try again.")}</p>`;
  }
}

function _paintPlansPage(plans, subscription, pendingRequest) {
  const container = document.getElementById("wf-plans-page");
  if (!container) return;

  const currencies = _plansPageCurrencyOptions(plans);
  if (!_plansPageCurrency || !currencies.includes(_plansPageCurrency)) {
    _plansPageCurrency = currencies[0] || null;
  }

  const currentPlanId = subscription?.plan?.id ?? null;

  container.innerHTML = `
        <div class="wf-plans-header">
            <h1 data-i18n="billing_plans_page_title">${t("billing_plans_page_title", "Choose your plan")}</h1>
            <p data-i18n="billing_plans_page_subtitle">${t("billing_plans_page_subtitle", "Pick the plan that fits, and we'll follow up to get you set up.")}</p>
        </div>
        ${_currencySelectHtml(currencies)}
        <div class="wf-plans-grid">
            ${plans.length ? plans.map((p) => _planCardHtml(p, currentPlanId, pendingRequest)).join("") : `<p>${t("no_active_plans", "No plans available yet.")}</p>`}
        </div>
        <div id="wf-account-data"></div>`;
  if (typeof renderAccountDataCard === "function") renderAccountDataCard();
}

function _plansPageCurrencyOptions(plans) {
  const codes = new Set();
  plans.forEach((p) => (p.prices || []).forEach((pr) => codes.add(pr.currency_code)));
  return Array.from(codes);
}

function _currencySelectHtml(currencies) {
  if (currencies.length <= 1) return "";
  return `
        <div class="wf-plans-currency-select">
            <select class="form-select" style="max-width:160px;" onchange="_onPlansCurrencyChange(this.value)">
                ${currencies
                  .map(
                    (c) =>
                      `<option value="${esc(c)}" ${c === _plansPageCurrency ? "selected" : ""}>${esc(c)}</option>`
                  )
                  .join("")}
            </select>
        </div>`;
}

function _onPlansCurrencyChange(code) {
  _plansPageCurrency = code;
  renderBillingPlansPage();
}

function _planCardHtml(plan, currentPlanId, pendingRequest) {
  const isCurrent = plan.id === currentPlanId;
  const price = (plan.prices || []).find((p) => p.currency_code === _plansPageCurrency);

  const priceHtml = price
    ? `<span dir="ltr" style="display: inline-flex; align-items: baseline; gap: 4px;">
         <span>${esc(price.currency_symbol || price.currency_code)}${fmt(price.amount)}</span>
         <span style="opacity: 0.8; font-size: 0.85em;">/ ${plan.billing_interval_days} ${t("days_suffix", "d")}</span>
       </span>`
    : `<span style="font-size:14px;">${t("no_prices_set", "No prices set")}</span>`;

  let ctaHtml;
  if (isCurrent) {
    ctaHtml = `<button class="wf-plan-card-cta" disabled>${t("current_plan_badge", "Current Plan")}</button>`;
  } else if (price) {
    ctaHtml = `<button class="wf-plan-card-cta" onclick="checkoutPlan(${plan.id})">${t("subscribe_btn", "Subscribe")}</button>`;
  } else if (pendingRequest && pendingRequest.plan_id === plan.id) {
    ctaHtml = `<button class="wf-plan-card-cta wf-plan-cta-pending" disabled>${t("upgrade_request_pending", "Request Pending")}</button>`;
  } else {
    ctaHtml = `<button class="wf-plan-card-cta" onclick="submitUpgradeRequest(${plan.id})">${t("request_upgrade_btn", "Request Upgrade")}</button>`;
  }

  // Ensures uniform vertical alignment across all cards whether they have a badge or not
  const badgeHtml = isCurrent
    ? `<span class="wf-plan-card-badge">${t("current_plan_badge", "Current Plan")}</span>`
    : `<span class="wf-plan-card-badge" style="visibility:hidden; pointer-events:none;">&nbsp;</span>`;

  return `
        <div class="wf-plan-card ${isCurrent ? "wf-plan-current" : ""}">
            ${badgeHtml}
            <div class="wf-plan-card-name">${esc(plan.name)}</div>
            <div class="wf-plan-card-price">${priceHtml}</div>
            ${ctaHtml}
        </div>`;
}

window.renderBillingPlansPage = renderBillingPlansPage;
