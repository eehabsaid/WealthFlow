"""
NOTE: Part of the cash_flow_forecast_service package split (see helpers.py
docstring for the 200-line-per-file convention this package follows).

RatesMixin: exchange-rate lookup and EGP conversion. Composed onto
CashFlowForecastService in core.py.
"""

from __future__ import annotations

from typing import Dict

from .helpers import to_float


class RatesMixin:
    def _rates(self) -> Dict[str, float]:
        comp = self._net_worth_service.portfolio_components()
        raw_rates = comp.get("rates", {})
        return {str(code or "").upper(): to_float(value) for code, value in raw_rates.items()}

    def _convert_egp(self, amount: float, currency_code: str, rates: Dict[str, float]) -> float:
        code = str(currency_code or "EGP").upper()
        if code in ("", "EGP"):
            return amount
        return amount * to_float(rates.get(code))
