from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WhatIfContext:
    """Carries state threaded through WhatIfSimulatorService.payload() phase functions."""

    service: Any  # WhatIfSimulatorService instance
    salary_change_pct: float = 0.0
    expenses_change_pct: float = 0.0
    gold_allocation_target_pct: Optional[float] = None
    certificate_reinvestment_choice: str = "reinvest"

    current: Dict[str, Any] = field(default_factory=dict)
    gold_slider_max: float = 0.0
    monthly_salary: float = 0.0
    avg_monthly_expenses: float = 0.0
    cash_balance: float = 0.0
    total_net_worth: float = 0.0
    current_gold_pct: float = 0.0
    current_gold_value: float = 0.0

    baseline_series: Dict[str, Any] = field(default_factory=dict)
    baseline_points: List[Dict[str, Any]] = field(default_factory=list)
    baseline_nw_12m: float = 0.0
    baseline_risk_score: float = 0.0
    baseline_cash_coverage: Optional[float] = None

    salary_scale: float = 1.0
    expense_scale: float = 1.0
    target_gold_value: Optional[float] = None
    forecast_overrides: Dict[str, Any] = field(default_factory=dict)

    adjusted_series: Dict[str, Any] = field(default_factory=dict)
    adjusted_points: List[Dict[str, Any]] = field(default_factory=list)
    adjusted_nw_12m: float = 0.0
    adjusted_risk_score: float = 0.0
    adjusted_cash_coverage: Optional[float] = None

    nw_delta: float = 0.0
    risk_delta: float = 0.0
    coverage_delta: Optional[float] = None
    nw_favorable: bool = False
    risk_favorable: bool = False
    coverage_favorable: bool = False

    month_labels: List[str] = field(default_factory=list)
