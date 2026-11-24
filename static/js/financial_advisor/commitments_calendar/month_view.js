"use strict";
// commitments_calendar/month_view.js — month grid view (weeks start on the user's first day of the week).

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
  const gridFirst = _commitmentsWeekStartOf(first);
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
        return `<span class="commitments-chip" style="--chip-color:${_commitmentsEventColor(e)};" title="${label}">${label}</span>`;
      })
      .join("");
    const more =
      dayEvents.length > 3 ? `<span class="commitments-more">+${dayEvents.length - 3}</span>` : "";
    const isToday = iso === today;
    cells += `<div class="commitments-day-cell${inMonth ? "" : " commitments-out-month"}${isToday ? " commitments-today" : ""}"${isToday ? ' aria-current="date"' : ""} data-commitments-day="${iso}" role="button" tabindex="0" aria-label="${_escapeHtml(_commitmentsShowDate(iso))}">
      <div class="commitments-day-num">${d.getDate()}</div>
      <div class="commitments-chips">${chips}${more}</div>
    </div>`;
  }

  const headers = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(gridFirst);
    d.setDate(gridFirst.getDate() + i);
    return `<div class="commitments-weekday">${_escapeHtml(_commitmentsWeekday(d))}</div>`;
  }).join("");

  return `
    <div class="card border-0 commitments-card">
      <div class="card-body commitments-card-body">
        <div style="font-weight:700; color:var(--text-primary); margin-bottom:12px; font-size:1.05rem;">
          ${_escapeHtml(_commitmentsMonthYear(first))}
        </div>
        <div class="commitments-weekdays">${headers}</div>
        <div class="commitments-month-grid">${cells}</div>
      </div>
    </div>
    <div id="commitments-day-detail"></div>
  `;
}
