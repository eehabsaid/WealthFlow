"""Phase 1 of payload(): allocation, health score, and exposure computation.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
Builds a typed PortfolioContext dataclass carrier consumed by payload.py
(mirrors the BaselineContext/ForecastContext dataclass-carrier pattern used
in scenario_planner_service/ and net_worth_service/).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .shared import _to_float


@dataclass
class PortfolioContext:
    comp: dict
    total_portfolio: float
    allocation_values: Dict[str, float]
    allocation_percentages: Dict[str, float]
    monthly_expenses: float
    emergency_months: float
    health_score: float
    metrics: Dict[str, float]
    allocation_cards: List[dict]
    categories_owned: int
    bank_exposure: List[dict]
    currency_exposure: List[dict]
    top_assets: List[dict]
    largest_balance: dict
    largest_category_key: str
    largest_category_pct: float
    largest_category_label: str
    diversification_rating_key: str
    largest_bank: dict = field(default_factory=dict)
    largest_currency: dict = field(default_factory=dict)
    largest_asset: dict = field(default_factory=dict)
    highest_appreciating_asset: dict = field(default_factory=dict)


class PayloadMetricsMixin:
    def _build_portfolio_context(self) -> PortfolioContext:
        comp = self.net_worth.portfolio_components()
        total_portfolio = _to_float(comp.get("net_worth_egp"))
        allocation_values = self._allocation_values(comp)
        allocation_percentages = self._allocation_percentages(allocation_values, total_portfolio)

        monthly_expenses = self._monthly_expense_average()
        liquid_for_emergency = allocation_values["cash"] + allocation_values["certificates"]
        emergency_months = self._emergency_fund_months(liquid_for_emergency, monthly_expenses)

        liquid_pct = _to_float(allocation_percentages.get("cash"))

        liquidity_metric = self._score_range_metric(liquid_pct, 15.0, 30.0)
        if liquid_pct > 30.0 and emergency_months >= 6.0:
            liquidity_metric = max(liquidity_metric, 88.0 - min((liquid_pct - 30.0) * 0.65, 18.0))
        fixed_metric = self._score_range_metric(
            _to_float(allocation_percentages.get("real_estate"))
            + _to_float(allocation_percentages.get("vehicles"))
            + _to_float(allocation_percentages.get("other_assets")),
            40.0,
            70.0,
        )
        gold_metric = self._score_range_metric(_to_float(allocation_percentages.get("gold")), 10.0, 20.0)
        emergency_metric = self._score_emergency_fund(emergency_months)
        diversification_metric = self._score_diversification(allocation_percentages)

        weighted_score = (
            (liquidity_metric * 0.25)
            + (fixed_metric * 0.20)
            + (gold_metric * 0.15)
            + (emergency_metric * 0.20)
            + (diversification_metric * 0.20)
        )
        monthly_income = self._latest_monthly_income()
        monthly_cash_flow = monthly_income - monthly_expenses
        if monthly_cash_flow > 0:
            weighted_score += min(4.0, (monthly_cash_flow / max(monthly_expenses, 1.0)) * 4.0)
        health_score = round(max(0.0, min(100.0, weighted_score)), 1)

        allocation_cards = self._allocation_cards(allocation_values, allocation_percentages)

        # Asset classes count only fixed-asset classes (Cash/Banks/Certificates are excluded).
        categories_owned = len(
            [
                value
                for value in [
                    _to_float(allocation_values.get("real_estate")),
                    _to_float(allocation_values.get("vehicles")),
                    _to_float(allocation_values.get("gold")),
                    _to_float(allocation_values.get("other_assets")),
                ]
                if value > 0
            ]
        )
        bank_exposure = self._bank_exposure(comp)
        currency_exposure = self._currency_exposure(comp)
        top_assets = self._top_assets(comp, total_portfolio)
        largest_balance = self._largest_balance_entry(comp)

        largest_category_key = (
            max(allocation_percentages, key=lambda key: allocation_percentages.get(key, 0.0))
            if allocation_percentages
            else "cash"
        )
        largest_category_pct = _to_float(allocation_percentages.get(largest_category_key))
        largest_category_label = self.ALLOCATION_LABELS.get(largest_category_key, "portfolio_optimizer_asset_cash")
        diversification_rating_key = self._diversification_rating(
            asset_classes_owned=categories_owned,
            largest_concentration_pct=largest_category_pct,
            liquid_pct=liquid_pct,
            diversification_metric=diversification_metric,
        )

        largest_bank = bank_exposure[0] if bank_exposure else {"bank_name": "-", "value": 0.0}
        largest_currency = currency_exposure[0] if currency_exposure else {"code": "EGP", "value": 0.0}
        largest_asset = top_assets[0] if top_assets else {"asset": "-", "value": 0.0}
        highest_appreciating_asset = self._highest_appreciating_asset(top_assets)

        return PortfolioContext(
            comp=comp,
            total_portfolio=total_portfolio,
            allocation_values=allocation_values,
            allocation_percentages=allocation_percentages,
            monthly_expenses=monthly_expenses,
            emergency_months=emergency_months,
            health_score=health_score,
            metrics={
                "liquidity": round(liquidity_metric, 2),
                "fixed_assets": round(fixed_metric, 2),
                "gold": round(gold_metric, 2),
                "emergency_fund": round(emergency_metric, 2),
                "diversification": round(diversification_metric, 2),
            },
            allocation_cards=allocation_cards,
            categories_owned=categories_owned,
            bank_exposure=bank_exposure,
            currency_exposure=currency_exposure,
            top_assets=top_assets,
            largest_balance=largest_balance,
            largest_category_key=largest_category_key,
            largest_category_pct=largest_category_pct,
            largest_category_label=largest_category_label,
            diversification_rating_key=diversification_rating_key,
            largest_bank=largest_bank,
            largest_currency=largest_currency,
            largest_asset=largest_asset,
            highest_appreciating_asset=highest_appreciating_asset,
        )
