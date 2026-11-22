"use strict";
// commitments_calendar/agenda_view.js — chronological agenda list grouped by month.

function _renderCommitmentsAgendaView(events) {
  if (!events.length) {
    return `<div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:32px; text-align:center; color:var(--text-secondary);">
        <i class="bi bi-calendar3 me-2"></i><span data-i18n="commitments_empty"></span>
      </div></div>`;
  }
  const lang =
    currentLang() === "ar"
      ? "ar"
      : currentLang() === "fr"
        ? "fr"
        : currentLang() === "de"
          ? "de"
          : "en";
  const groups = {};
  for (const e of events) {
    const key = e.date.slice(0, 7);
    (groups[key] = groups[key] || []).push(e);
  }
  const sections = Object.keys(groups)
    .sort()
    .map((key) => {
      const [y, m] = key.split("-").map(Number);
      const label = new Date(y, m - 1, 1).toLocaleDateString(lang, {
        month: "long",
        year: "numeric",
      });
      const rows = groups[key]
        .map(
          (
            e
          ) => `<div style="display:flex; gap:12px; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-color);">
            <div style="min-width:56px; text-align:center;">
              <div style="font-weight:800; color:var(--text-primary); font-size:1.05rem;">${Number(e.date.slice(8, 10))}</div>
              <div style="font-size:0.72rem; color:var(--text-secondary);">${_commitmentsDateFromISO(e.date).toLocaleDateString(lang, { weekday: "short" })}</div>
            </div>
            <div style="flex:1; min-width:0;">
              <div style="font-weight:600; color:var(--text-primary);">${_escapeHtml(_commitmentsEventLabel(e))}</div>
              <div style="font-size:0.75rem; color:var(--text-secondary);">${e.source || ""} · ${_commitmentsKindBadge(e)}</div>
            </div>
            <div style="text-align:end; white-space:nowrap;">
              <div style="font-weight:700; color:${_commitmentsEventColor(e)};">${_commitmentsAmountText(e)}</div>
              <div style="font-size:0.72rem; color:var(--text-secondary);">
                ${e.projected_balance !== undefined ? `<span data-i18n="commitments_projected_balance"></span> ${_money(e.projected_balance)}` : ""}
              </div>
            </div>
          </div>`
        )
        .join("");
      return `<div class="mb-3">
        <div style="font-weight:700; color:var(--text-primary); margin-bottom:4px; font-size:0.95rem;">${label}</div>
        ${rows}
      </div>`;
    })
    .join("");

  return `<div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
    <div class="card-body" style="padding:16px;">${sections}</div>
  </div>`;
}
