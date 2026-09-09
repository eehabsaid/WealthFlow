"use strict";

// Performance tab — shared state and API data loader. Split out of
// performance.js (200-line backlog). Bare top-level state, shared with the
// other performance_* sibling files loaded alongside it (same pattern as
// balance/utils.js).
// ════════════════════════════════════════════════════════════════════════════

let _performanceData = null;
let _goldTimeframe = "30D";
let _currencyTimeframe = "30D";
let _selectedCurrency = "USD";
let _goldChartInstance = null;
let _currencyChartInstance = null;

async function loadPerformance() {
  const container = document.getElementById("fa-pane-performance");
  if (!container) return;

  container.innerHTML = `
      <div class="d-flex justify-content-center align-items-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    `;

  try {
    const response = await fetch("/api/financial-advisor/performance/");
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    _performanceData = await response.json();
    renderPerformanceView(container);
  } catch (err) {
    container.innerHTML = `
        <div class="alert alert-danger my-3" role="alert">
          Failed to load Performance data. Please try again.
        </div>
      `;
  }
}

window.loadPerformance = loadPerformance;
