"use strict";

// balance/index_trend_health.js — Phase 6-7 of renderBalance: gold trend
// inference, financial health status, and suggested allocations.
// Split out of index.js (200-line backlog).
// ════════════════════════════════════════════════════════════════════════════

function deriveBalanceGoldTrend(forecastData) {
  const inferredTrend = (() => {
    const t90 = Number(forecastData.gold_trend_90 || 0);
    const gap = Number(forecastData.gold_ma_gap_pct || 0);
    const v = Math.abs(Number(forecastData.gold_signal || 0));
    if (
      v >= 3 &&
      Number(forecastData.gold_trend_7 || 0) >= 0 &&
      Number(forecastData.gold_trend_30 || 0) >= 0 &&
      t90 >= 0 &&
      gap >= 0
    )
      return v >= 8 ? "Strong Uptrend" : "Moderate Uptrend";
    if (
      v >= 3 &&
      Number(forecastData.gold_trend_7 || 0) <= 0 &&
      Number(forecastData.gold_trend_30 || 0) <= 0 &&
      t90 <= 0 &&
      gap <= 0
    )
      return v >= 8 ? "Strong Downtrend" : "Moderate Downtrend";
    if (v < 3 && Math.abs(Number(forecastData.gold_trend_30 || 0)) < 4 && Math.abs(t90) < 8)
      return "Sideways";
    if (
      Math.abs(Number(forecastData.gold_trend_7 || 0)) > 3 &&
      Math.abs(Number(forecastData.gold_trend_30 || 0)) < 3
    )
      return "High Volatility";
    if (v >= 8 && t90 > 0 && gap > 0) return "Strong Uptrend";
    if (v >= 3 && t90 > 0 && gap >= 0) return "Moderate Uptrend";
    if (v >= 8 && t90 < 0 && gap < 0) return "Strong Downtrend";
    if (v >= 3 && t90 < 0 && gap <= 0) return "Moderate Downtrend";
    return "Sideways";
  })();

  const trendLabelKey = (() => {
    const tr = String(inferredTrend || "").toLowerCase();
    if (tr.includes("strong uptrend")) return "trend_strong_uptrend";
    if (tr.includes("moderate uptrend")) return "trend_moderate_uptrend";
    if (tr.includes("strong downtrend")) return "trend_strong_downtrend";
    if (tr.includes("moderate downtrend")) return "trend_moderate_downtrend";
    if (tr.includes("high volatility")) return "trend_high_volatility";
    return "trend_sideways";
  })();
  const localizedTrendLabel = t(trendLabelKey, inferredTrend || "Sideways");
  const trendMeta = (() => {
    const tr = inferredTrend;
    if (/strong\s*up|moderate\s*up/i.test(tr)) return { icon: "📈", cls: "fi-positive" };
    if (/strong\s*down|moderate\s*down/i.test(tr)) return { icon: "📉", cls: "fi-negative" };
    if (/volatility/i.test(tr)) return { icon: "⚠️", cls: "fi-warning" };
    return { icon: "➖", cls: "fi-neutral" };
  })();

  return { trendMeta, localizedTrendLabel };
}

function deriveBalanceFinancialHealth(forecastData, financialDetails, getRecommendationText) {
  const netMonthlySurplus =
    Number(forecastData.total_monthly_income || 0) - Number(forecastData.avg_monthly_expenses || 0);
  const diversificationLabel = (() => {
    const ratios = [
      forecastData.cash_ratio,
      forecastData.certificate_ratio,
      forecastData.gold_ratio,
      forecastData.fixed_assets_ratio,
    ].map(Number);
    const max = Math.max(...ratios);
    if (max <= 45) return t("diversification_balanced", "Balanced");
    if (max <= 60) return t("diversification_moderate_concentration", "Moderate Concentration");
    return t("diversification_high_concentration", "High Concentration");
  })();
  const priorityRank = { high: 3, medium: 2, low: 1 };
  const worstPriority = (financialDetails || []).reduce(
    (acc, i) => Math.max(acc, priorityRank[String(i.priority || "").toLowerCase()] || 0),
    0
  );
  const hasBalancedKey = (financialDetails || []).some(
    (i) => String(i.key || "") === "recommend_asset_allocation_balanced"
  );
  const financialHealth = (() => {
    if (worstPriority >= 3)
      return { label: t("status_critical", "Critical"), icon: "🔴", cls: "fi-negative" };
    if (worstPriority === 2)
      return { label: t("status_warning", "Warning"), icon: "🟠", cls: "fi-warning" };
    if (hasBalancedKey && (forecastData.cash_coverage_months || 0) >= 6 && netMonthlySurplus >= 0)
      return { label: t("status_excellent", "Excellent"), icon: "🟢", cls: "fi-positive" };
    return { label: t("status_good", "Good"), icon: "🟦", cls: "fi-neutral" };
  })();

  const topFinancialItem =
    [...(financialDetails || [])].sort(
      (a, b) =>
        (priorityRank[String(b.priority || "").toLowerCase()] || 0) -
        (priorityRank[String(a.priority || "").toLowerCase()] || 0)
    )[0] || null;
  const financialParagraph = topFinancialItem ? getRecommendationText(topFinancialItem) : "";

  const suggestedAllocations = [
    {
      icon: "🥇",
      label: t("gold_value", "Gold"),
      value: Number(forecastData.action_plan?.gold_amount || 0),
    },
    {
      icon: "🏦",
      label: t("certificate_investments", "Certificates"),
      value: Number(forecastData.action_plan?.certificate_amount || 0),
    },
    {
      icon: "💰",
      label: t("liquid_cash", "Cash"),
      value: Number(forecastData.action_plan?.cash_amount || 0),
    },
  ].filter((r) => r.value > 0 || forecastData.action_plan?.key === "action_gold_cash");

  return { netMonthlySurplus, diversificationLabel, financialHealth, financialParagraph, suggestedAllocations };
}
