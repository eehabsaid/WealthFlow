from __future__ import annotations

import calendar
from datetime import date
from typing import Dict, List

from core.models import BankCertificate, _is_certificate_active
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.balance.net_worth_service import NetWorthService

def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

class WealthGrowthForecastService:
    MONTHS_AHEAD = 12

    def __init__(self, today: date | None = None):
        self.today = today or date.today()
        self._net_worth_service = NetWorthService()
        self._cash_flow_service = CashFlowForecastService(today=self.today)

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

    def _portfolio(self) -> Dict[str, float]:
        comp = self._net_worth_service.portfolio_components()
        forecast = self._net_worth_service.certificate_forecast_payload(today=self.today)
        cash_payload = self._cash_flow_service.payload()
        return {
            "current_net_worth": _to_float(comp["net_worth_egp"]),
            "current_cash": _to_float(cash_payload["checkpoints"]["current"]),
            "bank_balances": _to_float(comp["banks_total_egp"]),
            "fixed_assets": _to_float(comp["fixed_assets_total_egp"]),
            "gold_value": _to_float(comp["gold_value_egp"]),
            "certificate_value": _to_float(comp["certificate_total_egp"]),
            "certificate_interest_monthly": _to_float(comp["certificate_interest_total_egp"]),
            "cash_checkpoints": cash_payload["checkpoints"],
            "cash_timeline": cash_payload["timeline"],
            "gold_trend_30": _to_float(forecast["gold_trend_30"]),
            "gold_trend_90": _to_float(forecast["gold_trend_90"]),
            "gold_ma_gap_pct": _to_float(forecast["gold_ma_gap_pct"]),
            "gold_signal": _to_float(forecast["gold_signal"]),
            "monthly_rental_income": _to_float(forecast["monthly_rental_income"]),
            "monthly_salary": _to_float(forecast["monthly_salary"]),
            "monthly_certificate_income": _to_float(forecast["monthly_certificate_income"]),
            "total_monthly_income": _to_float(forecast["total_monthly_income"]),
        }

    def _active_certificate_principal_by_month(self, month_end: date) -> float:
        total = 0.0
        certs = BankCertificate.objects.select_related("currency").all()
        for cert in certs:
            if not _is_certificate_active(cert):
                continue
            if not cert.expiry_date:
                continue
            if cert.expiry_date <= month_end:
                continue
            total += _to_float(cert.amount) * self._convert_rate(cert.currency.code if cert.currency else "EGP")
        return total

    def _convert_rate(self, currency_code: str) -> float:
        rates = self._net_worth_service.portfolio_components()["rates"]
        code = str(currency_code or "EGP").upper()
        if code in ("", "EGP"):
            return 1.0
        return _to_float(rates.get(code)) or 0.0

    def _gold_monthly_growth_rate(self, portfolio: Dict[str, float]) -> float:
        trend_30_monthly = (portfolio["gold_trend_30"] / 100.0)
        trend_90_monthly = (portfolio["gold_trend_90"] / 100.0) / 3.0
        ma_bias_monthly = (portfolio["gold_ma_gap_pct"] / 100.0) / 2.0
        base_rate = (trend_30_monthly * 0.55) + (trend_90_monthly * 0.30) + (ma_bias_monthly * 0.15)
        return base_rate

    def _scenario_gold_rate(self, base_rate: float, scenario: str, portfolio: Dict[str, float]) -> float:
        spread = max(abs(base_rate) * 0.35, (abs(portfolio["gold_signal"]) / 100.0) * 0.10)
        if scenario == "conservative":
            return base_rate - spread
        if scenario == "optimistic":
            return base_rate + spread
        return base_rate

    def _project_gold(self, current_value: float, months_ahead: int, monthly_rate: float) -> float:
        if current_value <= 0:
            return 0.0
        return max(0.0, current_value * ((1.0 + monthly_rate) ** months_ahead))

    def _month_end_cash(self, cash_timeline: List[dict], month_index: int) -> float:
        if month_index <= 0:
            return _to_float(cash_timeline[0].get("ending_cash") if cash_timeline else 0)
        if not cash_timeline:
            return 0.0
        index = min(month_index, len(cash_timeline) - 1)
        return _to_float(cash_timeline[index].get("ending_cash"))

    def _component_forecast(self, portfolio: Dict[str, float], month_index: int, scenario: str, gold_rate: float) -> Dict[str, float]:
        month_end_dates = self._month_end_dates()
        month_end = month_end_dates[min(max(month_index - 1, 0), len(month_end_dates) - 1)] if month_index > 0 else self.today
        cash_timeline = portfolio["cash_timeline"]
        cash_value = portfolio["current_cash"] if month_index <= 0 else self._month_end_cash(cash_timeline, month_index)
        liquid_cash = cash_value + portfolio["bank_balances"]
        fixed_assets = portfolio["fixed_assets"]
        gold_value = self._project_gold(portfolio["gold_value"], month_index, gold_rate)
        certificate_value = self._active_certificate_principal_by_month(month_end)
        net_worth = liquid_cash + fixed_assets + gold_value + certificate_value
        return {
            "month_index": month_index,
            "month_end": month_end.isoformat(),
            "liquid_cash": round(liquid_cash, 2),
            "fixed_assets": round(fixed_assets, 2),
            "gold": round(gold_value, 2),
            "certificates": round(certificate_value, 2),
            "net_worth": round(net_worth, 2),
        }

    def _build_series(self, portfolio: Dict[str, float], scenario: str) -> Dict[str, object]:
        gold_base_rate = self._gold_monthly_growth_rate(portfolio)
        gold_rate = self._scenario_gold_rate(gold_base_rate, scenario, portfolio)
        points = [self._component_forecast(portfolio, month_index, scenario, gold_rate) for month_index in range(0, self.MONTHS_AHEAD + 1)]
        return {
            "scenario": scenario,
            "gold_monthly_rate": round(gold_rate * 100.0, 4),
            "points": points,
            "final_net_worth": points[-1]["net_worth"],
            "net_worth_increase": round(points[-1]["net_worth"] - portfolio["current_net_worth"], 2),
        }

    def _breakdown(self, portfolio: Dict[str, float], expected_points: List[Dict[str, float]]) -> Dict[str, dict]:
        final = expected_points[-1]
        current_liquid = portfolio["current_cash"] + portfolio["bank_balances"]
        current_components = {
            "liquid_cash": current_liquid,
            "fixed_assets": portfolio["fixed_assets"],
            "gold": portfolio["gold_value"],
            "certificates": portfolio["certificate_value"],
        }
        forecast_components = {
            "liquid_cash": final["liquid_cash"],
            "fixed_assets": final["fixed_assets"],
            "gold": final["gold"],
            "certificates": final["certificates"],
        }
        breakdown = {}
        for key in current_components:
            current = _to_float(current_components[key])
            forecast = _to_float(forecast_components[key])
            diff = forecast - current
            growth_pct = (diff / current * 100.0) if current > 0 else (100.0 if forecast > 0 else 0.0)
            breakdown[key] = {
                "current": round(current, 2),
                "forecast": round(forecast, 2),
                "difference": round(diff, 2),
                "growth_pct": round(growth_pct, 2),
            }
        return breakdown

    def _summary(self, portfolio: Dict[str, float], breakdown: Dict[str, dict], expected_points: List[Dict[str, float]]) -> Dict[str, object]:
        current = portfolio["current_net_worth"]
        final = expected_points[-1]["net_worth"]
        increase = final - current
        growth_pct = (increase / current * 100.0) if current > 0 else 0.0

        non_cash_breakdown = {
            key: data for key, data in breakdown.items() if key != "liquid_cash"
        }
        positive_components = [
            (key, data["difference"], data["growth_pct"])
            for key, data in non_cash_breakdown.items()
            if _to_float(data["difference"]) > 0
        ]
        largest_appreciating_asset = max(positive_components, key=lambda item: item[1], default=("none", 0.0, 0.0))
        fastest_growing_category = max(positive_components, key=lambda item: item[2], default=("none", 0.0, 0.0))

        cashflow_driver_totals: Dict[str, float] = {}
        for month in portfolio.get("cash_timeline", []):
            for event in month.get("events", []):
                event_type = str(event.get("type") or "")
                amount = _to_float(event.get("amount"))
                if amount <= 0:
                    continue
                cashflow_driver_totals[event_type] = cashflow_driver_totals.get(event_type, 0.0) + amount

        driver_candidates = {
            "salary": cashflow_driver_totals.get("salary", 0.0),
            "certificates": (
                cashflow_driver_totals.get("certificate_interest", 0.0)
                + cashflow_driver_totals.get("certificate_maturity", 0.0)
            ),
            "rental_income": cashflow_driver_totals.get("rental_income", 0.0),
            "asset_sale": cashflow_driver_totals.get("asset_sale", 0.0),
            "gold": max(0.0, _to_float(breakdown.get("gold", {}).get("difference"))),
            "fixed_assets": max(0.0, _to_float(breakdown.get("fixed_assets", {}).get("difference"))),
        }
        largest_driver_key, largest_driver_amount = max(
            driver_candidates.items(),
            key=lambda item: item[1],
            default=("none", 0.0),
        )

        insight_key = "wealth_growth_insight_balanced"
        if increase <= 0 or largest_driver_amount <= 0:
            insight_key = "wealth_growth_insight_flat"
        elif largest_driver_key == "salary":
            insight_key = "wealth_growth_insight_salary"
        elif largest_driver_key == "rental_income":
            insight_key = "wealth_growth_insight_rental_income"
        elif largest_driver_key == "asset_sale":
            insight_key = "wealth_growth_insight_asset_sale"
        elif largest_driver_key == "gold":
            insight_key = "wealth_growth_insight_gold"
        elif largest_driver_key == "certificates":
            insight_key = "wealth_growth_insight_certificates"
        elif largest_driver_key == "fixed_assets":
            insight_key = "wealth_growth_insight_fixed_assets"

        return {
            "expected_net_worth_increase": round(increase, 2),
            "expected_growth_pct": round(growth_pct, 2),
            "largest_appreciating_asset": {
                "key": largest_appreciating_asset[0],
                "difference": round(_to_float(largest_appreciating_asset[1]), 2),
            },
            "fastest_growing_asset_category": {
                "key": fastest_growing_category[0],
                "growth_pct": round(_to_float(fastest_growing_category[2]), 2),
            },
            "largest_growth_driver": {
                "key": largest_driver_key,
                "amount": round(_to_float(largest_driver_amount), 2),
            },
            "estimated_monthly_wealth_increase": round(increase / 12.0 if increase else 0.0, 2),
            "insight_key": insight_key,
        }

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
