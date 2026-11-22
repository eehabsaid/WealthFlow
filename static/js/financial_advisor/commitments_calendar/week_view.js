"use strict";
// commitments_calendar/week_view.js — 7-day week view around the anchor month's first week.

function _commitmentsWeekDays() {
  const first = new Date(_commitmentsAnchor.getFullYear(), _commitmentsAnchor.getMonth(), 1);
  const startOffset = (first.getDay() + 6) % 7;
  const start = new Date(first);
  start.setDate(first.getDate() - startOffset);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return d;
  });
}

function _renderCommitmentsWeekView(events) {
  const byDate = _commitmentsEventsByDate(events);
  const days = _commitmentsWeekDays();
  const today = _commitmentsLocalISO(new Date());
  const lang =
    currentLang() === "ar"
      ? "ar"
      : currentLang() === "fr"
        ? "fr"
        : currentLang() === "de"
          ? "de"
          : "en";

  const cols = days
    .map((d) => {
      const iso = _commitmentsLocalISO(d);
      const dayEvents = byDate[iso] || [];
      return `<div style="background:${iso === today ? "var(--bg-primary)" : "var(--bg-secondary)"}; border:1px solid var(--border-color); border-radius:8px; padding:8px; min-height:120px;">
        <div style="font-weight:700; color:var(--text-primary); margin-bottom:6px; font-size:0.85rem;">
          ${d.toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short" })}
        </div>
        ${dayEvents.length ? dayEvents.map((e) => _commitmentsEventCard(e, true)).join("") : `<div style="color:var(--text-secondary); font-size:0.78rem;" data-i18n="commitments_day_empty"></div>`}
      </div>`;
    })
    .join("");

  return `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:16px;">
        <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:8px;">${cols}</div>
      </div>
    </div>
  `;
}
