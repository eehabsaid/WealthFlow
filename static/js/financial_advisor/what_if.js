"use strict";
// What-If Simulator tab logic
// This file is part of the financial_advisor module. Do not edit directly.

(function () {
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

  // ── Floating Live Slider Thumb Tooltip ─────────────────────────────────────
  // (Defined in what_if_chart.js and available on window)

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
      console.error("Failed to load What-If Simulator data:", err);
      pane.innerHTML = `
        <div class="alert alert-danger my-3" role="alert" data-i18n="whatif_error_recalc">
          Failed to load What-If Simulator. Please try again.
        </div>
      `;
      if (typeof applyTranslations === "function") applyTranslations();
    }
  }

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
      console.error("Recalculation error:", err);
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

  // ── Render Views ──────────────────────────────────────────────────────────

  function _renderWhatIfView(pane) {
    if (!_whatIfData) return;

    const curr = _whatIfData.current_values || {};

    const salaryValStr = (curr.monthly_salary || 0).toLocaleString();
    const expValStr = (curr.monthly_expenses || 0).toLocaleString();
    const goldPctStr = Number(curr.gold_allocation_pct || 0).toFixed(1);
    const goldMaxSlider = Number(curr.gold_allocation_max_slider || 40);

    const salaryPctFormatted =
      _salaryChangePct >= 0 ? `+${_salaryChangePct}%` : `${_salaryChangePct}%`;
    const expPctFormatted =
      _expensesChangePct >= 0 ? `+${_expensesChangePct}%` : `${_expensesChangePct}%`;

    pane.innerHTML = `
      <style>
        .whatif-tooltip {
          position: absolute;
          z-index: 2050;
          pointer-events: none;
          transform: translate(-50%, -100%);
          padding: 4px 10px;
          font-size: 12px;
          font-weight: 600;
          border-radius: 6px;
          background: var(--bg-tertiary, #1e293b);
          color: var(--text-primary, #f8fafc);
          border: 1px solid var(--border-color, rgba(255, 255, 255, 0.15));
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
          white-space: nowrap;
        }
        .whatif-tooltip::after {
          content: "";
          position: absolute;
          top: 100%;
          left: 50%;
          transform: translateX(-50%);
          border-width: 5px;
          border-style: solid;
          border-color: var(--border-color, rgba(255, 255, 255, 0.15)) transparent transparent transparent;
        }
      </style>
      <div class="container-fluid p-0">
        <!-- Error Banner (Hidden by default) -->
        <div id="whatif-error-banner" class="alert alert-warning py-2 mb-3 d-none" style="background:rgba(245,158,11,0.15); border:1px solid rgba(245,158,11,0.3); color:var(--text-primary);">
          <i class="bi bi-exclamation-triangle-fill me-2 text-warning"></i>
          <span data-i18n="whatif_error_recalc">Recalculation failed. Displaying previous valid results.</span>
        </div>

        <!-- 2-Column Responsive Layout -->
        <div class="row g-4">
          <!-- Left Column: Controls -->
          <div class="col-12 col-lg-5">
            <div class="card border-0 p-4 h-100" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <div class="d-flex align-items-center justify-content-between mb-4">
                <h5 class="m-0 fw-bold" style="color:var(--text-primary);" data-i18n="whatif_controls_title">Adjust Your Plan</h5>
                <div id="whatif-spinner" class="spinner-border spinner-border-sm text-primary d-none" role="status">
                  <span class="visually-hidden">Calculating...</span>
                </div>
              </div>

              <!-- Salary Change Slider -->
              <div class="mb-4 position-relative">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small fw-semibold m-0" style="color:var(--text-primary);" data-i18n="whatif_salary_label">Salary Change</label>
                  <span id="whatif-salary-val-badge" class="badge bg-primary px-2 py-1">${salaryPctFormatted}</span>
                </div>
                <input type="range" class="form-range" id="whatif-salary-slider" min="-100" max="100" step="5" value="${_salaryChangePct}">
                <div class="d-flex justify-content-between extra-small" style="color:var(--text-muted);">
                  <span>-100% (Resign)</span>
                  <span>Current: ${salaryValStr} EGP/mo</span>
                  <span>+100%</span>
                </div>
              </div>

              <!-- Expenses Change Slider -->
              <div class="mb-4 position-relative">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small fw-semibold m-0" style="color:var(--text-primary);" data-i18n="whatif_expenses_label">Monthly Expenses Change</label>
                  <span id="whatif-expenses-val-badge" class="badge bg-primary px-2 py-1">${expPctFormatted}</span>
                </div>
                <input type="range" class="form-range" id="whatif-expenses-slider" min="-50" max="100" step="5" value="${_expensesChangePct}">
                <div class="d-flex justify-content-between extra-small" style="color:var(--text-muted);">
                  <span>-50%</span>
                  <span>Current: ${expValStr} EGP/mo</span>
                  <span>+100%</span>
                </div>
              </div>

              <!-- Gold Allocation Target Slider -->
              <div class="mb-4 position-relative">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <label class="form-label small fw-semibold m-0" style="color:var(--text-primary);" data-i18n="whatif_gold_label">Gold Allocation Target</label>
                  <span id="whatif-gold-val-badge" class="badge bg-primary px-2 py-1">${Number(_goldTargetPct).toFixed(1)}%</span>
                </div>
                <input type="range" class="form-range" id="whatif-gold-slider" min="0" max="${goldMaxSlider}" step="0.5" value="${_goldTargetPct}">
                <div class="d-flex justify-content-between extra-small" style="color:var(--text-muted);">
                  <span>0%</span>
                  <span>Current: ${goldPctStr}% of net worth</span>
                  <span>${goldMaxSlider}%</span>
                </div>
              </div>

              <!-- Certificate Reinvestment Dropdown -->
              <div class="mb-4">
                <label class="form-label small fw-semibold mb-2" style="color:var(--text-primary);" data-i18n="whatif_reinvest_label">Certificate Reinvestment</label>
                <select class="form-select border-secondary" id="whatif-reinvest-select" style="background:var(--bg-tertiary); color:var(--text-primary);">
                  <option value="reinvest" ${_reinvestmentChoice === "reinvest" ? "selected" : ""} data-i18n="whatif_reinvest_option">Reinvest at maturity</option>
                  <option value="cashout" ${_reinvestmentChoice === "cashout" ? "selected" : ""} data-i18n="whatif_cashout_option">Cash out at maturity</option>
                </select>
              </div>

              <!-- Reset Button -->
              <div class="mt-auto pt-3 border-top border-secondary">
                <button id="whatif-btn-reset" class="btn btn-outline-secondary w-100 py-2 d-flex align-items-center justify-content-center gap-2">
                  <i class="bi bi-arrow-counterclockwise"></i>
                  <span data-i18n="whatif_reset">Reset to Current</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Right Column: Comparison Cards + Chart -->
          <div class="col-12 col-lg-7 d-flex flex-column gap-4">
            <!-- Comparison Card -->
            <div class="card border-0 p-4" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <h5 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="whatif_comparison_title">Baseline vs. Adjusted</h5>
              <div id="whatif-comparison-body">
                ${_buildComparisonRowsHtml(_whatIfData)}
              </div>
            </div>

            <!-- Net Worth Projection Chart Card -->
            <div class="card border-0 p-4 flex-grow-1" style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:12px;">
              <h5 class="fw-bold mb-3" style="color:var(--text-primary);" data-i18n="whatif_chart_title">Net Worth Projection</h5>
              <div style="height:320px; position:relative;">
                <canvas id="whatIfChart"></canvas>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    if (typeof applyTranslations === "function") applyTranslations();
    _attachEventListeners(pane);
    if (typeof _renderWhatIfChart === "function") _renderWhatIfChart(_whatIfData);
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

  function _attachEventListeners(pane) {
    const salarySlider = pane.querySelector("#whatif-salary-slider");
    const expSlider = pane.querySelector("#whatif-expenses-slider");
    const goldSlider = pane.querySelector("#whatif-gold-slider");
    const reinvestSelect = pane.querySelector("#whatif-reinvest-select");
    const btnReset = pane.querySelector("#whatif-btn-reset");

    const perMonthText = typeof t === "function" ? t("whatif_per_month", "/mo") : "/mo";

    function updateSalaryTooltip() {
      const curr = _whatIfData?.current_values || {};
      const baseSalary = Number(curr.monthly_salary || 0);
      const actualSalary = Math.max(0, baseSalary * (1 + _salaryChangePct / 100));
      const pctStr = _salaryChangePct >= 0 ? `+${_salaryChangePct}%` : `${_salaryChangePct}%`;
      const resignNote = _salaryChangePct === -100 ? " (Resigned)" : "";
      const tooltipText =
        baseSalary > 0
          ? `${pctStr}${resignNote} (EGP ${_money(actualSalary)}${perMonthText})`
          : `${pctStr}${resignNote}`;
      _showSliderTooltip(salarySlider, tooltipText);
    }

    function updateExpensesTooltip() {
      const curr = _whatIfData?.current_values || {};
      const baseExpenses = Number(curr.monthly_expenses || 0);
      const actualExpenses = baseExpenses * (1 + _expensesChangePct / 100);
      const pctStr = _expensesChangePct >= 0 ? `+${_expensesChangePct}%` : `${_expensesChangePct}%`;
      const tooltipText =
        baseExpenses > 0 ? `${pctStr} (EGP ${_money(actualExpenses)}${perMonthText})` : `${pctStr}`;
      _showSliderTooltip(expSlider, tooltipText);
    }

    function updateGoldTooltip() {
      const tooltipText = `${Number(_goldTargetPct).toFixed(1)}%`;
      _showSliderTooltip(goldSlider, tooltipText);
    }

    if (salarySlider) {
      salarySlider.addEventListener("input", (e) => {
        _salaryChangePct = Number(e.target.value);
        const badge = pane.querySelector("#whatif-salary-val-badge");
        if (badge)
          badge.textContent =
            _salaryChangePct >= 0 ? `+${_salaryChangePct}%` : `${_salaryChangePct}%`;
        updateSalaryTooltip();
        _debouncedRecalculate();
      });
      salarySlider.addEventListener("pointerdown", updateSalaryTooltip);
      salarySlider.addEventListener("pointerup", _hideSliderTooltip);
      salarySlider.addEventListener("mouseleave", _hideSliderTooltip);
      salarySlider.addEventListener("touchend", _hideSliderTooltip);
      salarySlider.addEventListener("blur", _hideSliderTooltip);
    }

    if (expSlider) {
      expSlider.addEventListener("input", (e) => {
        _expensesChangePct = Number(e.target.value);
        const badge = pane.querySelector("#whatif-expenses-val-badge");
        if (badge)
          badge.textContent =
            _expensesChangePct >= 0 ? `+${_expensesChangePct}%` : `${_expensesChangePct}%`;
        updateExpensesTooltip();
        _debouncedRecalculate();
      });
      expSlider.addEventListener("pointerdown", updateExpensesTooltip);
      expSlider.addEventListener("pointerup", _hideSliderTooltip);
      expSlider.addEventListener("mouseleave", _hideSliderTooltip);
      expSlider.addEventListener("touchend", _hideSliderTooltip);
      expSlider.addEventListener("blur", _hideSliderTooltip);
    }

    if (goldSlider) {
      goldSlider.addEventListener("input", (e) => {
        _goldTargetPct = Number(e.target.value);
        const badge = pane.querySelector("#whatif-gold-val-badge");
        if (badge) badge.textContent = `${_goldTargetPct.toFixed(1)}%`;
        updateGoldTooltip();
        _debouncedRecalculate();
      });
      goldSlider.addEventListener("pointerdown", updateGoldTooltip);
      goldSlider.addEventListener("pointerup", _hideSliderTooltip);
      goldSlider.addEventListener("mouseleave", _hideSliderTooltip);
      goldSlider.addEventListener("touchend", _hideSliderTooltip);
      goldSlider.addEventListener("blur", _hideSliderTooltip);
    }

    if (reinvestSelect) {
      reinvestSelect.addEventListener("change", (e) => {
        _reinvestmentChoice = e.target.value;
        _recalculateBackend();
      });
    }

    if (btnReset) {
      btnReset.addEventListener("click", () => {
        const curr = _whatIfData?.current_values || {};
        _salaryChangePct = 0;
        _expensesChangePct = 0;
        _goldTargetPct = Number(curr.gold_allocation_pct || 0);
        _reinvestmentChoice = "reinvest";

        // Reset UI inputs
        if (salarySlider) salarySlider.value = 0;
        if (expSlider) expSlider.value = 0;
        if (goldSlider) goldSlider.value = _goldTargetPct;
        if (reinvestSelect) reinvestSelect.value = "reinvest";

        const salBadge = pane.querySelector("#whatif-salary-val-badge");
        const expBadge = pane.querySelector("#whatif-expenses-val-badge");
        const goldBadge = pane.querySelector("#whatif-gold-val-badge");
        if (salBadge) salBadge.textContent = "+0%";
        if (expBadge) expBadge.textContent = "+0%";
        if (goldBadge) goldBadge.textContent = `${_goldTargetPct.toFixed(1)}%`;

        _hideSliderTooltip();
        _recalculateBackend();
      });
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

  window.loadWhatIfSimulator = loadWhatIfSimulator;
})();
