"use strict";

function _toggleRecurringBankField() {
  const methodEl = document.getElementById("rMethod");
  const bankWrap = document.getElementById("rBankWrap");
  if (!methodEl || !bankWrap) return;
  const required =
    typeof isExpenseBankRequired === "function" && isExpenseBankRequired(methodEl.value);
  bankWrap.classList.toggle("d-none", !required);
}

function _budgetCurrencyOptions(selectedCode) {
  const curs = window._expCurrencies || [];
  return curs
    .map(
      (c) =>
        `<option value="${c.id}" ${c.code === selectedCode ? "selected" : c.code === baseCurrencyCode() && !selectedCode ? "selected" : ""}>${c.flag} ${c.code}</option>`
    )
    .join("");
}

function _budgetCategoryOptions(selectedId, includeAll) {
  const cats = window._expCategories || [];
  const allOpt = includeAll
    ? `<option value="" ${!selectedId ? "selected" : ""}>${t("budget_all_categories", "All categories (overall budget)")}</option>`
    : "";
  return (
    allOpt +
    cats
      .map(
        (c) =>
          `<option value="${c.id}" ${selectedId === c.id ? "selected" : ""}>${c.icon} ${c.name}</option>`
      )
      .join("")
  );
}

async function showBudgetModal(budget) {
  const html = `
    <div class="modal-header">
      <h5 class="modal-title" data-i18n="${budget ? "edit_budget" : "add_budget"}">${budget ? "Edit Budget" : "Add Budget"}</h5>
      <button type="button" class="btn-close" onclick="closeModal()"></button>
    </div>
    <div class="modal-body">
      <div class="mb-3">
        <label class="form-label" data-i18n="budget_name">Name</label>
        <input type="text" class="form-control" id="bName" value="${budget ? budget.name : ""}">
      </div>
      <div class="mb-3">
        <label class="form-label" data-i18n="budget_category">Category</label>
        <select class="form-select" id="bCat">${_budgetCategoryOptions(budget ? budget.category_id : null, true)}</select>
      </div>
      <div class="row">
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="budget_period">Period</label>
          <select class="form-select" id="bPeriod">
            <option value="weekly" ${budget && budget.period === "weekly" ? "selected" : ""} data-i18n="period_weekly">Weekly</option>
            <option value="monthly" ${!budget || budget.period === "monthly" ? "selected" : ""} data-i18n="period_monthly">Monthly</option>
            <option value="yearly" ${budget && budget.period === "yearly" ? "selected" : ""} data-i18n="period_yearly">Yearly</option>
          </select>
        </div>
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="budget_threshold">Alert threshold %</label>
          <input type="number" min="1" max="100" class="form-control" id="bThreshold" value="${budget ? budget.alert_threshold_percent : 80}">
        </div>
      </div>
      <div class="row">
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="budget_amount">Amount</label>
          <input type="number" step="0.01" class="form-control" id="bAmount" value="${budget ? budget.amount : ""}">
        </div>
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="budget_currency">Currency</label>
          <select class="form-select" id="bCurrency">${_budgetCurrencyOptions(budget ? budget.currency_code : null)}</select>
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal()" data-i18n="btn_cancel">Cancel</button>
      <button class="btn btn-primary" onclick="saveBudget(${budget ? budget.id : "null"})" data-i18n="btn_save">Save</button>
    </div>`;
  showModal(html);
  applyTranslations();
}

async function showRecurringModal(rec) {
  const banks = window._expBanks || [];
  const bankOpts = banks
    .map(
      (b) =>
        `<option value="${b.id}" ${rec && rec.bank_id === b.id ? "selected" : ""}>${b.name}</option>`
    )
    .join("");
  const methOpts = PAYMENT_METHODS.map(
    (m) =>
      `<option value="${m.value}" ${rec && rec.payment_method === m.value ? "selected" : ""} data-i18n="${m.key}">${m.value}</option>`
  ).join("");
  const today = new Date().toISOString().split("T")[0];
  const html = `
    <div class="modal-header">
      <h5 class="modal-title" data-i18n="${rec ? "edit_recurring" : "add_recurring"}">${rec ? "Edit Recurring Transaction" : "Add Recurring Transaction"}</h5>
      <button type="button" class="btn-close" onclick="closeModal()"></button>
    </div>
    <div class="modal-body">
      <div class="mb-3">
        <label class="form-label" data-i18n="recurring_name">Name</label>
        <input type="text" class="form-control" id="rName" value="${rec ? rec.name : ""}">
      </div>
      <div class="mb-3">
        <label class="form-label" data-i18n="budget_category">Category</label>
        <select class="form-select" id="rCat">${_budgetCategoryOptions(rec ? rec.category_id : null, false)}</select>
      </div>
      <div class="row">
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="budget_amount">Amount</label>
          <input type="number" step="0.01" class="form-control" id="rAmount" value="${rec ? rec.amount : ""}">
        </div>
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="budget_currency">Currency</label>
          <select class="form-select" id="rCurrency">${_budgetCurrencyOptions(rec ? rec.currency_code : null)}</select>
        </div>
      </div>
      <div class="row">
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="recurring_frequency">Frequency</label>
          <select class="form-select" id="rFrequency">
            <option value="daily" ${rec && rec.frequency === "daily" ? "selected" : ""} data-i18n="frequency_daily">Daily</option>
            <option value="weekly" ${rec && rec.frequency === "weekly" ? "selected" : ""} data-i18n="frequency_weekly">Weekly</option>
            <option value="monthly" ${!rec || rec.frequency === "monthly" ? "selected" : ""} data-i18n="frequency_monthly">Monthly</option>
            <option value="yearly" ${rec && rec.frequency === "yearly" ? "selected" : ""} data-i18n="frequency_yearly">Yearly</option>
          </select>
        </div>
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="recurring_interval">Repeat every</label>
          <input type="number" min="1" class="form-control" id="rInterval" value="${rec ? rec.interval : 1}">
        </div>
      </div>
      <div class="row">
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="recurring_start_date">Start date</label>
          <input type="date" class="form-control" id="rStartDate" value="${rec ? rec.start_date : today}">
        </div>
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="recurring_end_date">End date (optional)</label>
          <input type="date" class="form-control" id="rEndDate" value="${rec ? rec.end_date || "" : ""}">
        </div>
      </div>
      <div class="row">
        <div class="col-6 mb-3">
          <label class="form-label" data-i18n="payment_method">Payment method</label>
          <select class="form-select" id="rMethod" onchange="_toggleRecurringBankField()">${methOpts}</select>
        </div>
        <div class="col-6 mb-3" id="rBankWrap">
          <label class="form-label" data-i18n="bank_account">Bank</label>
          <select class="form-select" id="rBank">${bankOpts}</select>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label" data-i18n="notes">Notes</label>
        <input type="text" class="form-control" id="rNotes" value="${rec ? rec.notes : ""}">
      </div>
      <div class="form-check mb-2">
        <input class="form-check-input" type="checkbox" id="rActive" ${!rec || rec.is_active ? "checked" : ""}>
        <label class="form-check-label" for="rActive" data-i18n="recurring_active">Active (uncheck to pause)</label>
      </div>
      ${
        rec
          ? ""
          : `<div class="form-check mb-2">
        <input class="form-check-input" type="checkbox" id="rBackfill">
        <label class="form-check-label" for="rBackfill" data-i18n="recurring_backfill_missed">Also post missed past occurrences (off by default)</label>
      </div>`
      }
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal()" data-i18n="btn_cancel">Cancel</button>
      <button class="btn btn-primary" onclick="saveRecurring(${rec ? rec.id : "null"})" data-i18n="btn_save">Save</button>
    </div>`;
  showModal(html);
  applyTranslations();
}
