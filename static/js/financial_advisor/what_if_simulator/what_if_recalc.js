"use strict";
// What-If Simulator tab — recalculation flow (debounced backend calls,
// comparison/chart refresh, spinner/error banner state). Split out of
// what_if.js (200-line backlog). Bare globals.
// ════════════════════════════════════════════════════════════════════════════

async function _recalculateBackend() {
  const pane = document.getElementById("fa-pane-what-if-simulator");
  if (!pane) return;

  _showRecalculatingState(true);

  const query = new URLSearchParams({
    salary_change_pct: _salaryChangePct,
    expenses_change_pct: _expensesChangePct,
    gold_allocation_target_pct: _goldTargetPct !== null ? _goldTargetPct : "",
    certificate_reinvestment_choice: _reinvestmentChoice,
  });

  try {
    const resp = await fetch(`/api/financial-advisor/what-if-simulator/?${query.toString()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const payload = await resp.json();

    _whatIfData = payload;
    _lastSuccessfulData = payload;
    _hideErrorBanner();
    _updateComparisonAndChart(payload);
  } catch (err) {
    _showErrorBanner();
    if (_lastSuccessfulData) {
      _updateComparisonAndChart(_lastSuccessfulData);
    }
  } finally {
    _showRecalculatingState(false);
  }
}

function _debouncedRecalculate() {
  if (_debounceTimer) clearTimeout(_debounceTimer);
  _debounceTimer = setTimeout(() => {
    _recalculateBackend();
  }, 350);
}

function _updateComparisonAndChart(payload) {
  const compBody = document.getElementById("whatif-comparison-body");
  if (compBody && typeof _buildComparisonRowsHtml === "function") {
    compBody.innerHTML = _buildComparisonRowsHtml(payload);
    if (typeof applyTranslations === "function") applyTranslations();
  }
  if (typeof _renderWhatIfChart === "function") {
    _renderWhatIfChart(payload);
  }
}

function _showRecalculatingState(isCalculating) {
  const spinner = document.getElementById("whatif-spinner");
  if (spinner) {
    if (isCalculating) spinner.classList.remove("d-none");
    else spinner.classList.add("d-none");
  }
}

function _showErrorBanner() {
  const banner = document.getElementById("whatif-error-banner");
  if (banner) banner.classList.remove("d-none");
}

function _hideErrorBanner() {
  const banner = document.getElementById("whatif-error-banner");
  if (banner) banner.classList.add("d-none");
}
