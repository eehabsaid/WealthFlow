"use strict";
// commitments_calendar/shared.js — toolbar, event card builders and small
// helpers shared by the month / week / agenda views. Siblings: nav.js (dates
// and navigation), month_view.js, week_view.js, agenda_view.js, risk_panel.js.

const COMMITMENTS_SOURCE_KEYS = {
  SalaryEntry: "commitments_source_salary",
  AssetRental: "commitments_source_rental",
  AssetMortgage: "commitments_source_mortgage",
  BankCertificate: "commitments_source_certificate",
  RecurringTransaction: "commitments_source_recurring",
  AssetSale: "commitments_source_asset_sale",
  AssetInsurance: "commitments_source_insurance",
  VehicleDetails: "commitments_source_vehicle",
};

function _commitmentsEventColor(event) {
  if (event.category === "income") return "var(--success-color, #2ecc71)";
  if (event.category === "expense") return "var(--danger-color, #e74c3c)";
  return "var(--warning-color, #f39c12)"; // renewal
}

function _commitmentsEventLabel(event) {
  const extra = event.extra || {};
  const detail = extra.name || extra.company || extra.plate || extra.tenant || "";
  const text = t(event.description_key, event.description_key);
  return detail ? `${text} · ${detail}` : text;
}

function _commitmentsSourceLabel(event) {
  const key = COMMITMENTS_SOURCE_KEYS[event.source];
  return key ? t(key) : "";
}

function _commitmentsAmountText(event) {
  if (event.amount === 0 && event.amount_base === null) return "";
  const base = event.amount_base !== null ? event.amount_base : event.amount;
  let text = _money(base);
  if (event.currency_code && event.amount_base === null) text += ` ${event.currency_code}`;
  return text;
}

function _commitmentsKindBadge(event) {
  const map = {
    actual: ["commitments_kind_actual", "var(--success-color, #2ecc71)"],
    expected: ["commitments_kind_expected", "var(--info-color, #3498db)"],
    informational: ["commitments_kind_informational", "var(--text-secondary)"],
  };
  const [key, color] = map[event.kind] || map.informational;
  return `<span class="badge" style="background:transparent; color:${color}; border:1px solid ${color}; font-weight:500;">${_escapeHtml(t(key))}</span>`;
}

function _commitmentsEventCard(event, compact = false) {
  const color = _commitmentsEventColor(event);
  const amount = _commitmentsAmountText(event);
  return `<div class="commitments-event-card" data-date="${event.date}" style="border-inline-start:3px solid ${color}; background:var(--bg-primary); border-radius:8px; padding:${compact ? "6px 10px" : "10px 12px"}; margin-bottom:6px; cursor:default;">
    <div style="display:flex; justify-content:space-between; gap:8px; align-items:baseline;">
      <span style="font-weight:600; color:var(--text-primary); font-size:${compact ? "0.85rem" : "0.9rem"};">${_escapeHtml(_commitmentsEventLabel(event))}</span>
      ${amount ? `<span style="font-weight:700; color:${color}; white-space:nowrap;">${amount}</span>` : ""}
    </div>
    <div style="display:flex; gap:6px; align-items:center; margin-top:3px; flex-wrap:wrap;">
      ${_commitmentsKindBadge(event)}
      <span style="color:var(--text-secondary); font-size:0.75rem;">${_escapeHtml(_commitmentsSourceLabel(event))}</span>
    </div>
  </div>`;
}

function _commitmentsToolbarHtml() {
  const range = _commitmentsRange();
  const currentMonth = _commitmentsLocalMonth(_commitmentsAnchor);
  const months = Array.from({ length: 12 }, (_, i) => {
    const d = new Date(range.start.getFullYear(), range.start.getMonth() + i, 1);
    const value = _commitmentsLocalMonth(d);
    return `<option value="${value}" ${value === currentMonth ? "selected" : ""}>${_escapeHtml(_commitmentsMonthYear(d))}</option>`;
  });
  const banks =
    (_commitmentsData && _commitmentsData.filters && _commitmentsData.filters.banks) || [];
  const bankOptions = banks
    .map(
      (b) =>
        `<option value="${b.id}" ${String(_commitmentsBank) === String(b.id) ? "selected" : ""}>${_escapeHtml(b.name)}</option>`
    )
    .join("");
  const navDisabled = (delta) => (_commitmentsCanShift(delta) ? "" : "disabled");
  const navigation =
    _commitmentsView === "agenda"
      ? ""
      : `<div class="btn-group" role="group" aria-label="${_escapeHtml(t("commitments_aria_navigation"))}">
      <button type="button" class="btn btn-sm btn-outline-secondary" data-commitments-nav="-1" ${navDisabled(-1)} aria-label="${_escapeHtml(t("commitments_aria_previous"))}"><i class="bi bi-chevron-left"></i></button>
      <select class="form-select form-select-sm" id="commitments-month-select" style="width:auto; min-width:150px;" aria-label="${_escapeHtml(t("commitments_aria_month"))}">${months.join("")}</select>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-commitments-nav="1" ${navDisabled(1)} aria-label="${_escapeHtml(t("commitments_aria_next"))}"><i class="bi bi-chevron-right"></i></button>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-commitments-today data-i18n="commitments_today"></button>
    </div>`;
  return `
  <div class="d-flex flex-wrap gap-2 align-items-center" style="row-gap:8px;">
    <div class="btn-group" role="group" aria-label="${_escapeHtml(t("commitments_aria_view"))}">
      ${["month", "week", "agenda"].map((v) => `<button type="button" class="btn btn-sm ${_commitmentsView === v ? "btn-primary" : "btn-outline-primary"}" data-commitments-view="${v}" data-i18n="commitments_view_${v}"></button>`).join("")}
    </div>
    ${navigation}
    <select class="form-select form-select-sm" id="commitments-category-filter" style="width:auto;" aria-label="${_escapeHtml(t("commitments_aria_category"))}">
      <option value="" data-i18n="commitments_category_all"></option>
      <option value="income" data-i18n="commitments_category_income"></option>
      <option value="expense" data-i18n="commitments_category_expense"></option>
      <option value="renewal" data-i18n="commitments_category_renewal"></option>
    </select>
    <select class="form-select form-select-sm" id="commitments-bank-filter" style="width:auto;" aria-label="${_escapeHtml(t("commitments_aria_bank"))}">
      <option value="" data-i18n="commitments_filter_bank"></option>
      ${bankOptions}
    </select>
  </div>`;
}

function _renderCommitmentsToolbar() {
  const host = document.getElementById("commitments-toolbar");
  if (!host) return;
  host.innerHTML = _commitmentsToolbarHtml();
  const monthSelect = document.getElementById("commitments-month-select");
  if (monthSelect) {
    monthSelect.addEventListener("change", () => {
      const [y, m] = monthSelect.value.split("-").map(Number);
      _setCommitmentsAnchor(new Date(y, m - 1, 1));
    });
  }
  host
    .querySelectorAll("[data-commitments-view]")
    .forEach((btn) =>
      btn.addEventListener("click", () => _setCommitmentsView(btn.dataset.commitmentsView))
    );
  host
    .querySelectorAll("[data-commitments-nav]")
    .forEach((btn) =>
      btn.addEventListener("click", () =>
        _setCommitmentsAnchor(_commitmentsShifted(Number(btn.dataset.commitmentsNav)))
      )
    );
  const todayBtn = host.querySelector("[data-commitments-today]");
  if (todayBtn) todayBtn.addEventListener("click", () => _setCommitmentsAnchor(new Date()));
  const cat = document.getElementById("commitments-category-filter");
  cat.value = _commitmentsCategory || "";
  cat.addEventListener("change", () => _applyCommitmentsFilter(cat.value, _commitmentsBank));
  const bank = document.getElementById("commitments-bank-filter");
  bank.value = _commitmentsBank || "";
  bank.addEventListener("change", () => _applyCommitmentsFilter(_commitmentsCategory, bank.value));
}

// Month view: selecting a day (click or Enter/Space) lists its events below the grid.
function _showCommitmentsDay(date) {
  const host = document.getElementById("commitments-day-detail");
  if (!host) return;
  const events = (_commitmentsData ? _commitmentsData.events : []).filter((e) => e.date === date);
  const title = _escapeHtml(_commitmentsShowDate(date));
  host.innerHTML = events.length
    ? `<div class="mt-3"><div style="font-weight:700; color:var(--text-primary); margin-bottom:8px;">${title}</div>${events.map((e) => _commitmentsEventCard(e)).join("")}</div>`
    : `<div class="mt-3" style="color:var(--text-secondary);">${title} — ${_escapeHtml(t("commitments_day_empty"))}</div>`;
}

function _wireCommitmentsView() {
  document.querySelectorAll("[data-commitments-day]").forEach((cell) => {
    const open = () => _showCommitmentsDay(cell.dataset.commitmentsDay);
    cell.addEventListener("click", open);
    cell.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });
  });
}
