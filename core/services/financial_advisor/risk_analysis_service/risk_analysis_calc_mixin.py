"""
NOTE: Part of the risk_analysis_service package (split per the >200-line rule).
RiskCalcMixin holds the six per-category risk score calculators. Each returns
(score, reason_key, reason_params) and is composed into RiskAnalysisService in
risk_analysis_core.py. Constants (thresholds, EMERGENCY_FUND_TARGET_MONTHS) and
collaborator services (_optimizer_service, _goal_service) live on the composed
class and are accessed here via self.

Absorbs the former standalone risk_analysis_calculations.py (income stability
calc), which was folded in here for the same reason the other five calculators
live in this file: they're one cohesive "score a risk category" domain.
"""
from __future__ import annotations

from typing import List, Tuple

from core.services.financial_advisor.risk_analysis_service.metrics import _to_float


class RiskCalcMixin:
    def _calc_liquidity_risk(self, comp: dict) -> Tuple[float, str, dict]:
        if self._monthly_expenses_override is not None:
            monthly_expenses = max(0.0, self._monthly_expenses_override)
        else:
            monthly_expenses = self._optimizer_service._monthly_expense_average()
        cash_val = _to_float(comp.get("allocation_values", {}).get("type_cash"))
        cert_val = _to_float(comp.get("allocation_values", {}).get("bank_certificates"))
        liquid_value = cash_val + cert_val
        months = self._optimizer_service._emergency_fund_months(liquid_value, monthly_expenses)

        if months >= self.EMERGENCY_FUND_TARGET_MONTHS:
            return 5.0, "risk_analysis_reason_liq_good", {"months": str(round(months, 1))}
        if months >= 3.0:
            score = 30.0 + ((self.EMERGENCY_FUND_TARGET_MONTHS - months) / 3.0) * 30.0
            return score, "risk_analysis_reason_liq_mod", {"months": str(round(months, 1))}

        score = 60.0 + ((3.0 - months) / 3.0) * 40.0
        return score, "risk_analysis_reason_liq_high", {"months": str(round(months, 1))}

    def _calc_bank_concentration_risk(self, comp: dict) -> Tuple[float, str, dict]:
        bank_exposure = self._optimizer_service._bank_exposure(comp)
        if not bank_exposure:
            return 5.0, "risk_analysis_reason_bank_none", {}
        total_bank_value = sum(b["value"] for b in bank_exposure)
        if total_bank_value <= 0:
            return 5.0, "risk_analysis_reason_bank_none", {}

        max_bank_value = bank_exposure[0]["value"]
        pct = max_bank_value / total_bank_value

        if pct <= self.BANK_CONCENTRATION_THRESHOLD:
            return 10.0, "risk_analysis_reason_bank_good", {}

        score = 20.0 + ((pct - self.BANK_CONCENTRATION_THRESHOLD) / (1.0 - self.BANK_CONCENTRATION_THRESHOLD)) * 80.0
        reason_key = "risk_analysis_reason_bank_high" if pct > 0.50 else "risk_analysis_reason_bank_mod"
        return min(100.0, score), reason_key, {"pct": str(round(pct * 100))}

    def _calc_fixed_asset_concentration_risk(self, comp: dict) -> Tuple[float, str, dict]:
        alloc_vals = comp.get("allocation_values", {})
        assets = [
            _to_float(alloc_vals.get("type_real_estate")),
            _to_float(alloc_vals.get("type_gold")),
            _to_float(alloc_vals.get("type_vehicles")),
            _to_float(alloc_vals.get("type_other_assets")),
        ]
        total_assets = sum(assets)
        if total_assets <= 0:
            return 5.0, "risk_analysis_reason_asset_none", {}

        max_asset = max(assets)
        pct = max_asset / total_assets

        if pct <= self.ASSET_CONCENTRATION_THRESHOLD:
            return 10.0, "risk_analysis_reason_asset_good", {}

        score = 20.0 + ((pct - self.ASSET_CONCENTRATION_THRESHOLD) / (1.0 - self.ASSET_CONCENTRATION_THRESHOLD)) * 80.0
        reason_key = "risk_analysis_reason_asset_high" if pct > 0.60 else "risk_analysis_reason_asset_mod"
        return min(100.0, score), reason_key, {"pct": str(round(pct * 100))}

    def _calc_currency_exposure_risk(self, comp: dict) -> Tuple[float, str, dict]:
        currency_exposure = self._optimizer_service._currency_exposure(comp)
        if not currency_exposure:
            return 5.0, "risk_analysis_reason_curr_none", {}
        total_currency = sum(c["value"] for c in currency_exposure)
        if total_currency <= 0:
            return 5.0, "risk_analysis_reason_curr_none", {}

        max_curr = currency_exposure[0]["value"]
        pct = max_curr / total_currency

        if pct <= self.CURRENCY_CONCENTRATION_THRESHOLD:
            return 15.0, "risk_analysis_reason_curr_good", {}

        score = 20.0 + ((pct - self.CURRENCY_CONCENTRATION_THRESHOLD) / (1.0 - self.CURRENCY_CONCENTRATION_THRESHOLD)) * 80.0
        reason_key = "risk_analysis_reason_curr_high" if pct > 0.80 else "risk_analysis_reason_curr_mod"
        return min(100.0, score), reason_key, {"pct": str(round(pct * 100))}

    def _calc_income_stability_risk(self, income_sources: List[dict]) -> Tuple[float, str, dict]:
        total_income = sum(s["value"] for s in income_sources)
        if total_income <= 0:
            return 80.0, "risk_analysis_reason_inc_none", {}

        num_sources = len(income_sources)
        salary_source = next((s for s in income_sources if s["id"] == "salary"), None)
        salary_val = salary_source["value"] if salary_source else 0.0
        non_salary_pct = ((total_income - salary_val) / total_income) * 100.0

        if num_sources >= 2 and non_salary_pct > 15.0:
            return 10.0, "risk_analysis_reason_inc_good", {}
        if num_sources >= 2:
            return 30.0, "risk_analysis_reason_inc_mod", {}

        return 60.0, "risk_analysis_reason_inc_high", {}

    def _calc_goal_completion_risk(self) -> Tuple[float, str, dict]:
        goal_payload = self._goal_service.payload()
        summary = goal_payload.get("summary", {})
        total_goals = summary.get("total_goals", 0)
        at_risk_goals = summary.get("at_risk_goals", 0)
        overall_progress = summary.get("overall_progress_pct", 0.0)

        if total_goals == 0:
            return 5.0, "risk_analysis_reason_goal_none", {}

        progress_risk = 100.0 - overall_progress
        at_risk_pct = (at_risk_goals / total_goals) * 100.0

        risk = (progress_risk * 0.4) + (at_risk_pct * 0.6)

        if risk <= 33:
            reason = "risk_analysis_reason_goal_good"
        elif risk <= 66:
            reason = "risk_analysis_reason_goal_mod"
        else:
            reason = "risk_analysis_reason_goal_high"

        return min(100.0, risk), reason, {"pct": str(round(overall_progress))}
