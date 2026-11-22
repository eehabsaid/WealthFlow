"use strict";
// commitments_calendar/month_view.js — month grid view (weeks start on Monday).

function _commitmentsEventsByDate(events) {
  const map = {};
  for (const e of events) {
    (map[e.date] = map[e.date] || []).push(e);
  }
  return map;
}

function _renderCommitmentsMonthView(events) {
  const byDate = _commitmentsEventsByDate(events);
  const first = new Date(_commitmentsAnchor.getFullYear(), _commitmentsAnchor.getMonth(), 1);
  const gridFirst = _commitmentsMondayOf(first);
  const today = _commitmentsLocalISO(new Date());

  let cells = "";
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridFirst);
    d.setDate(gridFirst.getDate() + i);
    const iso = _commitmentsLocalISO(d);
    const inMonth = d.getMonth() === first.getMonth();
    const dayEvents = byDate[iso] || [];
    const chips = dayEvents
      .slice(0, 3)
      .map((e) => {
        const label = _escapeHtml(_commitmentsEventLabel(e));
        return `<span class="commitments-chip" style="display:inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis; border-inline-start:3px solid ${_commitmentsEventColor(e)}; background:var(--bg-secondary); border-radius:4px; padding:1px 5px; margin:1px; font-size:0.72rem; color:var(--text-primary); white-space:nowrap;" title="${label}">${label}</span>`;
      })
      .join("");
    const more =
      dayEvents.length > 3
        ? `<span style="font-size:0.72rem; color:var(--text-secondary);">+${dayEvents.length - 3}</span>`
        : "";
    cells += `<div class="commitments-day-cell" data-commitments-day="${iso}" role="button" tabindex="0" aria-label="${_escapeHtml(_commitmentsShowDate(iso))}" style="min-height:84px; background:${inMonth ? "var(--bg-primary)" : "var(--bg-secondary)"}; border:1px solid var(--border-color); border-radius:8px; padding:6px; cursor:pointer;">
      <div style="font-size:0.75rem; font-weight:${iso === today ? 800 : 600}; color:${iso === today ? "var(--primary-color, #3b82f6)" : "var(--text-secondary)"}; margin-bottom:3px;">${d.getDate()}</div>
      ${chips}${more}
    </div>`;
  }

  const headers = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(gridFirst);
    d.setDate(gridFirst.getDate() + i);
    return `<div style="text-align:center; font-size:0.75rem; font-weight:600; color:var(--text-secondary);">${_escapeHtml(_commitmentsWeekday(d))}</div>`;
  }).join("");

  return `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:16px;">
        <div style="font-weight:700; color:var(--text-primary); margin-bottom:12px; font-size:1.05rem;">
          ${_escapeHtml(_commitmentsMonthYear(first))}
        </div>
        <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:6px; margin-bottom:8px;">${headers}</div>
        <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:6px;">${cells}</div>
      </div>
    </div>
    <div id="commitments-day-detail"></div>
  `;
}
