"use strict";

// balance/index_fetch.js — Phase 1-2 of renderBalance: fetch all APIs once,
// store module-level state. Split out of index.js (200-line backlog).
// ════════════════════════════════════════════════════════════════════════════

async function fetchBalancePageData() {
  const [
    bRes,
    bankRes,
    currRes,
    forecastRes,
    transfersRes,
    exchangesRes,
    bankInterestsRes,
    creditCardPaymentsRes,
    cardRenewalFeesRes,
  ] = await Promise.all([
    fetch("/api/balance/"),
    fetch("/api/banks/"),
    fetch("/api/currencies/"),
    fetch("/api/certificate-forecast/"),
    fetch("/api/balance-transfers/"),
    fetch("/api/currency-exchanges/"),
    fetch("/api/bank-interests/"),
    fetch("/api/credit-card-payments/"),
    fetch("/api/card-renewal-fees/"),
  ]);
  const bData = await bRes.json();
  const bankData = await bankRes.json();
  const currData = await currRes.json();
  const forecastData = await forecastRes.json();
  const transfersData = await transfersRes.json();
  const exchangesData = await exchangesRes.json();
  const bankInterestsData = await bankInterestsRes.json();
  const creditCardPaymentsData = await creditCardPaymentsRes.json();
  const cardRenewalFeesData = await cardRenewalFeesRes.json();

  // ── Store module-level state ─────────────────────────────────────────────
  _balanceEntries = bData.entries;
  window.entries = _balanceEntries; // backward-compat
  _banks = bankData.banks; // global app var
  _currencies = currData.currencies || []; // global app var

  return {
    bData,
    bankData,
    currData,
    forecastData,
    transfersData,
    exchangesData,
    bankInterestsData,
    creditCardPaymentsData,
    cardRenewalFeesData,
  };
}
