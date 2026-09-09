"use strict";
// What-If Simulator tab — main view renderer (controls + comparison card +
// chart canvas). Split out of what_if.js (200-line backlog). Bare global.
// ════════════════════════════════════════════════════════════════════════════

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
