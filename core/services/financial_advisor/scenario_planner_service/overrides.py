"""Scenario-event-to-forecast-override translation mixin for ScenarioPlannerService.

NOTE (200-line file convention): extracted from the original monolithic
core/services/financial_advisor/scenario_planner_service.py (716 lines).
See __init__.py for the full package layout.
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.models import ScenarioEvent

from .config import _to_float


class OverridesMixin:
    """Provides _events_to_overrides(); mixed into ScenarioPlannerService."""

    def _events_to_overrides(
        self, events: List[ScenarioEvent], monthly_salary: float = 0.0
    ) -> tuple[dict, float, int | None]:
        """Translates a list of ScenarioEvents into WealthGrowthForecastService overrides.

        Returns (overrides_dict, scenario_added_debt, scenario_target_age).
        Reuses existing override keys (monthly_salary_scale, monthly_expense_scale)
        and minimal extended keys (monthly_salary_delta, monthly_expense_delta,
        lump_sum_outflows, lump_sum_inflows).
        """
        salary_scale = 1.0
        salary_delta = 0.0
        expense_delta = 0.0
        lump_outflows: List[dict] = []
        lump_inflows: List[dict] = []
        added_debt = 0.0
        scenario_target_age: int | None = None

        for idx, ev in enumerate(events):
            etype = str(ev.event_type or "").lower()
            p = ev.params or {}
            ev_date = ev.event_date or self.today

            # Calculate month_index (1..12) relative to current month
            m_index = max(1, (ev_date.year - self.today.year) * 12 + (ev_date.month - self.today.month) + 1)
            m_index = min(12, m_index)

            if etype == "house":
                down_pay = _to_float(p.get("down_payment"))
                price = _to_float(p.get("purchase_price"))
                installment = _to_float(p.get("monthly_installment"))
                if down_pay > 0:
                    lump_outflows.append({"month_index": m_index, "amount": down_pay})
                if installment > 0:
                    expense_delta += installment
                if price > down_pay:
                    added_debt += (price - down_pay)

            elif etype == "car":
                down_pay = _to_float(p.get("down_payment"))
                price = _to_float(p.get("purchase_price"))
                installment = _to_float(p.get("monthly_installment"))
                maint = _to_float(p.get("maintenance_monthly"))
                if down_pay > 0:
                    lump_outflows.append({"month_index": m_index, "amount": down_pay})
                if (installment + maint) > 0:
                    expense_delta += (installment + maint)
                if price > down_pay:
                    added_debt += (price - down_pay)

            elif etype == "salary_change":
                change_type = str(p.get("change_type", "percentage"))
                if change_type == "percentage":
                    pct = _to_float(p.get("salary_change_pct"))
                    salary_scale *= (1.0 + pct / 100.0)
                else:
                    amt = _to_float(p.get("salary_change_amount"))
                    salary_delta += amt

            elif etype == "marriage":
                cost = _to_float(p.get("one_time_cost"))
                new_exp = _to_float(p.get("new_monthly_expense"))
                if cost > 0:
                    lump_outflows.append({"month_index": m_index, "amount": cost})
                if new_exp > 0:
                    expense_delta += new_exp

            elif etype == "child":
                cost = _to_float(p.get("one_time_cost"))
                new_exp = _to_float(p.get("new_monthly_expense"))
                if cost > 0:
                    lump_outflows.append({"month_index": m_index, "amount": cost})
                if new_exp > 0:
                    expense_delta += new_exp

            elif etype == "inheritance":
                amt = _to_float(p.get("lump_sum_amount"))
                if amt > 0:
                    lump_inflows.append({"month_index": m_index, "amount": amt})

            elif etype == "medical":
                cost = _to_float(p.get("one_time_cost"))
                ongoing = _to_float(p.get("monthly_ongoing_cost") or p.get("ongoing_cost"))
                if cost > 0:
                    lump_outflows.append({"month_index": m_index, "amount": cost})
                if ongoing > 0:
                    expense_delta += ongoing

            elif etype == "business":
                cap = _to_float(p.get("capital_investment"))
                profit = _to_float(p.get("monthly_net_profit"))
                if cap > 0:
                    lump_outflows.append({"month_index": m_index, "amount": cap})
                salary_delta += profit

            elif etype == "job_loss":
                # Approximation: Lump-sum hit for duration_months of lost salary vs flat global scale-to-zero.
                duration = int(_to_float(p.get("duration_months") or 12))
                duration = max(1, min(duration, 12))
                lost_salary = monthly_salary * duration
                if lost_salary > 0:
                    lump_outflows.append({"month_index": m_index, "amount": lost_salary})

            elif etype == "retirement":
                age_val = _to_float(p.get("target_age"))
                if age_val > 0:
                    scenario_target_age = int(age_val)

        overrides: Dict[str, Any] = {}
        if salary_scale != 1.0:
            overrides["monthly_salary_scale"] = salary_scale
        if salary_delta != 0.0:
            overrides["monthly_salary_delta"] = salary_delta
        if expense_delta != 0.0:
            overrides["monthly_expense_delta"] = expense_delta
        if lump_outflows:
            overrides["lump_sum_outflows"] = lump_outflows
        if lump_inflows:
            overrides["lump_sum_inflows"] = lump_inflows

        return overrides, added_debt, scenario_target_age

