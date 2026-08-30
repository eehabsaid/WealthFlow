"""
Final fallback: ensures financial_recommendations is never empty.

NOTE (200-line file convention): split out of certificate_forecast_recommendations_allocation.py
purely for line-count headroom. Must run last - called at the end of
append_allocation_recommendations, which itself runs last in the phase-2
sequence (see certificate_forecast_recommendations.py).
"""
from __future__ import annotations

from core.services.balance.net_worth_service.certificate.certificate_forecast_context import ForecastContext
from core.services.balance.net_worth_service.certificate.certificate_forecast_recommendation_helpers import add_financial_recommendation
from core.services.balance.net_worth_service.helpers import _fmt_pct


def append_fallback_recommendation(service, ctx: ForecastContext) -> None:
    if not ctx.financial_recommendations:
        add_financial_recommendation(
            service,
            ctx,
            "recommend_asset_allocation_balanced",
            "recommend_reason_balanced_portfolio",
            {
                "cash_ratio": round(ctx.cash_ratio, 1),
                "certificate_ratio": round(ctx.certificate_ratio, 1),
                "gold_ratio": round(ctx.gold_ratio, 1),
            },
            text="Financial position is balanced with healthy liquidity, income coverage, and diversified assets.",
            reason_text=(
                f"Cash {_fmt_pct(ctx.cash_ratio, 1)}%, certificates {_fmt_pct(ctx.certificate_ratio, 1)}%, gold {_fmt_pct(ctx.gold_ratio, 1)}%, "
                f"fixed assets {_fmt_pct(ctx.fixed_assets_ratio, 1)}%."
            ),
            priority="low",
        )
