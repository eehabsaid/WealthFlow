from __future__ import annotations

from core.services.financial_advisor.what_if_simulator_service.context import WhatIfContext
from core.services.financial_advisor.what_if_simulator_service.helpers import _to_float


def build_success_payload(ctx: WhatIfContext) -> dict:
    return {
        "as_of": ctx.service.today.isoformat(),
        "parameters": {
            "salary_change_pct": round(ctx.salary_change_pct, 2),
            "expenses_change_pct": round(ctx.expenses_change_pct, 2),
            "gold_allocation_target_pct": round(ctx.gold_allocation_target_pct, 2),
            "certificate_reinvestment_choice": ctx.certificate_reinvestment_choice,
        },
        "current_values": {
            "monthly_salary": ctx.monthly_salary,
            "monthly_expenses": ctx.avg_monthly_expenses,
            "gold_allocation_pct": ctx.current_gold_pct,
            "gold_band_min": ctx.current["gold_band_min"],
            "gold_band_max": ctx.current["gold_band_max"],
            "gold_allocation_max_slider": ctx.gold_slider_max,
            "reinvestment_options": ctx.current["reinvestment_options"],
        },
        "baseline": {
            "net_worth_12m": round(ctx.baseline_nw_12m, 2),
            "risk_score": round(ctx.baseline_risk_score, 1),
            "cash_coverage_months": ctx.baseline_cash_coverage,
            "series": [
                {"month_end": pt["month_end"], "net_worth": pt["net_worth"]}
                for pt in ctx.baseline_points
            ],
        },
        "adjusted": {
            "net_worth_12m": round(ctx.adjusted_nw_12m, 2),
            "risk_score": round(ctx.adjusted_risk_score, 1),
            "cash_coverage_months": ctx.adjusted_cash_coverage,
            "series": [
                {"month_end": pt["month_end"], "net_worth": pt["net_worth"]}
                for pt in ctx.adjusted_points
            ],
        },
        "delta": {
            "net_worth_12m": ctx.nw_delta,
            "risk_score": ctx.risk_delta,
            "cash_coverage_months": ctx.coverage_delta,
            "net_worth_12m_favorable": ctx.nw_favorable,
            "risk_score_favorable": ctx.risk_favorable,
            "cash_coverage_favorable": ctx.coverage_favorable,
        },
        "month_labels": ctx.month_labels,
    }


def build_error_payload(ctx: WhatIfContext, exc: Exception) -> dict:
    """Defensive: always return valid JSON, never a 500."""
    return {
        "as_of": ctx.service.today.isoformat(),
        "error": str(exc),
        "parameters": {
            "salary_change_pct": round(ctx.salary_change_pct, 2),
            "expenses_change_pct": round(ctx.expenses_change_pct, 2),
            "gold_allocation_target_pct": round(_to_float(ctx.gold_allocation_target_pct), 2),
            "certificate_reinvestment_choice": ctx.certificate_reinvestment_choice,
        },
        "current_values": {
            "monthly_salary": 0.0,
            "monthly_expenses": 0.0,
            "gold_allocation_pct": 0.0,
            "gold_band_min": 10.0,
            "gold_band_max": 20.0,
            "gold_allocation_max_slider": 40.0,
            "reinvestment_options": list(ctx.service.REINVESTMENT_OPTIONS),
        },
        "baseline": {
            "net_worth_12m": 0.0,
            "risk_score": 0.0,
            "cash_coverage_months": None,
            "series": [],
        },
        "adjusted": {
            "net_worth_12m": 0.0,
            "risk_score": 0.0,
            "cash_coverage_months": None,
            "series": [],
        },
        "delta": {
            "net_worth_12m": 0.0,
            "risk_score": 0.0,
            "cash_coverage_months": None,
            "net_worth_12m_favorable": False,
            "risk_score_favorable": False,
            "cash_coverage_favorable": False,
        },
        "month_labels": [],
    }
