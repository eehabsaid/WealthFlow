"""Financial Commitments Calendar service package.

Read-only: derives calendar events from existing financial records and
anchors all liquidity figures to the CashFlowForecastService series.
Nothing is posted and no balances are modified.
"""
from .service import CommitmentsCalendarService, resolve_week_start_day, resolve_window_days

__all__ = ["CommitmentsCalendarService", "resolve_week_start_day", "resolve_window_days"]
