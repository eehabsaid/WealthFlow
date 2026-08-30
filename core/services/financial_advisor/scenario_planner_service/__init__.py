"""Financial Scenario Planner Service - public entry point.

Calculates multi-event financial scenario projections, N-way side-by-side
comparison, rule-based financial insights, and presentation-only retirement
readiness.

Architectural Constraints:
1. Reuses existing engines:
   - WealthGrowthForecastService.forecast_with_overrides() for net worth projection series.
   - RiskAnalysisService for risk scoring.
   - GoalPlanningService for goal achievement %.
   - PortfolioOptimizerService.RECOMMENDED_BANDS for asset allocation checks.
   - NetWorthService for current portfolio balances & cash flow baselines.
   - AssetMortgage model for real debt baseline.
2. Retirement readiness is computed strictly as a derived presentation metric from projected net worth.
   It NEVER mutates or interferes with GoalPlanningService, WealthGrowthForecastService, or NetWorthService.
3. Centralized threshold configuration: SCENARIO_PLANNER_CONFIG.
4. Single source of truth for event schema: EVENT_SCHEMA.
5. All calculations wrapped defensively in try/except returning valid JSON.

NOTE (200-line file convention): this package replaces the original
monolithic core/services/financial_advisor/scenario_planner_service.py
(716 lines). This file is the umbrella re-export:
`from core.services.financial_advisor.scenario_planner_service import
ScenarioPlannerService, create_scenario_record, EVENT_SCHEMA, ...`
continues to work unchanged. Single-domain package (no domain subfolders
needed), organized by concern:

- config.py: SCENARIO_PLANNER_CONFIG + _to_float shared helper
- event_schema.py: EVENT_SCHEMA / SCENARIO_EVENT_SCHEMA_VERSION (static data)
- record.py: create_scenario_record() - standalone atomic scenario creation
- overrides.py: OverridesMixin._events_to_overrides()
- retirement.py: RetirementMixin._compute_retirement_readiness()
- insights.py: InsightsMixin.generate_insights()
- payload_baseline.py + payload_scenarios.py + payload.py: PayloadMixin.payload()
  call chain, in call order:
    payload_baseline.py   - baseline trajectory computation phase
    payload_scenarios.py  - N-way scenario comparison phase
    payload.py             - thin orchestrator + defensive fallback

ScenarioPlannerService composes the above via mixins (mirrors the
NetWorthService package's mixin composition pattern). __init__ and
_get_current_real_debt stay here since they're small and directly own the
service's engine-instance state.
"""
from __future__ import annotations

from datetime import date

from core.models import AssetMortgage
from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.goal_planning_service import GoalPlanningService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService

from .config import SCENARIO_PLANNER_CONFIG, _to_float
from .event_schema import EVENT_SCHEMA, SCENARIO_EVENT_SCHEMA_VERSION
from .insights import InsightsMixin
from .overrides import OverridesMixin
from .payload import PayloadMixin
from .record import create_scenario_record
from .retirement import RetirementMixin

__all__ = [
    "ScenarioPlannerService",
    "create_scenario_record",
    "EVENT_SCHEMA",
    "SCENARIO_EVENT_SCHEMA_VERSION",
    "SCENARIO_PLANNER_CONFIG",
]


class ScenarioPlannerService(OverridesMixin, RetirementMixin, InsightsMixin, PayloadMixin):
    """Computes projections, comparison, and insights for Scenario Planner."""

    def __init__(self, today: date | None = None, user=None):
        self.today = today or date.today()
        self.user = user
        self.config = dict(SCENARIO_PLANNER_CONFIG)
        self._net_worth_service = NetWorthService()
        self._forecast_service = WealthGrowthForecastService(
            today=self.today,
            net_worth_service=self._net_worth_service,
        )
        self._cash_flow_service = CashFlowForecastService(
            today=self.today,
            net_worth_service=self._net_worth_service,
        )
        self._goal_service = GoalPlanningService(
            today=self.today,
            net_worth_service=self._net_worth_service,
        )

    def _get_current_real_debt(self) -> float:
        """Fetch total real debt from AssetMortgage model."""
        mortgages = AssetMortgage.objects.all()
        rates = self._net_worth_service.portfolio_components().get("rates", {})
        total_debt = 0.0
        for m in mortgages:
            rem = _to_float(m.remaining_balance)
            code = str(m.currency.code if m.currency else "EGP").upper()
            rate = 1.0 if code in ("", "EGP") else _to_float(rates.get(code)) or 1.0
            total_debt += rem * rate
        return total_debt
