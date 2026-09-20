"use strict";
// First-run setup wizard: employer (optional), first Cash account, categories.
// Shown once per new user; completion or skip is stored server-side.

let _onboardingStep = 1;
const _ONBOARDING_STEPS = 3;

function onboardingEsc(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

async function initOnboardingWizard() {
  try {
    const res = await fetch("/api/onboarding/status/");
    if (!res.ok) return;
    const status = await res.json();
    if (status.rates_missing) {
      fetch("/api/rates/refresh/", { method: "POST" }).catch(() => {});
    }
    if (status.needs_wizard) showOnboardingWizard(status);
  } catch (_e) {
    // The wizard is a convenience; never block the app on it.
  }
}

function onboardingCategoryRow(cat) {
  return `<label class="d-flex align-items-center gap-2 mb-2" style="cursor:pointer">
      <input type="checkbox" class="form-check-input onb-cat" value="${onboardingEsc(cat.name)}" checked>
      <span>${onboardingEsc(cat.icon || "💰")} ${onboardingEsc(cat.name)}</span></label>`;
}

function showOnboardingWizard(status) {
  _onboardingStep = 1;
  const currencyOptions = (status.currencies || [])
    .map((c) => `<option value="${c.id}">${onboardingEsc(c.code)} ${onboardingEsc(c.symbol)}</option>`)
    .join("");
  showModal(`
    <div class="modal-header">
      <h5 class="modal-title" data-i18n="onboarding_title">${t("onboarding_title", "Welcome to WealthFlow")}</h5>
    </div>
    <div class="modal-body" id="onbBody">
      <p style="color:var(--text-muted)" data-i18n="onboarding_subtitle">${t("onboarding_subtitle", "Three quick steps to get started. You can change everything later.")}</p>
      <div id="onbStep1">
        <h6 data-i18n="onboarding_employer_title">${t("onboarding_employer_title", "Your employer (optional)")}</h6>
        <label data-i18n="onboarding_employer_name">${t("onboarding_employer_name", "Employer name")}</label>
        <input id="onbEmployer" class="form-control" maxlength="200">
      </div>
      <div id="onbStep2" style="display:none">
        <h6 data-i18n="onboarding_account_title">${t("onboarding_account_title", "Your first account")}</h6>
        <div class="row g-2">
          <div class="col-md-4"><label data-i18n="onboarding_account_name">${t("onboarding_account_name", "Account name")}</label>
            <input id="onbAccTitle" class="form-control" maxlength="200" value="${onboardingEsc(t("onboarding_cash_default_name", "Cash"))}"></div>
          <div class="col-md-4"><label data-i18n="onboarding_account_currency">${t("onboarding_account_currency", "Currency")}</label>
            <select id="onbAccCurrency" class="form-select">${currencyOptions}</select></div>
          <div class="col-md-4"><label data-i18n="onboarding_account_balance">${t("onboarding_account_balance", "Starting balance")}</label>
            <input id="onbAccAmount" class="form-control" type="number" min="0" step="0.01" placeholder="0"></div>
        </div>
        <div class="mt-2" style="font-size:13px;color:var(--text-muted)" data-i18n="onboarding_cash_note">${t("onboarding_cash_note", "This is created as a Cash balance. Expenses are deducted from Cash balances, so it should hold the money you spend day to day.")}</div>
      </div>
      <div id="onbStep3" style="display:none">
        <h6 data-i18n="onboarding_categories_title">${t("onboarding_categories_title", "Expense categories")}</h6>
        <div style="color:var(--text-muted);font-size:13px" class="mb-2" data-i18n="onboarding_categories_hint">${t("onboarding_categories_hint", "Untick any you do not need, or add your own.")}</div>
        <div id="onbCats">${(status.categories || []).map(onboardingCategoryRow).join("")}</div>
        <div class="d-flex gap-2 mt-2">
          <input id="onbNewCat" class="form-control" maxlength="100" data-i18n-placeholder="onboarding_new_category" placeholder="${t("onboarding_new_category", "New category")}">
          <button class="btn btn-secondary" type="button" onclick="onboardingAddCategory()" data-i18n="onboarding_add_category">${t("onboarding_add_category", "Add")}</button>
        </div>
      </div>
    </div>
    <div class="modal-footer" style="justify-content:space-between">
      <button class="btn btn-link" type="button" onclick="onboardingSkip()" data-i18n="onboarding_skip">${t("onboarding_skip", "Skip for now")}</button>
      <div class="d-flex gap-2">
        <button class="btn btn-secondary" id="onbBack" type="button" onclick="onboardingMove(-1)" style="display:none" data-i18n="onboarding_back">${t("onboarding_back", "Back")}</button>
        <button class="btn btn-primary" id="onbNext" type="button" onclick="onboardingMove(1)" data-i18n="onboarding_next">${t("onboarding_next", "Next")}</button>
      </div>
    </div>`);
}

function onboardingAddCategory() {
  const input = document.getElementById("onbNewCat");
  const name = (input.value || "").trim();
  if (!name) return;
  document.getElementById("onbCats").insertAdjacentHTML("beforeend", onboardingCategoryRow({ name }));
  input.value = "";
}

function onboardingMove(delta) {
  if (delta > 0 && _onboardingStep === _ONBOARDING_STEPS) return onboardingFinish();
  _onboardingStep = Math.min(_ONBOARDING_STEPS, Math.max(1, _onboardingStep + delta));
  for (let i = 1; i <= _ONBOARDING_STEPS; i++) {
    document.getElementById(`onbStep${i}`).style.display = i === _onboardingStep ? "" : "none";
  }
  document.getElementById("onbBack").style.display = _onboardingStep > 1 ? "" : "none";
  const isLast = _onboardingStep === _ONBOARDING_STEPS;
  const next = document.getElementById("onbNext");
  next.textContent = isLast ? t("onboarding_finish", "Finish") : t("onboarding_next", "Next");
}

async function _onboardingPost(payload) {
  const res = await fetch("/api/onboarding/complete/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.ok) return true;
  const body = await res.json().catch(() => ({}));
  showToast(t(body.error_key || "settings_save_failed", body.error || "Save failed"), "error");
  return false;
}

async function onboardingSkip() {
  if (await _onboardingPost({ skip: true })) closeModal();
}

async function onboardingFinish() {
  const employer = document.getElementById("onbEmployer").value.trim();
  const amountRaw = document.getElementById("onbAccAmount").value;
  const account = amountRaw === "" ? null : {
    title: document.getElementById("onbAccTitle").value.trim(),
    currency_id: Number(document.getElementById("onbAccCurrency").value),
    amount: amountRaw,
  };
  const categories = [...document.querySelectorAll(".onb-cat:checked")].map((el) => el.value);
  const payload = { employer: employer ? { name: employer } : null, account, categories };
  if (!(await _onboardingPost(payload))) return;
  closeModal();
  showToast(t("onboarding_saved", "You are all set ✓"));
  window.location.reload();
}

window.initOnboardingWizard = initOnboardingWizard;
window.onboardingAddCategory = onboardingAddCategory;
window.onboardingMove = onboardingMove;
window.onboardingSkip = onboardingSkip;
