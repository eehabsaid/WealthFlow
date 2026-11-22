"use strict";
// commitments_calendar/agenda_view.js — chronological agenda list grouped by month.

function _commitmentsAgendaRow(e) {
  const date = _commitmentsDateFromISO(e.date);
  const balance =
    e.projected_balance !== undefined
      ? `${_escapeHtml(t("commitments_projected_balance"))} ${_money(e.projected_balance)}`
      : "";
  return `<div class="commitments-agenda-row" style="display:flex; gap:12px; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-color);">
    <div style="min-width:56px; text-align:center;">
      <div style="font-weight:800; color:var(--text-primary); font-size:1.05rem;">${date.getDate()}</div>
      <div style="font-size:0.72rem; color:var(--text-secondary);">${_escapeHtml(_commitmentsWeekday(date))}</div>
    </div>
    <div style="flex:1; min-width:0;">
      <div style="font-weight:600; color:var(--text-primary);">${_escapeHtml(_commitmentsEventLabel(e))}</div>
      <div style="font-size:0.75rem; color:var(--text-secondary);">${_escapeHtml(_commitmentsSourceLabel(e))} ${_commitmentsKindBadge(e)}</div>
    </div>
    <div style="text-align:end; white-space:nowrap;">
      <div style="font-weight:700; color:${_commitmentsEventColor(e)};">${_commitmentsAmountText(e)}</div>
      <div style="font-size:0.72rem; color:var(--text-secondary);">${balance}</div>
    </div>
  </div>`;
}

function _renderCommitmentsAgendaView(events) {
  if (!events.length) {
    return `<div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:32px; text-align:center; color:var(--text-secondary);">
        <i class="bi bi-calendar3 me-2"></i><span>${_escapeHtml(t("commitments_empty"))}</span>
      </div></div>`;
  }
  const groups = {};
  for (const e of events) {
    (groups[e.date.slice(0, 7)] = groups[e.date.slice(0, 7)] || []).push(e);
  }
  const sections = Object.keys(groups)
    .sort()
    .map((key) => {
      const [y, m] = key.split("-").map(Number);
      return `<div class="mb-3">
        <div style="font-weight:700; color:var(--text-primary); margin-bottom:4px; font-size:0.95rem;">${_escapeHtml(_commitmentsMonthYear(new Date(y, m - 1, 1)))}</div>
        ${groups[key].map(_commitmentsAgendaRow).join("")}
      </div>`;
    })
    .join("");

  return `<div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
    <div class="card-body" style="padding:16px;">${sections}</div>
  </div>`;
}
