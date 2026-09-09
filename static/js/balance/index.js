"use strict";

// balance/index.js — Page coordinator
// Fetches all APIs once on load, builds the tab shell, delegates rendering
// to the individual tab files. Tab switching never re-calls any API.
// Split into phase files (index_fetch, index_derive, index_recommendations,
// index_trend_health, index_labels, index_shell, index_events) as part of
// the 200-line backlog; this file is the orchestrator only.
// ════════════════════════════════════════════════════════════════════════════

async function renderBalance() {
  const mc = document.getElementById("main-content");
  if (!mc) return;
  mc.innerHTML =
    '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>';

  // ── 1-2. Fetch all data once, store module-level state ───────────────────
  const {
    bData,
    forecastData,
    transfersData,
    exchangesData,
    bankInterestsData,
    creditCardPaymentsData,
    cardRenewalFeesData,
  } = await fetchBalancePageData();

  // ── 3-4. Derived summary values + i18n helpers ────────────────────────────
  const summaryValues = deriveBalanceSummary(bData);
  const i18nHelpers = buildBalanceI18nHelpers();
  const { getRecommendationText, getReasonText, encodeI18nParams } = i18nHelpers;

  // ── 5. Recommendation data ─────────────────────────────────────────────────
  const { investmentDetails, financialDetails, actionReasonText, goldRecommendationText } =
    deriveBalanceRecommendations(forecastData, i18nHelpers);

  // ── 6. Gold trend ───────────────────────────────────────────────────────────
  const { trendMeta, localizedTrendLabel } = deriveBalanceGoldTrend(forecastData);

  // ── 7. Financial health ──────────────────────────────────────────────────
  const {
    netMonthlySurplus,
    diversificationLabel,
    financialHealth,
    financialParagraph,
    suggestedAllocations,
  } = deriveBalanceFinancialHealth(forecastData, financialDetails, getRecommendationText);

  // ── 8. Shared labels (passed once, used by tab renderers) ────────────────
  const labels = buildBalanceLabels();

  // ── 9. Single data bundle for all tab renderers ───────────────────────────
  const tabData = {
    // raw API responses
    forecastData,
    entries: _balanceEntries,
    transfers: transfersData.transfers || [],
    exchanges: exchangesData.exchanges || [],
    bank_interests: bankInterestsData.bank_interests || [],
    credit_card_payments: creditCardPaymentsData.credit_card_payments || [],
    card_renewal_fees: cardRenewalFeesData.card_renewal_fees || [],
    // summary values
    ...summaryValues,
    // recommendation data
    investmentDetails,
    financialDetails,
    actionReasonText,
    goldRecommendationText,
    financialParagraph,
    suggestedAllocations,
    // helpers (functions)
    getRecommendationText,
    getReasonText,
    encodeI18nParams,
    // trend
    trendMeta,
    localizedTrendLabel,
    // health
    netMonthlySurplus,
    diversificationLabel,
    financialHealth,
    // spread labels
    ...labels,
  };

  // ── 10-14. Build & inject tab shell, dispatch tab renders ─────────────────
  const activeTabId = renderBalanceShell(mc, tabData);

  // ── 15. Wire tab events — session storage persistence & Add button ───────
  wireBalanceTabEvents(activeTabId);
}

// ════════════════════════════════════════════════════════════════════════════
// GLOBAL EXPORTS
// ════════════════════════════════════════════════════════════════════════════

window.renderBalance = renderBalance;
window.showBalanceModal = showBalanceModal;
window.saveBalanceEntry = saveBalanceEntry;
window.deleteBalanceEntry = deleteBalanceEntry;
