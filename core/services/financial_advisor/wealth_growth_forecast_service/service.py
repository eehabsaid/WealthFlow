from __future__ import annotations

import calendar
from datetime import date
from typing import List

from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.balance.net_worth_service import NetWorthService

from .breakdown_summary import BreakdownSummaryMixin
from .gold_growth import GoldGrowthMixin
from .overrides import OverridesMixin
from .portfolio_data import PortfolioDataMixin
from .series_builder import SeriesBuilderMixin


class WealthGrowthForecastService(
    PortfolioDataMixin,
    GoldGrowthMixin,
    SeriesBuilderMixin,
    BreakdownSummaryMixin,
    OverridesMixin,
):
    MONTHS_AHEAD = 12

    def __init__(self, today: date | None = None, net_worth_service: NetWorthService | None = None):
        self.today = today or date.today()
        self._net_worth_service = net_worth_service or NetWorthService()
        self._cash_flow_service = CashFlowForecastService(today=self.today, net_worth_service=self._net_worth_service)

    def _add_months(self, base_date: date, months: int) -> date:
        month_index = base_date.month - 1 + months
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def _month_end_dates(self) -> List[date]:
        current_month_start = date(self.today.year, self.today.month, 1)
        out: List[date] = []
        for offset in range(1, self.MONTHS_AHEAD + 1):
            month_start = self._add_months(current_month_start, offset)
            last_day = calendar.monthrange(month_start.year, month_start.month)[1]
            out.append(date(month_start.year, month_start.month, last_day))
        return out

    def payload(self) -> dict:
        portfolio = self._portfolio()
        current_net_worth = portfolio["current_net_worth"]

        series = {
            scenario: self._build_series(portfolio, scenario)
            for scenario in ("conservative", "expected", "optimistic")
        }

        expected_points = series["expected"]["points"]
        breakdown = self._breakdown(portfolio, expected_points)
        summary = self._summary(portfolio, breakdown, expected_points)

        month_labels = ["Current"] + [point["month_end"] for point in expected_points[1:]]

        return {
            "as_of": self.today.isoformat(),
            "current_net_worth": round(current_net_worth, 2),
            "month_labels": month_labels,
            "series": series,
            "checkpoints": {
                "current": round(current_net_worth, 2),
                "next_month": round(expected_points[1]["net_worth"], 2),
                "month_3": round(expected_points[3]["net_worth"], 2),
                "month_6": round(expected_points[6]["net_worth"], 2),
                "month_12": round(expected_points[12]["net_worth"], 2),
            },
            "breakdown": breakdown,
            "summary": summary,
            "scenario_cards": {
                "conservative": {
                    "current": round(current_net_worth, 2),
                    "forecast": round(series["conservative"]["final_net_worth"], 2),
                    "difference": round(series["conservative"]["net_worth_increase"], 2),
                    "growth_pct": round((series["conservative"]["net_worth_increase"] / current_net_worth * 100.0) if current_net_worth > 0 else 0.0, 2),
                },
                "expected": {
                    "current": round(current_net_worth, 2),
                    "forecast": round(series["expected"]["final_net_worth"], 2),
                    "difference": round(series["expected"]["net_worth_increase"], 2),
                    "growth_pct": round((series["expected"]["net_worth_increase"] / current_net_worth * 100.0) if current_net_worth > 0 else 0.0, 2),
                },
                "optimistic": {
                    "current": round(current_net_worth, 2),
                    "forecast": round(series["optimistic"]["final_net_worth"], 2),
                    "difference": round(series["optimistic"]["net_worth_increase"], 2),
                    "growth_pct": round((series["optimistic"]["net_worth_increase"] / current_net_worth * 100.0) if current_net_worth > 0 else 0.0, 2),
                },
            },
            "scenario_labels": {
                "conservative": "conservative",
                "expected": "expected",
                "optimistic": "optimistic",
            },
        }
