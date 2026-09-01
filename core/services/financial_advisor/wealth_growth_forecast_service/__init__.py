"""wealth_growth_forecast_service package.

Split from the former single-file ``wealth_growth_forecast_service.py``
(407 lines) into a mixin-composition package. Sibling contents:

- utils.py               -- ``_to_float`` shared numeric coercion helper
- portfolio_data.py       -- ``PortfolioDataMixin`` (current portfolio state)
- gold_growth.py          -- ``GoldGrowthMixin`` (gold growth-rate math)
- series_builder.py       -- ``SeriesBuilderMixin`` (month-by-month series)
- breakdown_summary.py    -- ``BreakdownSummaryMixin`` (component breakdown + narrative summary)
- overrides.py            -- ``OverridesMixin`` (What-If Simulator / Scenario Planner overrides)
- service.py              -- ``WealthGrowthForecastService`` (composes all mixins; public entry point)

Only ``WealthGrowthForecastService`` is re-exported here; it is the sole
name external callers import from this package.
"""

from .service import WealthGrowthForecastService

__all__ = ["WealthGrowthForecastService"]
