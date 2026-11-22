"use strict";
// commitments_calendar/shared.js — toolbar, event card/chip builders and
// small helpers shared by the month / week / agenda views.

// Date helpers — the backend sends date-only "YYYY-MM-DD" calendar dates.
// A cell/date key must always be derived from LOCAL calendar components,
// never from Date.toISOString(): that is UTC, so in any non-UTC timezone it
// shifts the day (e.g. local Dec 2 00:00 in UTC+2 is Dec 1 22:00 UTC), which
// put events one cell ahead on the grid.
function _commitmentsLocalISO(d) {
  return (
    d.getFullYear() +
    "-" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(d.getDate()).padStart(2, "0")
  );
}
function _commitmentsLocalMonth(d) {
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
}
function _commitmentsDateFromISO(iso) {
  const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

function _commitmentsEventColor(event) {
  if (event.category === "income") return "var(--success-color, #2ecc71)";
  if (event.category === "expense") return "var(--danger-color, #e74c3c)";
  return "var(--warning-color, #f39c12)"; // renewal
}

function _commitmentsEventLabel(event) {
  const key = event.description_key || "";
  const text = t(key, event.extra && event.extra.name ? event.extra.name : key);
  return event.extra && event.extra.name ? `${text} · ${event.extra.name}` : text;
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
  return `<span class="badge" style="background:transparent; color:${color}; border:1px solid ${color}; font-weight:500;" data-i18n="${key}"></span>`;
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
      <span style="color:var(--text-secondary); font-size:0.75rem;">${event.source || ""}</span>
    </div>
  </div>`;
}

function _commitmentsToolbarHtml() {
  const currentMonth = _commitmentsLocalMonth(_commitmentsAnchor);
  const months = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(_commitmentsAnchor.getFullYear(), _commitmentsAnchor.getMonth() + i, 1);
    months.push(
      `<option value="${_commitmentsLocalMonth(d)}" ${_commitmentsLocalMonth(d) === currentMonth ? "selected" : ""}>${d.toLocaleDateString(currentLang() === "ar" ? "ar" : currentLang() === "fr" ? "fr" : currentLang() === "de" ? "de" : "en", { month: "long", year: "numeric" })}</option>`
    );
  }
  const banks =
    (_commitmentsData && _commitmentsData.filters && _commitmentsData.filters.banks) || [];
  const bankOptions = banks
    .map(
      (b) =>
        `<option value="${b.id}" ${String(_commitmentsBank) === String(b.id) ? "selected" : ""}>${_escapeHtml(b.name)}</option>`
    )
    .join("");
  return `
  <div class="d-flex flex-wrap gap-2 align-items-center" style="row-gap:8px;">
    <div class="btn-group" role="group" aria-label="commitments view">
      ${["month", "week", "agenda"].map((v) => `<button type="button" class="btn btn-sm ${_commitmentsView === v ? "btn-primary" : "btn-outline-primary"}" data-commitments-view="${v}" data-i18n="commitments_view_${v}"></button>`).join("")}
    </div>
    <div class="btn-group" role="group" aria-label="commitments navigation">
      <button type="button" class="btn btn-sm btn-outline-secondary" data-commitments-nav="-1" aria-label="previous"><i class="bi bi-chevron-left"></i></button>
      <select class="form-select form-select-sm" id="commitments-month-select" style="width:auto; min-width:150px;" aria-label="month">
        ${months.join("")}
      </select>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-commitments-nav="1" aria-label="next"><i class="bi bi-chevron-right"></i></button>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-commitments-today data-i18n="commitments_today"></button>
    </div>
    <select class="form-select form-select-sm" id="commitments-category-filter" style="width:auto;" aria-label="category">
      <option value="" data-i18n="commitments_category_all"></option>
      <option value="income" data-i18n="commitments_category_income"></option>
      <option value="expense" data-i18n="commitments_category_expense"></option>
      <option value="renewal" data-i18n="commitments_category_renewal"></option>
    </select>
    <select class="form-select form-select-sm" id="commitments-bank-filter" style="width:auto;" aria-label="bank">
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
    const cur = _commitmentsLocalMonth(_commitmentsAnchor);
    const opt = Array.from(monthSelect.options).find((o) => o.value === cur);
    if (opt) opt.selected = true;
    monthSelect.addEventListener("change", () => {
      const [y, m] = monthSelect.value.split("-").map(Number);
      _commitmentsAnchor = new Date(y, m - 1, 1);
      _renderCommitmentsView(_commitmentsData ? _commitmentsData.events || [] : []);
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
      btn.addEventListener("click", () => _setCommitmentsAnchor(Number(btn.dataset.commitmentsNav)))
    );
  const todayBtn = host.querySelector("[data-commitments-today]");
  if (todayBtn)
    todayBtn.addEventListener("click", () => {
      _commitmentsAnchor = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
      _renderCommitmentsView(_commitmentsData ? _commitmentsData.events || [] : []);
    });
  const cat = document.getElementById("commitments-category-filter");
  if (cat) {
    cat.value = _commitmentsCategory || "";
    cat.addEventListener("change", () => _applyCommitmentsFilter(cat.value, _commitmentsBank));
  }
  const bank = document.getElementById("commitments-bank-filter");
  if (bank) {
    bank.value = _commitmentsBank || "";
    bank.addEventListener("change", () =>
      _applyCommitmentsFilter(_commitmentsCategory, bank.value)
    );
  }
}

function _wireCommitmentsView() {
  // Month view: clicking a day cell lists that day's events below the grid.
  document.querySelectorAll("[data-commitments-day]").forEach((cell) =>
    cell.addEventListener("click", () => {
      const date = cell.dataset.commitmentsDay;
      const events = (_commitmentsData ? _commitmentsData.events : []).filter(
        (e) => e.date === date
      );
      const host = document.getElementById("commitments-day-detail");
      if (!host) return;
      host.innerHTML = events.length
        ? `<div class="mt-3"><div style="font-weight:700; color:var(--text-primary); margin-bottom:8px;">${date}</div>${events.map((e) => _commitmentsEventCard(e)).join("")}</div>`
        : `<div class="mt-3" style="color:var(--text-secondary);">${date} — <span data-i18n="commitments_day_empty"></span></div>`;
      applyTranslations();
    })
  );
}
