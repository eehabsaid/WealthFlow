"use strict";
// What-If Simulator tab — interactive slider/select event wiring. Split out
// of what_if.js (200-line backlog). Bare global.
// ════════════════════════════════════════════════════════════════════════════

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
