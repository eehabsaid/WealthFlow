from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OverviewContext:
    """Carries state threaded through the OverviewService.payload() phase functions."""

    service: Any  # OverviewService instance (for access to sub-services)

    # Phase 1: gathered sub-service payloads
    portfolio_comp: Dict[str, Any] = field(default_factory=dict)
    cash_flow_payload: Dict[str, Any] = field(default_factory=dict)
    wealth_growth_payload: Dict[str, Any] = field(default_factory=dict)
    portfolio_payload: Dict[str, Any] = field(default_factory=dict)
    goal_payload: Dict[str, Any] = field(default_factory=dict)
    current_nw: float = 0.0

    # Phase 2: Portfolio Optimizer metrics
    portfolio_health: Dict[str, Any] = field(default_factory=dict)
    health_score: float = 0.0
    expense_baseline: Dict[str, Any] = field(default_factory=dict)
    avg_monthly_expenses: float = 0.0
    emergency_months: float = 0.0
    diversification: Dict[str, Any] = field(default_factory=dict)
    diversification_rating: str = ""
    largest_asset_concentration: Dict[str, Any] = field(default_factory=dict)

    # Phase 3: Cash Flow Forecast metrics
    current_cash: float = 0.0
    expected_change_30d: float = 0.0
    largest_event: Dict[str, Any] = field(default_factory=dict)
    nearest_maturity: Dict[str, Any] = field(default_factory=dict)

    # Phase 4: Wealth Growth Projections metrics
    expected_growth_pct: float = 0.0
    expected_net_worth_1y: float = 0.0

    # Phase 5: Goal Planning metrics
    goal_summary: Dict[str, Any] = field(default_factory=dict)
    goals_total: int = 0
    goals_completed: int = 0
    goals_on_track: int = 0
    goals_delayed: int = 0
    goal_progress_pct: float = 0.0

    # Phase 6: Spending trend
    this_month_spending: float = 0.0
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    spending_increase: float = 0.0

    # Phase 7: Alerts
    alerts_sorted: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 8: AI summary
    executive_summary: Dict[str, Any] = field(default_factory=dict)

    # Phase 9: Opportunities
    opportunities: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 10: Sparklines
    cash_sparkline: List[Dict[str, Any]] = field(default_factory=list)
    wealth_sparkline: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 11: Next goal due
    next_goal: Optional[Dict[str, Any]] = None

    # Phase 12: Localized date components
    as_of_dict: Dict[str, Any] = field(default_factory=dict)
