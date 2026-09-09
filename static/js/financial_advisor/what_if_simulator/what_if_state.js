"use strict";
// What-If Simulator tab — shared state, formatters, and data loader.
// Split out of what_if.js (200-line backlog). Bare globals (same pattern
// as balance/utils.js); some names (_money, _fmtDelta) intentionally
// duplicate identical definitions already present in what_if_chart.js and
// utils.js — this mirrors the pre-existing pattern in this codebase where
// multiple files define byte-identical bare-global helpers.
// ════════════════════════════════════════════════════════════════════════════

let _whatIfData = null;
let _lastSuccessfulData = null;
let _debounceTimer = null;
let _themeListenerAttached = false;

// Track user-selected slider/dropdown values
let _salaryChangePct = 0;
let _expensesChangePct = 0;
let _goldTargetPct = null;
let _reinvestmentChoice = "reinvest";

function _money(value) {
  const num = Number(value) || 0;
  if (typeof fmtpresent === "function") {
    return fmtpresent(num);
  }
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function _fmtDelta(val, isPct = false, digits = 1) {
  if (val === null || val === undefined) return "-";
  const num = Number(val) || 0;
  const sign = num > 0 ? "+" : "";
  if (isPct) return `${sign}${num.toFixed(digits)}%`;
  if (typeof fmtpresent === "function") {
    return `${sign}${fmtpresent(num)}`;
  }
  return `${sign}${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function _attachThemeListener() {
  if (_themeListenerAttached) return;
  window.addEventListener("themeChanged", () => {
    if (_whatIfData && typeof _renderWhatIfChart === "function") {
      _renderWhatIfChart(_whatIfData);
    }
  });
  _themeListenerAttached = true;
}

// ── Data Loading & Recalculation ──────────────────────────────────────────

async function loadWhatIfSimulator(forceFetch = false) {
  const pane = document.getElementById("fa-pane-what-if-simulator");
  if (!pane) return;

  if (!forceFetch && _whatIfData) {
    _renderWhatIfView(pane);
    return;
  }

  pane.innerHTML = `
      <div class="d-flex justify-content-center align-items-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden" data-i18n="whatif_loading">Loading...</span>
        </div>
      </div>
    `;
  if (typeof applyTranslations === "function") applyTranslations();

  try {
    const resp = await fetch("/api/financial-advisor/what-if-simulator/");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const payload = await resp.json();

    _whatIfData = payload;
    _lastSuccessfulData = payload;

    // Sync state with real backend baseline defaults
    const params = payload.parameters || {};
    const curr = payload.current_values || {};
    _salaryChangePct = Number(params.salary_change_pct || 0);
    _expensesChangePct = Number(params.expenses_change_pct || 0);
    _goldTargetPct =
      params.gold_allocation_target_pct !== undefined
        ? Number(params.gold_allocation_target_pct)
        : Number(curr.gold_allocation_pct || 0);
    _reinvestmentChoice = params.certificate_reinvestment_choice || "reinvest";

    _renderWhatIfView(pane);
    _attachThemeListener();
  } catch (err) {
    pane.innerHTML = `
        <div class="alert alert-danger my-3" role="alert" data-i18n="whatif_error_recalc">
          Failed to load What-If Simulator. Please try again.
        </div>
      `;
    if (typeof applyTranslations === "function") applyTranslations();
  }
}

window.loadWhatIfSimulator = loadWhatIfSimulator;
