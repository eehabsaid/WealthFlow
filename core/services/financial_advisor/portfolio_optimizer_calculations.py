# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
from typing import Dict, List

def _to_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def allocation_percentages(values: Dict[str, float], total: float) -> Dict[str, float]:
    if total <= 0:
        return {key: 0.0 for key in values}
    return {key: round((val / total) * 100.0, 2) for key, val in values.items()}

def score_range_metric(value_pct: float, low: float, high: float) -> float:
    if low <= value_pct <= high:
        return 100.0
    spread = max(high - low, 1.0)
    if value_pct < low:
        distance = low - value_pct
    else:
        distance = value_pct - high
    penalty = min(100.0, (distance / spread) * 75.0)
    return max(0.0, 100.0 - penalty)

def emergency_fund_months(liquid_value: float, monthly_expenses: float) -> float:
    if monthly_expenses <= 0:
        return 12.0
    return liquid_value / monthly_expenses

def score_emergency_fund(months: float) -> float:
    if months >= 6.0:
        return 100.0
    return max(0.0, min(100.0, (months / 6.0) * 100.0))

def score_diversification(percentages: Dict[str, float]) -> float:
    keys = [key for key in percentages if percentages[key] > 0]
    if not keys:
        return 0.0
    n = float(len(percentages))
    hhi = 0.0
    for value in percentages.values():
        share = (value / 100.0)
        hhi += share * share
    min_hhi = 1.0 / n
    max_hhi = 1.0
    if max_hhi == min_hhi:
        return 100.0
    normalized = (max_hhi - hhi) / (max_hhi - min_hhi)
    return max(0.0, min(100.0, normalized * 100.0))

def health_label_key(score: float) -> str:
    if score >= 90:
        return "portfolio_optimizer_health_excellent"
    if score >= 75:
        return "portfolio_optimizer_health_good"
    if score >= 60:
        return "portfolio_optimizer_health_average"
    return "portfolio_optimizer_health_attention"

def highest_appreciating_asset(top_assets: List[dict]) -> dict:
    if not top_assets:
        return {"asset": "-", "gain_pct": 0.0, "gain": 0.0}

    best = max(top_assets, key=lambda item: _to_float(item.get("gain_pct")))
    return {
        "asset": best.get("asset") or "-",
        "gain_pct": round(_to_float(best.get("gain_pct")), 2),
        "gain": round(_to_float(best.get("gain")), 2),
    }

def diversification_rating(
    *,
    asset_classes_owned: int,
    largest_concentration_pct: float,
    liquid_pct: float,
    diversification_metric: float,
) -> str:
    score = 0
    if asset_classes_owned >= 4:
        score += 3
    elif asset_classes_owned == 3:
        score += 2
    elif asset_classes_owned == 2:
        score += 1

    if largest_concentration_pct <= 35:
        score += 3
    elif largest_concentration_pct <= 50:
        score += 2
    elif largest_concentration_pct <= 65:
        score += 1

    if 15 <= liquid_pct <= 35:
        score += 2
    elif 10 <= liquid_pct <= 45:
        score += 1

    if diversification_metric >= 75:
        score += 2
    elif diversification_metric >= 55:
        score += 1

    if score >= 8:
        return "portfolio_optimizer_diversification_excellent"
    if score >= 6:
        return "portfolio_optimizer_diversification_good"
    if score >= 4:
        return "portfolio_optimizer_diversification_moderate"
    return "portfolio_optimizer_diversification_weak"

def health_explanation_key(
    *,
    score: float,
    emergency_months: float,
    largest_concentration_pct: float,
    asset_classes_owned: int,
    gold_pct: float,
    recommended_gold_min: float = 10.0,
) -> str:
    if score >= 85 and emergency_months >= 6 and largest_concentration_pct <= 50 and asset_classes_owned >= 2:
        return "portfolio_optimizer_health_explain_strong"
    if emergency_months < 6:
        return "portfolio_optimizer_health_explain_liquidity_gap"
    if gold_pct < recommended_gold_min:
        return "portfolio_optimizer_health_explain_gold_low"
    if largest_concentration_pct > 50:
        return "portfolio_optimizer_health_explain_concentration"
    return "portfolio_optimizer_health_explain_balanced"
