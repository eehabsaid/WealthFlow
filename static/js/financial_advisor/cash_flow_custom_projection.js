"use strict";
// Custom Cash Projection card: interactive what-if cash forecast in the
// Cash Flow tab. Pick a target date (preset or custom) and currency scope,
// fetch the FULL list of individual upcoming events (nothing pre-excluded),
// then toggle any specific event on/off — the projected balance recomputes
// live in the browser, no extra network round-trip per toggle. Backed by
// core/services/financial_advisor/cash_flow_forecast_service/
// custom_projection.py — a pure deterministic calculation, no LLM math.
// This file is part of the financial_advisor module. Do not edit directly.

let _customProjectionState = null; // { startingBalance, events: [{date,type,amount,checked}] }

function _renderCashFlowCustomProjectionCard() {
  const container = document.getElementById("cash_flow_custom_projection_container");
  if (!container) return;

  container.innerHTML = `
    <div class="card border-0" style="background:var(--bg-secondary); border:1px solid var(--border-color);">
      <div class="card-body" style="padding:20px;">
        <div style="color:var(--text-primary); font-weight:700; margin-bottom:12px;" data-i18n="cash_flow_custom_title"></div>

        <div class="row g-3 mb-3">
          <div class="col-12 col-md-6">
            <label style="color:var(--text-secondary); font-size:12px; margin-bottom:4px; display:block;" data-i18n="cash_flow_custom_target_label"></label>
            <select id="custom_projection_preset" class="form-select form-select-sm" style="background:var(--bg-primary); color:var(--text-primary); border-color:var(--border-color);">
              <option value="30" data-i18n="cash_flow_custom_preset_30"></option>
              <option value="90" data-i18n="cash_flow_custom_preset_90"></option>
              <option value="180" data-i18n="cash_flow_custom_preset_180"></option>
              <option value="365" data-i18n="cash_flow_custom_preset_365"></option>
              <option value="custom" data-i18n="cash_flow_custom_preset_custom"></option>
            </select>
            <input type="date" id="custom_projection_date" class="form-control form-control-sm mt-2" style="display:none; background:var(--bg-primary); color:var(--text-primary); border-color:var(--border-color);">
            <div id="custom_projection_date_hint" style="display:none; color:var(--text-secondary); font-size:11px; margin-top:4px;" data-i18n="cash_flow_custom_date_hint"></div>
          </div>

          <div class="col-12 col-md-6">
            <label style="color:var(--text-secondary); font-size:12px; margin-bottom:4px; display:block;" data-i18n="cash_flow_custom_currency_label"></label>
            <select id="custom_projection_currency_scope" class="form-select form-select-sm" style="background:var(--bg-primary); color:var(--text-primary); border-color:var(--border-color);">
              <option value="egp_only" data-i18n="cash_flow_custom_currency_egp_only"></option>
              <option value="total_liquid" data-i18n="cash_flow_custom_currency_total_liquid"></option>
            </select>
          </div>
        </div>

        <button type="button" id="custom_projection_load_btn" class="btn btn-primary btn-sm" data-i18n="cash_flow_custom_load_btn"></button>

        <div id="custom_projection_result" class="mt-3"></div>
      </div>
    </div>
  `;

  const presetSelect = document.getElementById("custom_projection_preset");
  const dateInput = document.getElementById("custom_projection_date");
  // The global date-picker system (static/js/datepicker/) auto-upgrades every
  // input[type="date"] on the page: it wraps the native input in a
  // <div class="wf-dp-wrap">, moves any inline style from the native input
  // onto that wrapper, and permanently hides the native input itself via a
  // CSS class. So toggling display on `dateInput` directly is a no-op once
  // upgraded — the wrapper is the element that actually needs to be shown.
  const dateWrapper = () => dateInput.closest(".wf-dp-wrap") || dateInput;

  presetSelect.addEventListener("change", () => {
    const isCustom = presetSelect.value === "custom";
    dateWrapper().style.display = isCustom ? "block" : "none";
    document.getElementById("custom_projection_date_hint").style.display = isCustom ? "block" : "none";
    if (isCustom && !dateInput.value) {
      // Pre-fill with a sensible default (today + 30 days) so the field
      // is never blank/ambiguous — the user can still change it freely.
      const defaultDate = new Date();
      defaultDate.setDate(defaultDate.getDate() + 30);
      const minDate = new Date();
      minDate.setDate(minDate.getDate() + 1);
      dateInput.min = minDate.toISOString().split("T")[0];
      dateInput.value = defaultDate.toISOString().split("T")[0];
    }
  });

  document.getElementById("custom_projection_load_btn").addEventListener("click", _loadCustomProjectionEvents);

  applyTranslations();
}

async function _loadCustomProjectionEvents() {
  const resultEl = document.getElementById("custom_projection_result");
  const preset = document.getElementById("custom_projection_preset").value;
  const customDate = document.getElementById("custom_projection_date").value;
  const currencyScope = document.getElementById("custom_projection_currency_scope").value;

  const params = new URLSearchParams();
  if (preset === "custom") {
    if (!customDate) {
      // Never silently fall back to a default — tell the user exactly
      // what's missing instead of guessing.
      resultEl.innerHTML = `<div class="alert alert-warning" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);" data-i18n="cash_flow_custom_missing_date"></div>`;
      applyTranslations();
      return;
    }
    params.set("target_date", customDate);
  } else {
    params.set("days", preset);
  }
  params.set("currency_scope", currencyScope);
  // Fetch the FULL, unfiltered event list — individual toggling happens
  // client-side from here on, so nothing is excluded server-side.

  resultEl.innerHTML = `<div style="color:var(--text-secondary);" data-i18n="cash_flow_custom_loading"></div>`;
  applyTranslations();

  try {
    const response = await fetch(`/api/financial-advisor/cash-flow-custom-projection/?${params.toString()}`);
    if (!response.ok) throw new Error("request failed");
    const data = await response.json();

    _customProjectionState = {
      startingBalance: data.starting_balance,
      targetDate: data.target_date,
      events: (data.included_events || []).map((e) => ({ ...e, checked: true })),
    };

    _renderCustomProjectionEventsAndResult();
  } catch (error) {
    resultEl.innerHTML = `<div class="alert alert-danger" style="background:var(--bg-secondary); border-color:var(--border-color); color:var(--text-primary);" data-i18n="cash_flow_custom_error"></div>`;
    applyTranslations();
  }
}

function _customProjectionTotal() {
  const state = _customProjectionState;
  if (!state) return 0;
  return state.events.reduce(
    (sum, e) => sum + (e.checked ? Number(e.amount || 0) : 0),
    state.startingBalance
  );
}

function _renderCustomProjectionEventsAndResult() {
  const resultEl = document.getElementById("custom_projection_result");
  const state = _customProjectionState;
  if (!resultEl || !state) return;

  const langCode = currentLang ? currentLang() : document.documentElement.lang || "en";
  const dateFmt = new Intl.DateTimeFormat(langCode, { year: "numeric", month: "long", day: "numeric" });
  const shortDateFmt = new Intl.DateTimeFormat(langCode, { month: "short", day: "numeric" });

  const eventsHtml = state.events.length
    ? state.events
        .map((e, idx) => {
          const isPositive = Number(e.amount || 0) >= 0;
          const sign = isPositive ? "+" : "-";
          const amountText = _money(Math.abs(Number(e.amount || 0)));
          return `
        <label style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px dashed var(--border-color); cursor:pointer;">
          <span style="display:flex; align-items:center; gap:8px;">
            <input type="checkbox" class="custom-projection-event-toggle" data-event-index="${idx}" ${e.checked ? "checked" : ""}>
            <span style="color:var(--text-secondary); font-size:12px; min-width:56px;">${shortDateFmt.format(new Date(e.date))}</span>
            <span style="color:var(--text-primary);" data-i18n="${_eventTranslationKey(e.type)}"></span>
          </span>
          <span style="color:var(--text-secondary); font-weight:600;">${sign}${amountText}</span>
        </label>
      `;
        })
        .join("")
    : `<div style="color:var(--text-secondary);" data-i18n="cash_flow_custom_no_events"></div>`;

  resultEl.innerHTML = `
    <div class="asset-summary-card mb-3" style="background:var(--bg-primary);">
      <div class="asset-summary-label" data-i18n="cash_flow_custom_projected_balance"></div>
      <div class="asset-summary-value" id="custom_projection_total_display">${_money(_customProjectionTotal())}</div>
      <div style="color:var(--text-secondary); font-size:12px; margin-top:4px;">
        ${dateFmt.format(new Date(state.targetDate))}
      </div>
    </div>
    <div style="color:var(--text-secondary); font-size:12px; margin-bottom:6px;" data-i18n="cash_flow_custom_events_label"></div>
    <div>${eventsHtml}</div>
  `;

  resultEl.querySelectorAll(".custom-projection-event-toggle").forEach((checkbox) => {
    checkbox.addEventListener("change", (ev) => {
      const idx = Number(ev.target.getAttribute("data-event-index"));
      _customProjectionState.events[idx].checked = ev.target.checked;
      const totalEl = document.getElementById("custom_projection_total_display");
      if (totalEl) totalEl.textContent = _money(_customProjectionTotal());
    });
  });

  applyTranslations();
}
