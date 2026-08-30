"""Portfolio Optimizer Service - public entry point.

Computes portfolio health score, asset allocation cards, bank/currency
exposure, top-asset breakdown, rule-based recommendations, and rule-based
opportunities from the current net worth snapshot.

NOTE (200-line file convention): this package replaces the original
monolithic core/services/financial_advisor/portfolio_optimizer_service.py
(659 lines). This file is the umbrella re-export:
`from core.services.financial_advisor.portfolio_optimizer_service import
PortfolioOptimizerService` continues to work unchanged. Single-domain
package (no domain subfolders needed), organized by concern:

- shared.py: _to_float / AllocationBand shared primitives (kept separate
  from this file to avoid circular imports with the mixin modules below)
- calculations.py: pure scoring math, moved verbatim from the former
  standalone core/services/financial_advisor/portfolio_optimizer_calculations.py
- allocation.py: AllocationMixin - allocation values/percentages/status/cards
- exposure.py: ExposureMixin - bank/currency exposure, largest balance entry
- top_assets.py: TopAssetsMixin - top-10 asset breakdown (largest method)
- scoring.py: ScoringMixin - score wrappers, health label/rating/explanation
- expense_income.py: ExpenseIncomeMixin - expense baseline, income, maturity
- recommendations.py: RecommendationsMixin - rule-based recommendations
- opportunities.py: OpportunitiesMixin - rule-based opportunities
- payload_metrics.py + payload.py: PayloadMetricsMixin + PayloadMixin -
  payload() call chain, in call order:
    payload_metrics.py - phase 1: allocation/health/exposure -> PortfolioContext
    payload.py          - phase 2: recommendations/opportunities/chart + assembly

PortfolioOptimizerService composes the above via mixins (mirrors the
ScenarioPlannerService/NetWorthService packages' mixin composition pattern).
__init__ and the class constants stay here since they're small and directly
own the service's state and product-required constant data.
"""
from __future__ import annotations

from datetime import date
from typing import Dict

from core.services.balance.net_worth_service import NetWorthService

from .allocation import AllocationMixin
from .exposure import ExposureMixin
from .expense_income import ExpenseIncomeMixin
from .opportunities import OpportunitiesMixin
from .payload import PayloadMixin
from .payload_metrics import PayloadMetricsMixin
from .recommendations import RecommendationsMixin
from .scoring import ScoringMixin
from .shared import AllocationBand
from .top_assets import TopAssetsMixin

__all__ = [
    "PortfolioOptimizerService",
    "AllocationBand",
]


class PortfolioOptimizerService(
    AllocationMixin,
    ExposureMixin,
    TopAssetsMixin,
    ScoringMixin,
    ExpenseIncomeMixin,
    RecommendationsMixin,
    OpportunitiesMixin,
    PayloadMetricsMixin,
    PayloadMixin,
):
    ALLOCATION_LABELS: Dict[str, str] = {
        "cash": "portfolio_optimizer_asset_cash",
        "certificates": "portfolio_optimizer_asset_certificates",
        "gold": "portfolio_optimizer_asset_gold",
        "real_estate": "portfolio_optimizer_asset_real_estate",
        "vehicles": "portfolio_optimizer_asset_vehicles",
        "other_assets": "portfolio_optimizer_asset_other_assets",
    }

    # Recommended ranges kept as constants by product requirement.
    RECOMMENDED_BANDS: Dict[str, AllocationBand] = {
        "cash": AllocationBand(20.0, 40.0),
        "certificates": AllocationBand(15.0, 35.0),
        "gold": AllocationBand(10.0, 20.0),
        "real_estate": AllocationBand(30.0, 60.0),
        "vehicles": AllocationBand(0.0, 15.0),
        "other_assets": AllocationBand(0.0, 15.0),
    }

    HOLDING_ORDER = [
        "cash",
        "certificates",
        "gold",
        "real_estate",
        "vehicles",
        "other_assets",
    ]

    def __init__(self, *, today: date | None = None, net_worth_service: NetWorthService | None = None, monthly_expenses_override: float | None = None):
        self.today = today or date.today()
        self.net_worth = net_worth_service or NetWorthService()
        self._monthly_expenses_override = monthly_expenses_override
