"use strict";

// Performance tab — interactive event wiring (timeframe buttons, currency
// selector/tabs) and internal chart-render wrappers. Split out of
// performance.js (200-line backlog).
// NOTE: the wrapper functions are named renderPerfGoldChart/
// renderPerfCurrencyChart (not renderGoldChart/renderCurrencyChart) to avoid
// colliding with the bare-global renderGoldChart/renderCurrencyChart already
// defined in performance_charts.js. The original file avoided this collision
// via an IIFE; since this split uses bare globals, the rename is required.
// ════════════════════════════════════════════════════════════════════════════

function attachPerformanceEventListeners(container) {
  // Gold Timeframe Buttons
  const goldTfGroup = container.querySelector("#fa-gold-tf-group");
  if (goldTfGroup) {
    goldTfGroup.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        _goldTimeframe = e.target.getAttribute("data-tf") || "30D";
        goldTfGroup.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        e.target.classList.add("active");
        if (_performanceData && _performanceData.gold) {
          renderPerfGoldChart(_performanceData.gold);
        }
      });
    });
  }

  // Single Currency Selector Dropdown (Updates same chart and analysis panel)
  const currSelect = container.querySelector("#fa-curr-select");
  if (currSelect) {
    currSelect.addEventListener("change", (e) => {
      _selectedCurrency = e.target.value;
      renderPerformanceView(container);
    });
  }

  // Currency Timeframe Buttons
  const currTfGroup = container.querySelector("#fa-curr-tf-group");
  if (currTfGroup) {
    currTfGroup.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        _currencyTimeframe = e.target.getAttribute("data-tf") || "30D";
        currTfGroup.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        e.target.classList.add("active");
        if (_performanceData && _performanceData.currencies && _performanceData.currencies.data) {
          renderPerfCurrencyChart(_performanceData.currencies.data[_selectedCurrency] || {});
        }
      });
    });
  }

  // Currency Analysis Tabs (Synchronized with dropdown)
  const currAnalysisTabs = container.querySelector("#fa-curr-analysis-tabs");
  if (currAnalysisTabs) {
    currAnalysisTabs.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        _selectedCurrency = e.target.getAttribute("data-curr") || "USD";
        renderPerformanceView(container);
      });
    });
  }
}

function renderPerfGoldChart(goldObj) {
  if (typeof window.renderGoldChart === "function") {
    _goldChartInstance = window.renderGoldChart(goldObj, _goldTimeframe);
  }
}

function renderPerfCurrencyChart(currObj) {
  if (typeof window.renderCurrencyChart === "function") {
    _currencyChartInstance = window.renderCurrencyChart(
      currObj,
      _currencyTimeframe,
      _selectedCurrency
    );
  }
}
