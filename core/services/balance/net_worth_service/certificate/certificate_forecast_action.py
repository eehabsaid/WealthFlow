"""
Phase 3 of certificate_forecast_payload: action plan + final payload
assembly.

NOTE (200-line file convention): see certificate_forecast_context.py for the
overall phase-split rationale. This runs after certificate_forecast_metrics.py
and certificate_forecast_recommendations.py have fully populated the
ForecastContext.
"""
from __future__ import annotations

from core.models import AppSettings

from .certificate_forecast_context import ForecastContext
from ..helpers import _fmt_money, _fmt_pct


def build_action_plan(ctx: ForecastContext) -> dict:
    action_plan: dict = {}
    available_capital = max(ctx.cash_balance + ctx.forecast_30, 0.0)
    if available_capital <= 0:
        available_capital = max(ctx.total_monthly_income, 0.0)

    income_loss_ratio = (
        (ctx.maturing_interest_30 / ctx.total_monthly_income) * 100 if ctx.total_monthly_income > 0 else 0
    )
    if income_loss_ratio > 20 and ctx.certificate_balance > 0:
        action_plan = {"key": "action_renew_certificate"}
    elif ctx.low_liquidity_flag:
        action_plan = {
            "key": "action_gold_cash",
            "gold_amount": round(available_capital * 0.20, 0),
            "cash_amount": round(available_capital * 0.80, 0),
        }
    elif ctx.certificate_ratio > 40 or ctx.certificate_income_ratio > 30:
        action_plan = {
            "key": "action_gold_certificate_cash",
            "gold_amount": round(available_capital * 0.30, 0),
            "certificate_amount": round(available_capital * 0.35, 0),
            "cash_amount": round(available_capital * 0.35, 0),
        }
    elif ctx.gold_signal >= 6:
        action_plan = {
            "key": "action_gold_certificate",
            "gold_amount": round(available_capital * 0.60, 0),
            "certificate_amount": round(available_capital * 0.40, 0),
        }
    elif ctx.gold_signal <= -6:
        action_plan = {
            "key": "action_gold_certificate_cash",
            "gold_amount": round(available_capital * 0.20, 0),
            "certificate_amount": round(available_capital * 0.45, 0),
            "cash_amount": round(available_capital * 0.35, 0),
        }
    elif available_capital > 0:
        action_plan = {
            "key": "action_gold_cash",
            "gold_amount": round(available_capital * 0.50, 0),
            "cash_amount": round(available_capital * 0.50, 0),
        }

    # Recommended action must never be empty.
    if not action_plan:
        if ctx.certificate_balance > 0:
            action_plan = {"key": "action_renew_certificate"}
        else:
            action_plan = {
                "key": "action_gold_cash",
                "gold_amount": 0,
                "cash_amount": 0,
            }

    action_reason_key = "action_reason_rebalance_mix"
    if action_plan.get("key") == "action_renew_certificate":
        action_reason_key = "action_reason_renew_certificate"
    elif ctx.low_liquidity_flag:
        action_reason_key = "action_reason_liquidity_protection"
    elif ctx.gold_signal >= ctx.neutral_band or ctx.gold_signal <= -ctx.neutral_band:
        action_reason_key = "action_reason_gold_tilt"

    action_reason_text = (
        f"Allocation context: cash {_fmt_pct(ctx.cash_ratio, 1)}%, gold {_fmt_pct(ctx.gold_ratio, 1)}%, "
        f"certificates {_fmt_pct(ctx.certificate_ratio, 1)}%. "
    )
    if action_plan.get("key") == "action_renew_certificate":
        action_reason_text += (
            f"Certificate maturity impact on income is material ({_fmt_pct(income_loss_ratio, 1)}% of monthly income), "
            "so preserving income continuity is prioritized."
        )
    elif ctx.low_liquidity_flag:
        action_reason_text += (
            f"Liquidity protection takes priority because cash coverage is {_fmt_pct(ctx.cash_coverage_months or 0, 1)} months "
            f"with near-term projected cash {_fmt_money(ctx.future_cash_30)} EGP (30d)."
        )
    elif ctx.gold_trend_state in {"Strong Uptrend", "Moderate Uptrend", "Strong Downtrend", "Moderate Downtrend", "High Volatility"}:
        action_reason_text += (
            f"Gold signal is {_fmt_pct(ctx.gold_signal)} ({ctx.gold_trend_state}), so the split is aimed at balancing trend opportunity "
            "with concentration and liquidity risk."
        )
    else:
        action_reason_text += "Portfolio is broadly balanced, so this action keeps diversification while preserving flexibility."

    action_plan["reason_key"] = action_reason_key
    action_plan["reason_params"] = {
        "cash_ratio": round(ctx.cash_ratio, 1),
        "gold_ratio": round(ctx.gold_ratio, 1),
        "certificate_ratio": round(ctx.certificate_ratio, 1),
        "cash_coverage": round(ctx.cash_coverage_months or 0, 1),
        "gold_signal": round(ctx.gold_signal, 2),
    }
    action_plan["reason_text"] = action_reason_text

    return action_plan


def assemble_forecast_payload(service, ctx: ForecastContext, action_plan: dict) -> dict:
    snapshot = service.fixed_assets_snapshot()

    return {
        "cash_balance": round(ctx.cash_balance, 2),
        "certificate_balance": round(ctx.certificate_balance, 2),
        "fixed_assets_balance": round(ctx.comp["fixed_assets_total_egp"], 2),
        "net_worth": round(ctx.comp["net_worth_egp"], 2),
        "future_cash_30": round(ctx.future_cash_30, 2),
        "future_cash_90": round(ctx.future_cash_90, 2),
        "future_cash_180": round(ctx.future_cash_180, 2),
        "forecast_30": round(ctx.forecast_30, 2),
        "forecast_90": round(ctx.forecast_90, 2),
        "forecast_180": round(ctx.forecast_180, 2),
        "upcoming": ctx.upcoming[:10],
        "cash_ratio": round(ctx.cash_ratio, 1),
        "foreign_currency_ratio": round(ctx.foreign_currency_ratio, 1),
        "certificate_ratio": round(ctx.certificate_ratio, 1),
        "gold_ratio": round(ctx.gold_ratio, 1),
        "fixed_assets_ratio": round(ctx.fixed_assets_ratio, 1),
        "real_estate_ratio": round(snapshot["fixed_assets_breakdown_pct"]["type_real_estate"], 1),
        "vehicles_ratio": round(snapshot["fixed_assets_breakdown_pct"]["type_vehicles"], 1),
        "other_assets_ratio": round(snapshot["fixed_assets_breakdown_pct"]["type_other_assets"], 1),
        "gold_value": round(ctx.comp["gold_value_egp"], 2),
        "gold_grams": round(ctx.comp["gold_grams"], 3),
        "gold_trend_pct": round(ctx.gold_trend_pct, 2),
        "investment_recommendations": ctx.investment_recommendations,
        "financial_recommendations": ctx.financial_recommendations,
        "action_plan": action_plan,
        "monthly_salary": round(ctx.monthly_salary, 2),
        "monthly_certificate_income": round(ctx.monthly_certificate_income, 2),
        "monthly_rental_income": round(ctx.monthly_rental_income, 2),
        "total_monthly_income": round(ctx.total_monthly_income, 2),
        "certificate_income_ratio": round(ctx.certificate_income_ratio, 1),
        "gold_trend_30": round(ctx.gold_trend_30, 2),
        "gold_trend_90": round(ctx.gold_trend_90, 2),
        "gold_trend_365": round(ctx.gold_trend_365, 2),
        "gold_trend_7": round(ctx.gold_trend_7, 2),
        "gold_ma_short": round(ctx.gold_ma_short, 2),
        "gold_ma_long": round(ctx.gold_ma_long, 2),
        "gold_ma_gap_pct": round(ctx.gold_ma_gap_pct, 2),
        "gold_signal": round(ctx.gold_signal, 2),
        "avg_monthly_expenses": round(ctx.avg_monthly_expenses, 2),
        "cash_coverage_months": round(ctx.cash_coverage_months, 1) if ctx.cash_coverage_months is not None else None,
        "allocation_values": ctx.comp["allocation_values"],
        "allocation_percentages": ctx.comp["allocation_percentages"],
        "investment_recommendation_details": ctx.investment_recommendation_details,
        "financial_recommendation_details": ctx.financial_recommendation_details,
        "fixed_assets_snapshot": snapshot,
        "expiry_warning_days": int(AppSettings.get("cert_expiry_warning_days", "30") or 30),
    }
