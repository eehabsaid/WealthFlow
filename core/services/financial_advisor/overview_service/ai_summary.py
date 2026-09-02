from __future__ import annotations

from core.services.financial_advisor.overview_service.context import OverviewContext


def build_executive_summary(ctx: OverviewContext) -> None:
    """Phase 8: Construct structured AI summary parameters."""
    if ctx.health_score >= 90:
        status_text_key = "overview_legend_excellent"
        status_text_fallback = "Excellent"
    elif ctx.health_score >= 75:
        status_text_key = "overview_legend_good"
        status_text_fallback = "Good"
    elif ctx.health_score >= 60:
        status_text_key = "overview_legend_average"
        status_text_fallback = "Average"
    else:
        status_text_key = "overview_legend_needs_attention"
        status_text_fallback = "Needs Attention"

    if "moderate" in ctx.diversification_rating:
        div_status_key = "overview_diversification_moderate"
        div_status_fallback = "moderately diversified"
    elif "good" in ctx.diversification_rating or "excellent" in ctx.diversification_rating:
        div_status_key = "overview_diversification_well"
        div_status_fallback = "well diversified"
    else:
        div_status_key = "overview_diversification_concentrated"
        div_status_fallback = "highly concentrated"

    # AI Recommendation paragraphs (Concise, strictly actionable advice, limited to 3 items)
    # P1: Action on Liquidity
    if ctx.emergency_months >= 6.0:
        p1_key = "overview_rec_liquidity_good"
        p1_fallback = "Your liquidity levels are healthy. You may explore investing surplus cash into yield-generating assets."
    else:
        p1_key = "overview_rec_liquidity_low"
        p1_fallback = "Your liquidity reserves are below the 6-month threshold. Focus on saving to build up emergency cash."

    # P2: Action on Portfolio Balance
    if "moderate" in ctx.diversification_rating:
        p2_key = "overview_rec_diversification_moderate"
        p2_fallback = "Your diversification is average. Consider adding gold or fixed-income certificates to improve stability."
    elif "good" in ctx.diversification_rating or "excellent" in ctx.diversification_rating:
        p2_key = "overview_rec_diversification_well"
        p2_fallback = "Your portfolio balance is well diversified. Maintain this allocation to shield against market volatility."
    else:
        p2_key = "overview_rec_diversification_concentrated"
        p2_fallback = "High asset concentration detected. Consider rebalancing some funds into alternative holdings."

    # P3: Action on Milestone Saving
    if ctx.goals_total > 0:
        if ctx.goals_on_track == ctx.goals_total:
            p3_key = "overview_rec_goals_all_on_track"
            p3_fallback = "All goals are progressing on track. Keep up your monthly savings rate to hit your milestones."
        else:
            p3_key = "overview_rec_goals_some_track"
            p3_fallback = "Some goals require attention. Consider adjusting target dates or saving amounts for delayed milestones."
    else:
        p3_key = "overview_rec_goals_none"
        p3_fallback = "No active goals created yet. Set up specific savings targets to guide your asset growth."

    rec_paragraphs = [
        {
            "key": p1_key,
            "fallback": p1_fallback,
            "params": {"months": round(ctx.emergency_months, 1)}
        },
        {
            "key": p2_key,
            "fallback": p2_fallback,
            "params": {"asset_class_key": ctx.largest_asset_concentration.get("label_key", "portfolio_optimizer_asset_cash")}
        },
        {
            "key": p3_key,
            "fallback": p3_fallback,
            "params": {"on_track": ctx.goals_on_track + ctx.goals_completed, "total": ctx.goals_total}
        }
    ]

    ctx.executive_summary = {
        "health_score": round(ctx.health_score),
        "health_status_key": status_text_key,
        "health_status_fallback": status_text_fallback,
        "yoy_growth": round(ctx.expected_growth_pct, 1),
        "emergency_months": round(ctx.emergency_months, 1),
        "liquidity_status_key": "overview_liquidity_sufficient" if ctx.emergency_months >= 6.0 else "overview_liquidity_limited",
        "liquidity_status_fallback": "sufficient" if ctx.emergency_months >= 6.0 else "limited",
        "diversification_status_key": div_status_key,
        "diversification_status_fallback": div_status_fallback,
        "goals_total": ctx.goals_total,
        "goals_on_track": ctx.goals_on_track + ctx.goals_completed,
        "spending_increase_pct": round(ctx.spending_increase, 1),
        "recommendation_paragraphs": rec_paragraphs
    }
