"use strict";
// commitments_calendar/risk_panel.js — Financial Intelligence panel:
// risk reasons, concentration windows, negative-balance months, highlights.
// All computed by the backend (CommitmentsCalendarService); rendered here.

function _commitmentsFillParams(text, params) {
  let out = String(text || "");
  for (const [k, v] of Object.entries(params || {})) {
    out = out.split(`{${k}}`).join(String(v));
  }
  return out;
}

function _renderCommitmentsRiskPanel(analysis) {
  const host = document.getElementById("commitments-risk-panel");
  if (!host) return;
  const reasons = analysis.risk_reasons || [];
  const windows = analysis.concentration_windows || [];
  const highlights = analysis.highlights || [];
  const lang =
    currentLang() === "ar"
      ? "ar"
      : currentLang() === "fr"
        ? "fr"
        : currentLang() === "de"
          ? "de"
          : "en";

  let reasonsHtml = "";
  if (reasons.length) {
    reasonsHtml = reasons
      .map(
        (
          r
        ) => `<div style="display:flex; gap:8px; align-items:flex-start; padding:8px 10px; border-radius:8px; background:var(--bg-primary); border:1px solid var(--border-color); margin-bottom:6px;">
        <i class="bi bi-exclamation-circle mt-1" style="color:var(--warning-color, #f39c12);"></i>
        <span style="color:var(--text-primary); font-size:0.88rem;">${_commitmentsFillParams(t(r.key), r.params)}</span>
      </div>`
      )
      .join("");
  } else {
    reasonsHtml = `<div style="display:flex; gap:8px; align-items:center; padding:8px 10px; border-radius:8px; background:var(--bg-primary); border:1px solid var(--border-color); margin-bottom:6px;">
      <i class="bi bi-check-circle" style="color:var(--success-color, #2ecc71);"></i>
      <span style="color:var(--text-secondary); font-size:0.88rem;" data-i18n="commitments_risk_clear"></span>
    </div>`;
  }

  let windowsHtml = "";
  if (windows.length) {
    windowsHtml = `<div style="margin-top:10px;">
      <div style="font-weight:600; color:var(--text-primary); font-size:0.85rem; margin-bottom:6px;" data-i18n="commitments_concentration_title"></div>
      ${windows
        .map(
          (
            w
          ) => `<div style="font-size:0.82rem; color:var(--text-secondary); padding:4px 10px; background:var(--bg-primary); border:1px solid var(--border-color); border-radius:6px; margin-bottom:4px;">
          ${w.start} · <span data-i18n="commitments_concentration_events"></span> ${w.events} · ${_money(w.outflow)}
        </div>`
        )
        .join("")}
    </div>`;
  }

  let highlightsHtml = "";
  if (highlights.length) {
    highlightsHtml = `<div style="margin-top:10px;">
      <div style="font-weight:600; color:var(--text-primary); font-size:0.85rem; margin-bottom:6px;" data-i18n="commitments_highlights_title"></div>
      ${highlights
        .slice(0, 5)
        .map(
          (
            h
          ) => `<div style="font-size:0.82rem; color:var(--text-secondary); padding:4px 10px; background:var(--bg-primary); border:1px solid var(--border-color); border-radius:6px; margin-bottom:4px;">
          ${_commitmentsDateFromISO(h.date).toLocaleDateString(lang, { day: "numeric", month: "short", year: "numeric" })} · ${t(`commitments_event_${h.event_type === "certificate_maturity" ? "certificate_maturity" : h.event_type}`)} · ${_money(h.amount)}${h.currency_code ? ` ${h.currency_code}` : ""}
        </div>`
        )
        .join("")}
    </div>`;
  }

  host.innerHTML = `<div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
    <div class="card-body" style="padding:16px;">
      <div style="font-weight:700; color:var(--text-primary); margin-bottom:10px; font-size:1rem;">
        <i class="bi bi-graph-up me-2"></i><span data-i18n="commitments_risk_title"></span>
      </div>
      ${reasonsHtml}${windowsHtml}${highlightsHtml}
    </div>
  </div>`;
}
