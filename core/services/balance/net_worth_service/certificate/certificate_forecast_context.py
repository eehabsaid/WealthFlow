"""
ForecastContext: typed carrier for certificate_forecast_payload's computed
state, threaded across certificate_forecast_metrics.py ->
certificate_forecast_recommendations.py -> certificate_forecast_action.py.

NOTE (200-line file convention): certificate_forecast_payload was originally
a single 710-line method in net_worth_service.py. It was split into three
sequential phases (metrics -> recommendations -> action plan) that share
this dataclass instead of closures/locals, since the phases run in
different files/functions. This is a safe split because none of the
original recommendation-adding code mutates a value that later metric
calculations depend on - recommendations only *read* already-finalized
metrics - so computing all metrics first, then evaluating every
recommendation condition afterward (in the same original relative order),
produces identical output to the interleaved original.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class ForecastContext:
    today: date
    comp: Dict[str, Any]

    cash_balance: float = 0.0
    certificate_balance: float = 0.0
    forecast_30: float = 0.0
    forecast_90: float = 0.0
    forecast_180: float = 0.0
    maturing_interest_30: float = 0.0
    upcoming: List[dict] = field(default_factory=list)
    nearest_maturity: Optional[int] = None

    cash_ratio: float = 0.0
    foreign_currency_ratio: float = 0.0
    certificate_ratio: float = 0.0
    gold_ratio: float = 0.0
    fixed_assets_ratio: float = 0.0

    avg_monthly_expenses: float = 0.0
    monthly_certificate_income: float = 0.0
    monthly_salary: float = 0.0
    monthly_rental_income: float = 0.0
    total_monthly_income: float = 0.0
    cash_coverage_months: Optional[float] = None
    certificate_income_ratio: float = 0.0

    low_liquidity_flag: bool = False
    future_cash_30: float = 0.0
    future_cash_90: float = 0.0
    future_cash_180: float = 0.0

    gold_trend_pct: float = 0.0
    gold_trend_7: float = 0.0
    gold_trend_30: float = 0.0
    gold_trend_90: float = 0.0
    gold_trend_365: float = 0.0
    gold_ma_short: float = 0.0
    gold_ma_long: float = 0.0
    gold_ma_gap_pct: float = 0.0
    gold_volatility: float = 0.0
    gold_signal: float = 0.0
    neutral_band: float = 0.0
    strong_band: float = 0.0
    gold_trend_state: str = "Sideways"
    gold_text: str = ""
    gold_reason_params: Dict[str, Any] = field(default_factory=dict)

    investment_recommendations: List[Any] = field(default_factory=list)
    financial_recommendations: List[str] = field(default_factory=list)
    investment_recommendation_details: List[dict] = field(default_factory=list)
    financial_recommendation_details: List[dict] = field(default_factory=list)
