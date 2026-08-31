"""
Package-folder split of the former flat
core/services/financial_advisor/cash_flow_forecast_service.py (482 lines),
per the project's 200-line-per-file convention. Every file in this
package must stay under 200 lines; promote a sibling to its own subfolder
if it grows past that.

Sibling files:
- helpers.py         shared to_decimal/to_float coercion + ForecastEvent dataclass
- rates_mixin.py      RatesMixin: exchange-rate lookup and EGP conversion
- recurring_mixin.py  RecurringMixin: monthly expense/salary/rental/mortgage figures
- events_mixin.py     EventsMixin: month walking + certificate/asset-sale event generation
- timeline_mixin.py   TimelineMixin: checkpoints, month-grouped timeline, flattened events
- summary_phase.py    standalone phase functions building the summary/warnings blocks
- core.py             CashFlowForecastService: mixin composition + payload() orchestrator

This __init__.py re-exports only what external callers actually import,
so `from core.services.financial_advisor.cash_flow_forecast_service import
CashFlowForecastService` keeps working unchanged. ForecastEvent is not
imported by any external caller and is intentionally not re-exported here.
"""

from .core import CashFlowForecastService

__all__ = [
    "CashFlowForecastService",
]
