"""
NetWorthService - public entry point.

NOTE (200-line file convention): this package replaces the original
monolithic core/services/balance/net_worth_service.py (1162 lines). This
file is the umbrella re-export: `from core.services.balance.net_worth_service
import NetWorthService` continues to work unchanged. Layout, organized by
domain subfolder:

- helpers.py: stateless constants + _to_float/_to_decimal/_normalize_gold_purity
- data_access.py + balance_entries.py: NetWorthDataAccessMixin - cached DB loaders
- portfolio.py: NetWorthPortfolioMixin - portfolio_components, balance_payload,
  fixed_assets_snapshot (cross-domain aggregator, stays at package root)
- assets/fixed_assets_snapshot.py: fixed_assets_snapshot builder (fixed-asset domain)
- gold/certificate_forecast_gold_signal.py: gold trend/signal calc (gold domain),
  called from certificate/certificate_forecast_metrics.py
- certificate/: everything specific to certificate_forecast_payload(), in
  call order:
    certificate_forecast_context.py       - ForecastContext dataclass
    certificate_forecast_metrics.py       - phase 1, pure metric calc
    certificate_forecast_recommendations.py +
    certificate_forecast_recommendations_allocation.py +
    certificate_forecast_recommendation_helpers.py +
    certificate_forecast_recommendation_fallback.py
                                           - phase 2, recommendation building
                                             (order-preserving - see
                                             certificate_forecast_context.py
                                             docstring for why this split is
                                             behavior-safe)
    certificate_forecast_action.py        - phase 3, action plan + final
                                             payload assembly

certificate_forecast_payload() below is a thin orchestrator: build metrics ->
append recommendations -> build action plan -> assemble payload.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, TypeVar, cast

from core.services.balance.net_worth_service.certificate.certificate_forecast_action import assemble_forecast_payload, build_action_plan
from core.services.balance.net_worth_service.certificate.certificate_forecast_metrics import build_forecast_metrics
from core.services.balance.net_worth_service.certificate.certificate_forecast_recommendations import append_forecast_recommendations
from core.services.balance.net_worth_service.data_access import NetWorthDataAccessMixin
from core.services.balance.net_worth_service.portfolio import NetWorthPortfolioMixin

T = TypeVar("T")


class NetWorthService(NetWorthDataAccessMixin, NetWorthPortfolioMixin):
    _shared_cache: Dict[str, Any] = {}
    _shared_cache_time: float = 0.0

    def __init__(self, cache: Dict[str, Any] | None = None):
        self._cache = cache if cache is not None else {}

    def _cached(self, key: str, producer: Callable[[], T]) -> T:
        if key not in self._cache:
            self._cache[key] = producer()
        return cast(T, self._cache[key])

    def certificate_forecast_payload(self, today: date | None = None) -> dict:
        ctx = build_forecast_metrics(self, today)
        append_forecast_recommendations(self, ctx)
        action_plan = build_action_plan(ctx)
        return assemble_forecast_payload(self, ctx, action_plan)
