"""
Phase 2 of certificate_forecast_payload, part 2: strengths/pressure points,
allocation-concentration recommendations, and the final "must never be
empty" fallback. Called last from certificate_forecast_recommendations.py -
order matters, especially for the trailing fallback check.
"""
from __future__ import annotations

from typing import List

from core.services.balance.net_worth_service.certificate.certificate_forecast_context import ForecastContext
from core.services.balance.net_worth_service.certificate.certificate_forecast_recommendation_helpers import add_financial_recommendation
from core.services.balance.net_worth_service.certificate.certificate_forecast_recommendation_fallback import append_fallback_recommendation
from core.services.balance.net_worth_service.helpers import _fmt_money, _fmt_pct


def append_allocation_recommendations(service, ctx: ForecastContext) -> None:
    obligations_90 = ctx.avg_monthly_expenses * 3
    net_income_buffer = ctx.total_monthly_income - ctx.avg_monthly_expenses
    projected_obligation_cover_90 = (ctx.future_cash_90 / obligations_90) if obligations_90 > 0 else 999.0
    liquidity_strength = (ctx.cash_coverage_months or 0.0)

    strengths: List[str] = []
    if liquidity_strength >= 6:
        strengths.append(f"liquidity coverage is {_fmt_pct(liquidity_strength, 1)} months")
    if net_income_buffer > 0:
        strengths.append(f"monthly surplus is {_fmt_money(net_income_buffer)} EGP")
    if ctx.comp["net_worth_egp"] > 0 and ctx.fixed_assets_ratio >= 20:
        strengths.append(f"net worth is {_fmt_money(ctx.comp['net_worth_egp'])} EGP with diversified fixed assets")
    if ctx.future_cash_90 >= ctx.cash_balance:
        strengths.append("future cash projection is stable to improving over 90 days")

    pressure_points: List[str] = []
    if ctx.low_liquidity_flag:
        pressure_points.append("near-term liquidity pressure is elevated")
    if net_income_buffer < 0:
        pressure_points.append(f"monthly cash flow is negative by {_fmt_money(abs(net_income_buffer))} EGP")
    if projected_obligation_cover_90 < 1.0:
        pressure_points.append("90-day cash projection does not fully cover expected obligations")
    if ctx.certificate_income_ratio > 45:
        pressure_points.append(
            f"income is concentrated in certificates ({_fmt_pct(ctx.certificate_income_ratio, 1)}% of recurring income)"
        )

    if strengths:
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
            text=(
                "Overall financial health is "
                + ("strong" if len(strengths) >= 3 and not pressure_points else "stable")
                + ": "
                + "; ".join(strengths[:3])
                + "."
            ),
            reason_text=(
                f"Allocation mix: cash {_fmt_pct(ctx.cash_ratio, 1)}%, certificates {_fmt_pct(ctx.certificate_ratio, 1)}%, "
                f"gold {_fmt_pct(ctx.gold_ratio, 1)}%, fixed assets {_fmt_pct(ctx.fixed_assets_ratio, 1)}%."
            ),
            priority="low",
        )

    if pressure_points:
        add_financial_recommendation(
            service,
            ctx,
            "recommend_low_liquidity" if ctx.low_liquidity_flag else "recommend_cashflow_attention",
            "recommend_reason_liquidity_pressure",
            {
                "liquid_assets": round(ctx.cash_balance, 2),
                "monthly_expenses": round(ctx.avg_monthly_expenses, 2),
                "cash_coverage": round(ctx.cash_coverage_months or 0, 1),
                "future_cash_30": round(ctx.future_cash_30, 2),
                "future_cash_90": round(ctx.future_cash_90, 2),
            },
            text=(
                "Financial pressure points need attention: " + "; ".join(pressure_points[:3]) + "."
            ),
            reason_text=(
                "Prioritize short-term resilience before increasing long-term risk allocations."
            ),
            priority="high" if ctx.low_liquidity_flag else "medium",
        )

    dominant_non_cash_ratio = max(ctx.certificate_ratio, ctx.gold_ratio, ctx.fixed_assets_ratio, ctx.foreign_currency_ratio)
    excess_liquidity = (
        not ctx.low_liquidity_flag
        and ctx.cash_coverage_months is not None
        and ctx.cash_coverage_months > 10
        and (ctx.cash_ratio > dominant_non_cash_ratio + 8 or ctx.cash_ratio > 55)
    )
    if excess_liquidity:
        add_financial_recommendation(
            service,
            ctx,
            "recommend_idle_cash",
            "recommend_reason_excess_liquidity",
            {
                "liquid_assets": round(ctx.cash_balance, 2),
                "monthly_expenses": round(ctx.avg_monthly_expenses, 2),
                "cash_coverage": round(ctx.cash_coverage_months or 0, 1),
            },
            text=(
                f"Liquidity is comfortably above requirements ({_fmt_pct(ctx.cash_coverage_months or 0, 1)} months); "
                "consider deploying part of excess cash gradually into diversified return-generating assets."
            ),
            reason_text=(
                f"Cash weight is {_fmt_pct(ctx.cash_ratio, 1)}% versus certificates {_fmt_pct(ctx.certificate_ratio, 1)}% "
                f"and gold {_fmt_pct(ctx.gold_ratio, 1)}%."
            ),
            priority="medium",
        )

    if ctx.foreign_currency_ratio > max(ctx.certificate_ratio, ctx.gold_ratio) + 10 and ctx.foreign_currency_ratio > 30:
        add_financial_recommendation(
            service,
            ctx,
            "recommend_high_foreign_currency_exposure",
            "recommend_reason_foreign_exposure",
            {
                "foreign_ratio": round(ctx.foreign_currency_ratio, 1),
                "gold_ratio": round(ctx.gold_ratio, 1),
                "certificate_ratio": round(ctx.certificate_ratio, 1),
            },
            text=(
                f"Foreign-currency exposure is elevated at {_fmt_pct(ctx.foreign_currency_ratio, 1)}%; "
                "rebalance gradually to reduce concentration risk."
            ),
            reason_text=(
                f"Current mix vs alternatives: gold {_fmt_pct(ctx.gold_ratio, 1)}%, certificates {_fmt_pct(ctx.certificate_ratio, 1)}%."
            ),
            priority="medium",
        )

    dominant_ratio = max(ctx.cash_ratio, ctx.foreign_currency_ratio, ctx.certificate_ratio, ctx.gold_ratio, ctx.fixed_assets_ratio)
    cert_lead = ctx.certificate_ratio - max(ctx.cash_ratio, ctx.gold_ratio, ctx.foreign_currency_ratio)
    if ctx.certificate_ratio == dominant_ratio and ctx.certificate_ratio > 35 and cert_lead > 12:
        add_financial_recommendation(
            service,
            ctx,
            "recommend_certificate_concentration",
            "recommend_reason_certificate_concentration",
            {
                "certificate_ratio": round(ctx.certificate_ratio, 1),
                "cash_ratio": round(ctx.cash_ratio, 1),
                "gold_ratio": round(ctx.gold_ratio, 1),
            },
            text=(
                f"Certificate allocation is concentrated at {_fmt_pct(ctx.certificate_ratio, 1)}%; "
                "reduce single-asset dependence by rebalancing future maturities."
            ),
            reason_text=(
                f"Relative weights are cash {_fmt_pct(ctx.cash_ratio, 1)}% and gold {_fmt_pct(ctx.gold_ratio, 1)}%."
            ),
            priority="medium",
        )

    min_certificate_ratio = max(8.0, min(20.0, (ctx.gold_ratio + ctx.fixed_assets_ratio) * 0.25))
    if ctx.certificate_ratio < min_certificate_ratio:
        add_financial_recommendation(
            service,
            ctx,
            "recommend_low_certificate_allocation",
            "recommend_reason_low_certificate_allocation",
            {
                "certificate_ratio": round(ctx.certificate_ratio, 1),
                "target_ratio": round(min_certificate_ratio, 1),
            },
            text=(
                f"Certificate allocation is {_fmt_pct(ctx.certificate_ratio, 1)}%, below the target band around "
                f"{_fmt_pct(min_certificate_ratio, 1)}%."
            ),
            reason_text=(
                "A moderate increase in certificates can improve income stability and reduce return volatility."
            ),
            priority="medium",
        )

    append_fallback_recommendation(service, ctx)
