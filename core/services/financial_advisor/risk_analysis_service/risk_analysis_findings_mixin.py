"""
NOTE: Part of the risk_analysis_service package (split per the >200-line rule).
RiskFindingsMixin turns already-scored metrics into human-facing findings, and
runs a fixed set of stress-test scenarios against the current portfolio. Both
read finalized metric values only (metrics-first, recommendations-second) and
never mutate state other mixins depend on.
"""
from __future__ import annotations

from typing import Dict, List

from core.services.financial_advisor.risk_analysis_service.metrics import RiskMetric, _to_float


class RiskFindingsMixin:
    def _generate_findings(self, metrics: Dict[str, RiskMetric], comp: dict, income_sources: List[dict]) -> List[dict]:
        findings = []

        if metrics["bank"].score >= 50:
            bank_exposure = self._optimizer_service._bank_exposure(comp)
            largest_bank = bank_exposure[0]["bank_name"] if bank_exposure else "one bank"
            findings.append({
                "severity": "high",
                "severity_key": "risk_analysis_severity_high",
                "title_key": "risk_analysis_finding_bank_conc_title",
                "title_params": {"bank": largest_bank},
                "desc_key": "risk_analysis_finding_bank_conc_desc"
            })

        monthly_expenses = self._optimizer_service._monthly_expense_average()
        liquid_value = _to_float(comp.get("allocation_values", {}).get("type_cash")) + _to_float(comp.get("allocation_values", {}).get("bank_certificates"))
        months = self._optimizer_service._emergency_fund_months(liquid_value, monthly_expenses)
        if months < self.EMERGENCY_FUND_TARGET_MONTHS:
            findings.append({
                "severity": "medium",
                "severity_key": "risk_analysis_severity_medium",
                "title_key": "risk_analysis_finding_liquidity_title",
                "title_params": {"months": str(round(months, 1))},
                "desc_key": "risk_analysis_finding_liquidity_desc"
            })
        else:
            findings.append({
                "severity": "low",
                "severity_key": "risk_analysis_severity_low",
                "title_key": "risk_analysis_finding_liquidity_good_title",
                "title_params": {"months": str(round(months, 1))},
                "desc_key": "risk_analysis_finding_liquidity_good_desc"
            })

        if metrics["asset"].score >= 50:
            alloc_vals = comp.get("allocation_values", {})
            assets = {
                "Real Estate": _to_float(alloc_vals.get("type_real_estate")),
                "Gold": _to_float(alloc_vals.get("type_gold")),
                "Vehicles": _to_float(alloc_vals.get("type_vehicles")),
            }
            if sum(assets.values()) > 0:
                top_asset_name = max(assets.items(), key=lambda x: x[1])[0]
                pct = round((assets[top_asset_name] / sum(assets.values())) * 100.0)
                findings.append({
                    "severity": "info",
                    "severity_key": "risk_analysis_severity_info",
                    "title_key": "risk_analysis_finding_asset_conc_title",
                    "title_params": {"asset": top_asset_name, "pct": str(pct)},
                    "desc_key": "risk_analysis_finding_asset_conc_desc"
                })

        if metrics["currency"].score <= 40:
            findings.append({
                "severity": "low",
                "severity_key": "risk_analysis_severity_low",
                "title_key": "risk_analysis_finding_currency_good_title",
                "title_params": {},
                "desc_key": "risk_analysis_finding_currency_good_desc"
            })

        if len(income_sources) >= 2:
            findings.append({
                "severity": "low",
                "severity_key": "risk_analysis_severity_low",
                "title_key": "risk_analysis_finding_income_good_title",
                "title_params": {"count": str(len(income_sources))},
                "desc_key": "risk_analysis_finding_income_good_desc"
            })

        return findings[:5]

    def _stress_tests(self, comp: dict) -> List[dict]:
        total_nw = _to_float(comp.get("net_worth_egp"))
        if total_nw <= 0:
            return []

        alloc_vals = comp.get("allocation_values", {})
        gold_val = _to_float(alloc_vals.get("type_gold"))
        real_estate_val = _to_float(alloc_vals.get("type_real_estate"))

        rates = comp.get("rates", {})
        foreign_val = 0.0
        totals_by_currency = comp.get("totals_by_currency", {})
        for code, amount in totals_by_currency.items():
            if str(code).upper() not in ("EGP", "GOLD"):
                foreign_val += _to_float(amount) * _to_float(rates.get(str(code).upper(), 1.0))

        scenarios = [
            {
                "id": "usd_up",
                "icon": "bi-currency-dollar",
                "title_key": "risk_analysis_stress_usd_title",
                "desc_key": "risk_analysis_stress_usd_desc",
                "impact_amount": foreign_val * 0.20,
            },
            {
                "id": "gold_down",
                "icon": "bi-coin",
                "title_key": "risk_analysis_stress_gold_title",
                "desc_key": "risk_analysis_stress_gold_desc",
                "impact_amount": gold_val * -0.15,
            },
            {
                "id": "real_estate_down",
                "icon": "bi-house-door",
                "title_key": "risk_analysis_stress_re_title",
                "desc_key": "risk_analysis_stress_re_desc",
                "impact_amount": real_estate_val * -0.10,
            }
        ]

        from core.services.salary.salary_service import get_current_monthly_salary
        salary_val = get_current_monthly_salary()
        if salary_val > 0:
            salary_annual_impact = salary_val * 6 * -1.0  # 6 months loss
            scenarios.append({
                "id": "salary_down",
                "icon": "bi-briefcase",
                "title_key": "risk_analysis_stress_salary_title",
                "desc_key": "risk_analysis_stress_salary_desc",
                "impact_amount": salary_annual_impact,
            })

        for sc in scenarios:
            sc["impact_pct"] = round((sc["impact_amount"] / total_nw) * 100.0, 1)
            sc["impact_amount"] = round(sc["impact_amount"], 2)

        return scenarios
