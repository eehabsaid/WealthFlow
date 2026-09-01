'use strict';

// balance/utils.js — Tab configuration and balance-specific state
// ════════════════════════════════════════════════════════════════════════════

// ── Tab definitions ──────────────────────────────────────────────────────────
// All 5 tabs are primary (no overflow "More" menu needed for exactly 5 tabs)
const BALANCE_TABS = [
    { id: 'overview',        key: 'balance_tab_overview' },
    { id: 'accounts',        key: 'balance_tab_accounts' },
    { id: 'transfers',       key: 'balance_tab_transfers' },
    { id: 'currency_exchange', key: 'balance_tab_currency_exchange' },
    { id: 'bank_interest',   key: 'balance_tab_bank_interest' },
    { id: 'credit_card_payment', key: 'balance_tab_credit_card_payment' },
    { id: 'allocation',      key: 'balance_tab_allocation' },
    { id: 'forecasts',       key: 'balance_tab_forecasts' },
    { id: 'recommendations', key: 'balance_tab_recommendations' },
];

const BALANCE_ACTIVE_TAB_KEY = 'wf_balance_active_tab';

// AbortController for tab event listener cleanup on re-render
let _balanceTabEventsAbortController = null;

// ── Balance-specific state ────────────────────────────────────────────────────
// NOTE: _banks and _currencies are global app-level vars declared in app/index.js.
// Do NOT redeclare them here. Balance module reads/writes them directly.
let _balanceEntries = [];
