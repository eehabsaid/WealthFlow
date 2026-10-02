"use strict";

function _budgetAlertHtml(alert) {
  const iconByType = {
    budget_exceeded: "bi-exclamation-octagon-fill text-danger",
    budget_threshold: "bi-exclamation-triangle-fill text-warning",
    recurring_due_soon: "bi-clock-fill text-info",
    recurring_overdue: "bi-alarm-fill text-danger",
  };
  let text = "";
  if (alert.type === "budget_exceeded") {
    text = `${alert.budget_name}: ${alert.percent_used}% ${t("budget_alert_exceeded_suffix", "of budget used")}`;
  } else if (alert.type === "budget_threshold") {
    text = `${alert.budget_name}: ${alert.percent_used}% ${t("budget_alert_threshold_suffix", "of budget used")}`;
  } else if (alert.type === "recurring_due_soon") {
    text = `${alert.recurring_name} ${t("recurring_due_on", "due on")} ${alert.next_run_date}`;
  } else {
    text = `${alert.recurring_name} ${t("recurring_overdue_since", "overdue since")} ${alert.next_run_date}`;
  }
  return `<div class="d-flex align-items-center gap-2 py-1"><i class="bi ${iconByType[alert.type] || "bi-info-circle"}"></i><span>${text}</span></div>`;
}

function _budgetRowHtml(b) {
  const percent = Math.min(b.percent_used || 0, 100);
  const barClass =
    b.percent_used >= 100
      ? "bg-danger"
      : b.percent_used >= b.alert_threshold_percent
        ? "bg-warning"
        : "bg-success";
  return `
    <div class="card mb-2" style="background:var(--bg-secondary);border:1px solid var(--border-color)">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <strong>${b.category_icon || "💰"} ${b.name}</strong>
            <div class="text-secondary" style="font-size:12px">${b.category_name || t("budget_all_categories", "All categories")} · <span data-i18n="period_${b.period}">${b.period}</span></div>
          </div>
          <div class="d-flex gap-2">
            <button class="btn-icon" onclick="showBudgetModal(${JSON.stringify(b).replace(/"/g, "&quot;")})"><i class="bi bi-pencil"></i></button>
            <button class="btn-icon" onclick="deleteBudget(${b.id})"><i class="bi bi-trash"></i></button>
          </div>
        </div>
        <div class="progress mt-2" style="height:8px">
          <div class="progress-bar ${barClass}" style="width:${percent}%"></div>
        </div>
        <div class="d-flex justify-content-between mt-1" style="font-size:12px">
          <span>${(b.spent_base || 0).toFixed(2)} / ${b.amount_base.toFixed(2)} ${b.currency_code}</span>
          <span>${b.percent_used}%</span>
        </div>
      </div>
    </div>`;
}

function _recurringRowHtml(r) {
  return `
    <div class="card mb-2" style="background:var(--bg-secondary);border:1px solid var(--border-color)">
      <div class="card-body d-flex justify-content-between align-items-center">
        <div>
          <strong>${r.name}</strong>
          <div class="text-secondary" style="font-size:12px">
            ${r.amount} ${r.currency_code} · <span data-i18n="frequency_${r.frequency}">${r.frequency}</span>
            · <span data-i18n="recurring_next_run">Next</span>: ${r.next_run_date}
            ${r.is_active ? "" : `· <span class="text-danger" data-i18n="recurring_inactive">Inactive</span>`}
          </div>
        </div>
        <div class="d-flex gap-2">
          <button class="btn-icon" title="${r.is_active ? t("recurring_pause", "Pause") : t("recurring_resume", "Resume")}" onclick="toggleRecurringActive(${r.id}, ${!r.is_active})"><i class="bi ${r.is_active ? "bi-pause-circle" : "bi-play-circle"}"></i></button>
          <button class="btn-icon" onclick="showRecurringModal(${JSON.stringify(r).replace(/"/g, "&quot;")})"><i class="bi bi-pencil"></i></button>
          <button class="btn-icon" onclick="deleteRecurring(${r.id})"><i class="bi bi-trash"></i></button>
        </div>
      </div>
    </div>`;
}

async function renderBudgets() {
  const mc = document.getElementById("main-content");
  mc.innerHTML =
    '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

  const [budgetsRes, recurringRes, alertsRes, catRes, curRes, bankRes] = await Promise.all([
    fetch("/api/budgets/"),
    fetch("/api/recurring-transactions/"),
    fetch("/api/budgets/alerts/"),
    fetch("/api/expense-categories/"),
    fetch("/api/currencies/"),
    fetch("/api/banks/"),
  ]);
  const budgets = (await budgetsRes.json()).budgets || [];
  const recurring = (await recurringRes.json()).recurring_transactions || [];
  const alerts = (await alertsRes.json()).alerts || [];
  window._expCategories = (await catRes.json()).categories || [];
  window._expCurrencies = (await curRes.json()).currencies || [];
  window._expBanks = ((await bankRes.json()).banks || []).filter((b) => b.is_active !== false);

  mc.innerHTML = `
    <div class="container-fluid p-3">
      ${
        alerts.length
          ? `<div class="card mb-3" style="background:var(--bg-secondary);border:1px solid var(--border-color)">
              <div class="card-body">
                <h6 data-i18n="budget_alerts">Alerts</h6>
                ${alerts.map(_budgetAlertHtml).join("")}
              </div>
            </div>`
          : ""
      }
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h5 data-i18n="nav_budgets">Budgets</h5>
      </div>
      ${budgets.length ? budgets.map(_budgetRowHtml).join("") : `<p class="text-secondary" data-i18n="no_budgets_yet">No budgets yet.</p>`}

      <div class="d-flex justify-content-between align-items-center mt-4 mb-2">
        <h5 data-i18n="nav_recurring_transactions">Recurring Transactions</h5>
        <div class="d-flex gap-2">
          <button class="btn btn-outline-secondary btn-sm" onclick="processDueRecurring()" data-i18n="btn_process_due">Post Due Now</button>
          <button class="btn btn-primary btn-sm" onclick="showRecurringModal(null)" data-i18n="btn_add_recurring">Add Recurring</button>
        </div>
      </div>
      ${recurring.length ? recurring.map(_recurringRowHtml).join("") : `<p class="text-secondary" data-i18n="no_recurring_yet">No recurring transactions yet.</p>`}
    </div>`;
  applyTranslations();
}
