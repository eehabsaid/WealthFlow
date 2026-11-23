"use strict";
// commitments_calendar/risk_panel.js — Financial Intelligence panel:
// risk reasons, concentration windows, highlights. All figures are computed
// by the backend (CommitmentsCalendarService); this file only renders them.

function _commitmentsFillParams(text, params) {
  let out = String(text || "");
  for (const [k, v] of Object.entries(params || {})) {
    out = out.split(`{${k}}`).join(k === "amount" ? _money(v) : String(v));
  }
  return out;
}

const _COMMITMENTS_ROW_STYLE =
  "font-size:0.82rem; color:var(--text-secondary); padding:4px 10px; background:var(--bg-primary); border:1px solid var(--border-color); border-radius:6px; margin-bottom:4px;";

function _commitmentsPanelSection(titleKey, rows) {
  if (!rows.length) return "";
  return `<div style="margin-top:10px;">
    <div style="font-weight:600; color:var(--text-primary); font-size:0.85rem; margin-bottom:6px;">${_escapeHtml(t(titleKey))}</div>
    ${rows.map((row) => `<div style="${_COMMITMENTS_ROW_STYLE}">${row}</div>`).join("")}
  </div>`;
}

function _commitmentsReasonRow(icon, color, text, textColor) {
  return `<div style="display:flex; gap:8px; align-items:center; padding:8px 10px; border-radius:8px; background:var(--bg-primary); border:1px solid var(--border-color); margin-bottom:6px;">
    <i class="bi ${icon}" style="color:${color};"></i>
    <span style="color:${textColor}; font-size:0.88rem;">${_escapeHtml(text)}</span>
  </div>`;
}

function _renderCommitmentsRiskPanel(analysis) {
  const host = document.getElementById("commitments-risk-panel");
  if (!host) return;
  const reasons = analysis.risk_reasons || [];
  const incomplete = Boolean(analysis.concentration_incomplete);
  const incompleteHtml = incomplete
    ? _commitmentsReasonRow(
        "bi-info-circle",
        "var(--info-color, #3498db)",
        _commitmentsFillParams(t("commitments_risk_incomplete"), {
          count: analysis.unconverted_count || 0,
          currencies: (analysis.unconverted_currencies || []).join(", "),
        }),
        "var(--text-primary)"
      )
    : "";
  const reasonsHtml =
    reasons.length || incomplete
      ? reasons
          .map((r) =>
            _commitmentsReasonRow(
              "bi-exclamation-circle",
              "var(--warning-color, #f39c12)",
              _commitmentsFillParams(t(r.key), r.params),
              "var(--text-primary)"
            )
          )
          .join("")
      : _commitmentsReasonRow(
          "bi-check-circle",
          "var(--success-color, #2ecc71)",
          t("commitments_risk_clear"),
          "var(--text-secondary)"
        );

  const windows = (analysis.concentration_windows || []).map(
    (w) =>
      `${_escapeHtml(_commitmentsShowDate(w.start))} · ${_escapeHtml(t("commitments_concentration_events"))} ${w.events} · ${_money(w.outflow)}`
  );
  const highlights = (analysis.highlights || [])
    .slice(0, 5)
    .map(
      (h) =>
        `${_escapeHtml(_commitmentsShowDate(h.date))} · ${_escapeHtml(t(`commitments_event_${h.event_type}`))} · ${_money(h.amount)}${h.currency_code ? ` ${_escapeHtml(h.currency_code)}` : ""}`
    );

  host.innerHTML = `<div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
    <div class="card-body" style="padding:16px;">
      <div style="font-weight:700; color:var(--text-primary); margin-bottom:10px; font-size:1rem;">
        <i class="bi bi-graph-up me-2"></i><span>${_escapeHtml(t("commitments_risk_title"))}</span>
      </div>
      ${reasonsHtml}
      ${incompleteHtml}
      ${_commitmentsPanelSection("commitments_concentration_title", windows)}
      ${_commitmentsPanelSection("commitments_highlights_title", highlights)}
    </div>
  </div>`;
}
