"""
Phase 2 of certificate_forecast_payload: recommendation building, part 1
(maturity, liquidity, gold-dynamic). Part 2 (allocation/strengths/pressure
recommendations) lives in certificate_forecast_recommendations_allocation.py.

NOTE (200-line file convention): see certificate_forecast_context.py for the
safety argument behind splitting this from certificate_forecast_metrics.py.
Every recommendation check below only reads ctx fields already finalized by
build_forecast_metrics - none of them mutate a value another check depends
on - so appending them here, after metrics are fully computed, in the same
relative order as the original single method, produces identical output.
"""
from __future__ import annotations

from core.services.balance.net_worth_service.certificate.certificate_forecast_context import ForecastContext
from core.services.balance.net_worth_service.certificate.certificate_forecast_recommendation_helpers import add_financial_recommendation, add_investment_recommendation
from core.services.balance.net_worth_service.certificate.certificate_forecast_recommendations_allocation import append_allocation_recommendations
from core.services.balance.net_worth_service.helpers import _fmt_money, _fmt_pct


def append_forecast_recommendations(service, ctx: ForecastContext) -> None:
    if ctx.nearest_maturity is not None:
        if ctx.nearest_maturity <= 7:
            add_investment_recommendation(
                ctx,
                {"key": "recommend_maturity_very_soon", "days_left": ctx.nearest_maturity},
                "recommend_reason_maturity_window",
                {
                    "days_left": ctx.nearest_maturity,
                    "forecast_30": round(ctx.forecast_30, 2),
                    "forecast_90": round(ctx.forecast_90, 2),
                },
                text=(
                    f"A certificate matures in {ctx.nearest_maturity} days. "
                    f"Expected inflow: {_fmt_money(ctx.forecast_30)} EGP (30d), {_fmt_money(ctx.forecast_90)} EGP (90d)."
                ),
                reason_text=(
                    f"Short maturity window improves near-term liquidity planning with a visible 90-day inflow pipeline "
                    f"of {_fmt_money(ctx.forecast_90)} EGP."
                ),
                priority="high",
            )
        elif ctx.nearest_maturity <= 30:
            add_investment_recommendation(
                ctx,
                {"key": "recommend_maturity_soon", "days_left": ctx.nearest_maturity},
                "recommend_reason_maturity_window",
                {
                    "days_left": ctx.nearest_maturity,
                    "forecast_30": round(ctx.forecast_30, 2),
                    "forecast_90": round(ctx.forecast_90, 2),
                },
                text=(
                    f"A certificate matures in {ctx.nearest_maturity} days. "
                    f"Expected inflow: {_fmt_money(ctx.forecast_30)} EGP (30d), {_fmt_money(ctx.forecast_90)} EGP (90d)."
                ),
                reason_text=(
                    "The maturity profile supports liquidity and optional reinvestment decisions over the next quarter."
                ),
                priority="medium",
            )

    obligations_30 = ctx.avg_monthly_expenses
    if ctx.forecast_90 > (ctx.forecast_30 + max(obligations_30, 1)) * 1.8:
        add_investment_recommendation(
            ctx,
            "recommend_large_maturity_90",
            "recommend_reason_large_maturity",
            {
                "forecast_30": round(ctx.forecast_30, 2),
                "forecast_90": round(ctx.forecast_90, 2),
                "forecast_180": round(ctx.forecast_180, 2),
            },
            text=(
                f"Maturity inflows are front-loaded to the coming quarter: "
                f"30d {_fmt_money(ctx.forecast_30)} EGP, 90d {_fmt_money(ctx.forecast_90)} EGP, 180d {_fmt_money(ctx.forecast_180)} EGP."
            ),
            reason_text=(
                "You can stage renewals and diversification gradually instead of concentrating decisions on a single date."
            ),
            priority="medium",
        )

    if ctx.low_liquidity_flag:
        add_financial_recommendation(
            service,
            ctx,
            "recommend_low_liquidity",
            "recommend_reason_liquidity_pressure",
            {
                "liquid_assets": round(ctx.cash_balance, 2),
                "monthly_expenses": round(ctx.avg_monthly_expenses, 2),
                "cash_coverage": round(ctx.cash_coverage_months or 0, 1),
                "future_cash_30": round(ctx.future_cash_30, 2),
                "future_cash_90": round(ctx.future_cash_90, 2),
            },
            text=(
                f"Liquidity is tight: liquid assets {_fmt_money(ctx.cash_balance)} EGP cover about "
                f"{_fmt_pct(ctx.cash_coverage_months or 0, 1)} months of expenses."
            ),
            reason_text=(
                f"Monthly expenses are {_fmt_money(ctx.avg_monthly_expenses)} EGP, while projected cash is "
                f"{_fmt_money(ctx.future_cash_30)} EGP (30d) and {_fmt_money(ctx.future_cash_90)} EGP (90d)."
            ),
            priority="high",
        )

    if ctx.cash_coverage_months is not None and ctx.cash_coverage_months < 3:
        add_financial_recommendation(
            service,
            ctx,
            "recommend_low_emergency_fund",
            "recommend_reason_cash_coverage",
            {
                "liquid_assets": round(ctx.cash_balance, 2),
                "monthly_expenses": round(ctx.avg_monthly_expenses, 2),
                "cash_coverage": round(ctx.cash_coverage_months, 1),
            },
            text=(
                f"Emergency coverage is below target at {_fmt_pct(ctx.cash_coverage_months, 1)} months."
            ),
            reason_text=(
                "Build a larger reserve before increasing risk exposure in gold or long-dated allocations."
            ),
            priority="high",
        )

    add_investment_recommendation(
        ctx,
        {
            "key": "recommend_gold_dynamic",
            "trend": ctx.gold_trend_state,
        },
        "recommend_reason_gold_signal",
        ctx.gold_reason_params,
        text=ctx.gold_text,
        reason_text=(
            f"Gold signal {_fmt_pct(ctx.gold_signal)} with volatility {_fmt_pct(ctx.gold_volatility)}%; "
            f"current allocation {_fmt_pct(ctx.gold_ratio)}%."
        ),
        priority="medium" if ctx.gold_trend_state in {"Strong Uptrend", "Strong Downtrend", "High Volatility"} else "low",
    )

    append_allocation_recommendations(service, ctx)
