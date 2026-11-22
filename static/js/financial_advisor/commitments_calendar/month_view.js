"use strict";
// commitments_calendar/month_view.js — month grid view.

function _commitmentsEventsByDate(events) {
  const map = {};
  for (const e of events) {
    (map[e.date] = map[e.date] || []).push(e);
  }
  return map;
}

function _commitmentsDayName(offset) {
  // Header column `offset` must be the weekday of the SAME grid day the cell
  // loop renders there. The grid starts on the Monday on/ before the 1st
  // (startOffset = (getDay()+6)%7), so derive the header from that grid first
  // day — not from the 1st — or the labels shift a column vs the dates.
  const first = new Date(_commitmentsAnchor.getFullYear(), _commitmentsAnchor.getMonth(), 1);
  const startOffset = (first.getDay() + 6) % 7;
  const gridFirst = new Date(first);
  gridFirst.setDate(first.getDate() - startOffset);
  const d = new Date(gridFirst);
  d.setDate(gridFirst.getDate() + offset);
  return d.toLocaleDateString(
    currentLang() === "ar"
      ? "ar"
      : currentLang() === "fr"
        ? "fr"
        : currentLang() === "de"
          ? "de"
          : "en",
    { weekday: "short" }
  );
}

function _renderCommitmentsMonthView(events) {
  const byDate = _commitmentsEventsByDate(events);
  const first = new Date(_commitmentsAnchor.getFullYear(), _commitmentsAnchor.getMonth(), 1);
  const startOffset = (first.getDay() + 6) % 7; // week starts on Monday
  const today = _commitmentsLocalISO(new Date());

  let cells = "";
  for (let i = 0; i < 42; i++) {
    const d = new Date(first);
    d.setDate(first.getDate() - startOffset + i);
    const iso = _commitmentsLocalISO(d);
    const inMonth = d.getMonth() === first.getMonth();
    const dayEvents = byDate[iso] || [];
    const chips = dayEvents
      .slice(0, 3)
      .map(
        (e) =>
          `<span class="commitments-chip" style="display:inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis; border-inline-start:3px solid ${_commitmentsEventColor(e)}; background:var(--bg-secondary); border-radius:4px; padding:1px 5px; margin:1px; font-size:0.72rem; color:var(--text-primary); white-space:nowrap;" title="${_escapeHtml(_commitmentsEventLabel(e))}">${_escapeHtml(_commitmentsEventLabel(e))}</span>`
      )
      .join("");
    const more =
      dayEvents.length > 3
        ? `<span style="font-size:0.72rem; color:var(--text-secondary);">+${dayEvents.length - 3}</span>`
        : "";
    cells += `<div class="commitments-day-cell" data-commitments-day="${iso}" role="button" tabindex="0" style="min-height:84px; background:${inMonth ? "var(--bg-primary)" : "var(--bg-secondary)"}; border:1px solid var(--border-color); border-radius:8px; padding:6px; cursor:pointer;">
      <div style="font-size:0.75rem; font-weight:${iso === today ? 800 : 600}; color:${iso === today ? "var(--primary-color, #3b82f6)" : "var(--text-secondary)"}; margin-bottom:3px;">${d.getDate()}</div>
      ${chips}${more}
    </div>`;
  }

  return `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:16px;">
        <div style="font-weight:700; color:var(--text-primary); margin-bottom:12px; font-size:1.05rem;">
          ${first.toLocaleDateString(currentLang() === "ar" ? "ar" : currentLang() === "fr" ? "fr" : currentLang() === "de" ? "de" : "en", { month: "long", year: "numeric" })}
        </div>
        <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:6px; margin-bottom:8px;">
          ${Array.from({ length: 7 }, (_, i) => `<div style="text-align:center; font-size:0.75rem; font-weight:600; color:var(--text-secondary);">${_commitmentsDayName(i)}</div>`).join("")}
        </div>
        <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:6px;">${cells}</div>
      </div>
    </div>
    <div id="commitments-day-detail"></div>
  `;
}
