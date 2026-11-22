"use strict";
// commitments_calendar/index.js — Financial Commitments Calendar tab.
// One backend payload (date range + filters) drives three frontend views:
// month, week, agenda. Siblings: month_view.js, week_view.js, agenda_view.js,
// risk_panel.js, shared.js (state + small helpers).
// Read-only feature: it never posts expenses or changes balances.

let _commitmentsData = null;
let _commitmentsView = "month";
let _commitmentsCategory = "";
let _commitmentsBank = "";
let _commitmentsAnchor = new Date(); // first day of the month being shown
let _commitmentsLoading = false;

function _commitmentsPaneId() {
  return "fa-commitments-calendar-content";
}

function _commitmentsRange() {
  // 12-month window starting at the first day of the current month (API max is 366 days).
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 11, 0);
  return { start, end };
}

function _commitmentsInWindow(d) {
  const { start, end } = _commitmentsRange();
  return d >= start && d <= end;
}

async function loadCommitmentsCalendar(force = false) {
  if (_commitmentsData && !force) {
    _renderCommitmentsCalendar();
    return;
  }
  const pane = document.getElementById(_commitmentsPaneId());
  if (!pane) return;
  if (_commitmentsLoading) return;
  _commitmentsLoading = true;
  pane.innerHTML = `<div class="text-center py-5" style="color:var(--text-secondary);">
    <div class="spinner-border spinner-border-sm me-2"></div><span data-i18n="commitments_loading"></span></div>`;
  applyTranslations();
  try {
    const { start, end } = _commitmentsRange();
    const params = new URLSearchParams();
    params.set("start_date", _commitmentsLocalISO(start));
    params.set("end_date", _commitmentsLocalISO(end));
    if (_commitmentsCategory) params.set("category", _commitmentsCategory);
    if (_commitmentsBank) params.set("bank", _commitmentsBank);
    const response = await fetch(
      `/api/financial-advisor/commitments-calendar/?${params.toString()}`
    );
    if (!response.ok) throw new Error("commitments_fetch_failed");
    _commitmentsData = await response.json();
    _renderCommitmentsCalendar();
  } catch (error) {
    _renderCommitmentsError();
  } finally {
    _commitmentsLoading = false;
  }
}

function _renderCommitmentsCalendar() {
  const pane = document.getElementById(_commitmentsPaneId());
  if (!pane || !_commitmentsData) return;
  const events = _commitmentsData.events || [];
  const analysis = _commitmentsData.analysis || {};
  pane.innerHTML = `
    <div class="mb-3" id="commitments-toolbar"></div>
    <div class="mb-4" id="commitments-risk-panel"></div>
    <div id="commitments-view"></div>
  `;
  _renderCommitmentsToolbar();
  _renderCommitmentsRiskPanel(analysis);
  _renderCommitmentsView(events);
  applyTranslations();
}

function _renderCommitmentsView(events) {
  const host = document.getElementById("commitments-view");
  if (!host) return;
  if (_commitmentsView === "week") {
    host.innerHTML = _renderCommitmentsWeekView(events);
  } else if (_commitmentsView === "agenda") {
    host.innerHTML = _renderCommitmentsAgendaView(events);
  } else {
    host.innerHTML = _renderCommitmentsMonthView(events);
  }
  _wireCommitmentsView();
}

function _setCommitmentsView(view) {
  if (view !== _commitmentsView) {
    _commitmentsView = view;
    _renderCommitmentsView(_commitmentsData ? _commitmentsData.events || [] : []);
  }
}

function _setCommitmentsAnchor(deltaMonths) {
  _commitmentsAnchor = new Date(
    _commitmentsAnchor.getFullYear(),
    _commitmentsAnchor.getMonth() + deltaMonths,
    1
  );
  _renderCommitmentsView(_commitmentsData ? _commitmentsData.events || [] : []);
}

function _applyCommitmentsFilter(category, bank) {
  _commitmentsCategory = category || "";
  _commitmentsBank = bank || "";
  loadCommitmentsCalendar(true);
}

function _renderCommitmentsError() {
  const pane = document.getElementById(_commitmentsPaneId());
  if (!pane) return;
  pane.innerHTML = `<div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
    <div class="card-body" style="padding:32px; text-align:center; color:var(--text-secondary);">
      <i class="bi bi-exclamation-triangle me-2"></i><span data-i18n="commitments_error"></span>
    </div></div>`;
  applyTranslations();
}
