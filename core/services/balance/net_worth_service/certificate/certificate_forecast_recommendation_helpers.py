"""
Shared append helpers for the recommendation-building phase.

NOTE (200-line file convention): pulled out of the original nested closures
(_add_investment_recommendation / _add_financial_recommendation) so both
certificate_forecast_recommendations.py and
certificate_forecast_recommendations_allocation.py can share them without
duplicating logic.
"""
from __future__ import annotations

from typing import Dict, cast

from core.services.balance.net_worth_service.certificate.certificate_forecast_context import ForecastContext


def add_investment_recommendation(
    ctx: ForecastContext,
    rec: object,
    reason_key: str,
    reason_params: Dict[str, float | int],
    text: str,
    reason_text: str,
    priority: str = "medium",
) -> None:
    ctx.investment_recommendations.append(rec)
    key = rec.get("key") if isinstance(rec, dict) else str(rec)
    params: Dict[str, float | int] = {}
    if isinstance(rec, dict):
        for field in ["days_left"]:
            if field in rec:
                params[field] = cast(float | int, rec[field])
    ctx.investment_recommendation_details.append(
        {
            "key": key,
            "params": params,
            "reason_key": reason_key,
            "reason_params": reason_params,
            "text": text,
            "reason_text": reason_text,
            "priority": priority,
        }
    )


def add_financial_recommendation(
    service,
    ctx: ForecastContext,
    key: str,
    reason_key: str,
    reason_params: Dict[str, float | int],
    text: str,
    reason_text: str,
    priority: str,
) -> None:
    service._append_unique(ctx.financial_recommendations, key)
    ctx.financial_recommendation_details.append(
        {
            "key": key,
            "params": {},
            "reason_key": reason_key,
            "reason_params": reason_params,
            "text": text,
            "reason_text": reason_text,
            "priority": priority,
        }
    )
