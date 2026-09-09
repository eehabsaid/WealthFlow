"use strict";

// balance/index_recommendations.js — Phase 5 of renderBalance: recommendation
// data (investment/financial details, action reason text, gold detail text).
// Split out of index.js (200-line backlog).
// ════════════════════════════════════════════════════════════════════════════

function deriveBalanceRecommendations(forecastData, i18nHelpers) {
  const { resolveI18nTemplate, getRecommendationText } = i18nHelpers;

  const investmentDetails = (forecastData.investment_recommendation_details || []).length
    ? forecastData.investment_recommendation_details || []
    : (forecastData.investment_recommendations || []).map((r) => {
        const key = typeof r === "object" && r.key ? r.key : r;
        const params =
          typeof r === "object" && r.days_left != null ? { days_left: r.days_left } : {};
        return { key, params, reason_key: "", reason_params: {} };
      });

  const financialDetails = (forecastData.financial_recommendation_details || []).length
    ? forecastData.financial_recommendation_details || []
    : (forecastData.financial_recommendations || []).map((key) => ({
        key,
        params: {},
        reason_key: "",
        reason_params: {},
      }));

  const actionReasonText = forecastData.action_plan?.reason_text
    ? forecastData.action_plan?.reason_key
      ? resolveI18nTemplate(
          forecastData.action_plan.reason_key,
          forecastData.action_plan.reason_text,
          forecastData.action_plan.reason_params || {}
        )
      : forecastData.action_plan.reason_text
    : forecastData.action_plan?.reason_key
      ? resolveI18nTemplate(
          forecastData.action_plan.reason_key,
          forecastData.action_plan.reason_key,
          forecastData.action_plan.reason_params || {}
        )
      : "";

  const goldDetail =
    investmentDetails.find((i) =>
      String(i.key || "")
        .toLowerCase()
        .includes("gold")
    ) || null;
  const goldRecommendationText = goldDetail ? getRecommendationText(goldDetail) : "";

  return { investmentDetails, financialDetails, actionReasonText, goldRecommendationText };
}
