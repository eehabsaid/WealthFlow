"use strict";
// commitments_calendar/index.js — Financial Commitments Calendar tab.
// One backend payload (date range + filters) drives three frontend views:
// month, week, agenda. Siblings: nav.js, shared.js, month_view.js,
// week_view.js, agenda_view.js, risk_panel.js.
// Read-only feature: it never posts expenses or changes balances.

let _commitmentsData = null;
let _commitmentsView = "month";
let _commitmentsCategory = "";
let _commitmentsBank = "";
let _commitmentsAnchor = new Date(); // any day inside the month / week being shown
let _commitmentsLoading = false;

function _commitmentsPaneId() {
  return "fa-commitments-calendar-content";
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
  pane.innerHTML = `
    <div class="mb-3" id="commitments-toolbar"></div>
    <div class="mb-4" id="commitments-risk-panel"></div>
    <div id="commitments-view"></div>
  `;
  _renderCommitmentsToolbar();
  _renderCommitmentsRiskPanel(_commitmentsData.analysis || {});
  _renderCommitmentsView();
}

// Re-renders the active view from the loaded payload and re-applies
// translations, because every view contains data-i18n elements.
function _renderCommitmentsView() {
  const host = document.getElementById("commitments-view");
  if (!host) return;
  const events = _commitmentsData ? _commitmentsData.events || [] : [];
  if (_commitmentsView === "week") {
    host.innerHTML = _renderCommitmentsWeekView(events);
  } else if (_commitmentsView === "agenda") {
    host.innerHTML = _renderCommitmentsAgendaView(events);
  } else {
    host.innerHTML = _renderCommitmentsMonthView(events);
  }
  _wireCommitmentsView();
  applyTranslations();
}

// Toolbar state (active view, month, disabled arrows) depends on the view and anchor.
function _refreshCommitmentsView() {
  _renderCommitmentsToolbar();
  _renderCommitmentsView();
  applyTranslations();
}

function _setCommitmentsView(view) {
  if (view === _commitmentsView) return;
  _commitmentsView = view;
  _refreshCommitmentsView();
}

function _setCommitmentsAnchor(date) {
  _commitmentsAnchor = date;
  _refreshCommitmentsView();
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
