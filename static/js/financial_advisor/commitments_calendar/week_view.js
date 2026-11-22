"use strict";
// commitments_calendar/week_view.js — the 7-day week (starting on the user's first day of the week)
// containing the anchor date; the toolbar arrows move one week at a time.

function _renderCommitmentsWeekView(events) {
  const byDate = _commitmentsEventsByDate(events);
  const weekStart = _commitmentsWeekStartOf(_commitmentsAnchor);
  const today = _commitmentsLocalISO(new Date());

  const cols = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    const iso = _commitmentsLocalISO(d);
    const dayEvents = byDate[iso] || [];
    return `<div class="commitments-week-day" data-commitments-week-day="${iso}" style="background:${iso === today ? "var(--bg-primary)" : "var(--bg-secondary)"}; border:1px solid var(--border-color); border-radius:8px; padding:8px; min-height:120px;">
        <div style="font-weight:700; color:var(--text-primary); font-size:0.85rem;">${_escapeHtml(_commitmentsWeekday(d))}</div>
        <div style="color:var(--text-secondary); font-size:0.72rem; margin-bottom:6px;">${_escapeHtml(_commitmentsShowDate(iso))}</div>
        ${dayEvents.length ? dayEvents.map((e) => _commitmentsEventCard(e, true)).join("") : `<div style="color:var(--text-secondary); font-size:0.78rem;">${_escapeHtml(t("commitments_day_empty"))}</div>`}
      </div>`;
  }).join("");

  return `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:16px;">
        <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:8px;">${cols}</div>
      </div>
    </div>
  `;
}
