'use strict';

// balance/allocation.js — Allocation & Portfolio tab renderer
// Renders: Asset Allocation bars
// Called by index.js with pre-fetched data. Zero API calls here.
// ════════════════════════════════════════════════════════════════════════════

function renderBalanceAllocation(data) {
    const pane = document.getElementById('bal-pane-allocation');
    if (!pane) return;

    const { netWorth, cashAllocationValue, allocationValues, goldValue } = data;

    pane.innerHTML = `
        <div class="kpi-card mb-4">
            <div class="kpi-label" data-i18n="asset_allocation">Asset Allocation</div>
            ${renderAllocationBar('type_cash',        cashAllocationValue,                          netWorth)}
            ${renderAllocationBar('bank_certificates', allocationValues.bank_certificates || 0,      netWorth)}
            ${renderAllocationBar('type_gold',         allocationValues.type_gold || goldValue,      netWorth)}
            ${renderAllocationBar('type_real_estate',  allocationValues.type_real_estate || 0,       netWorth)}
            ${renderAllocationBar('type_vehicles',     allocationValues.type_vehicles || 0,          netWorth)}
            ${renderAllocationBar('type_other_assets', allocationValues.type_other_assets || 0,      netWorth)}
        </div>
    `;
}
