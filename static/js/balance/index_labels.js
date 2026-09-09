"use strict";

// balance/index_labels.js — Phase 8 of renderBalance: shared labels object,
// passed once and used by all tab renderers. Split out of index.js
// (200-line backlog).
// ════════════════════════════════════════════════════════════════════════════

function buildBalanceLabels() {
  return {
    labelGoldMarketAnalysis: t("gold_market_analysis", "Gold Market Analysis"),
    labelTrend: t("trend_label", "Trend"),
    labelSevenDayChange: t("seven_day_change", "7-Day Change"),
    labelThirtyDayChange: t("thirty_day_change", "30-Day Change"),
    labelNinetyDayChange: t("ninety_day_change", "90-Day Change"),
    labelMa7: t("ma_short_label", "MA(7)"),
    labelMa30: t("ma_long_label", "MA(30)"),
    labelMaGap: t("ma_gap_label", "MA Gap"),
    labelCurrentAllocation: t("current_allocation", "Current Allocation"),
    labelRecommendation: t("recommendation_label", "Recommendation"),
    labelSuggestedAllocation: t("suggested_allocation", "Suggested Allocation"),
    labelFinancialHealth: t("financial_health_label", "Financial Health"),
    labelFinancialHealthOverview: t("financial_health_overview", "Financial Health Overview"),
    labelNetWorth: t("net_worth", "Net Worth"),
    labelLiquidityCoverage: t("liquidity_coverage", "Liquidity Coverage"),
    labelMonthlySurplus: t("monthly_surplus", "Monthly Surplus"),
    labelDiversification: t("diversification_label", "Diversification"),
    labelCash: t("label_cash", "Cash"),
    labelCertificates: t("label_certificates", "Certificates"),
    labelGold: t("label_gold", "Gold"),
    labelFixedAssets: t("label_fixed_assets", "Fixed Assets"),
    labelMonths: t("months", "months"),
    labelEgp: t("EGP", "EGP"),
    grandTotalLabel: t("grand_total", "Total All Balances (EGP equiv.)"),
    formulaDesc: t(
      "balance_formula_desc",
      "= EGP + (USD x rate) + (EUR x rate) + (SAR x rate) + Sum(Gold amount x (purity sell price + purity cashback))"
    ),
  };
}
