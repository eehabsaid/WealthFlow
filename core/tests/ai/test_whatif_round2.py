"""
Round-2 regression tests for the What-if follow-up fixes:

1. Empty cash timeline builds a progressive monthly series (month N carries
   N months of the net delta), with lump sums landing in their own month.
2. Numeric validation rejects NaN, infinity, booleans, and non-numeric values;
   certificate_reinvestment_choice is validated against reinvest/cashout.
3. Goal-only requests require both goal_name and extra_monthly_savings > 0.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from core.models import AppSettings, Goal, SalaryEntry
from core.services.ai.tools import validate_and_execute_tool
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.tests.ai.investigation.support import make_user, seed_tenant


def _data(res: dict) -> dict:
    return res.get("data") or {}


class WhatIfRound2Test(TestCase):
    def setUp(self):
        AppSettings.set("ai_read_only", "false")
        self.user = make_user("whatif_r2")
        tenant = seed_tenant(self.user, "R2", expenses=3)
        self.currency = tenant["currency"]
        self.company = tenant["company"]
        self.company.current_salary_currency = self.currency
        self.company.save(update_fields=["current_salary_currency"])
        self.salary = SalaryEntry.objects.get(company=self.company)
        self.salary.year, self.salary.month = 2026, "9"
        self.salary.expected, self.salary.paid, self.salary.bonus = (
            Decimal("1000.00"), Decimal("1000.00"), Decimal("0.00")
        )
        self.salary.save()
        self.goal = Goal.objects.create(
            owner=self.user, name="Car fund", goal_type="Purchase", priority="High",
            target_amount=Decimal("12000.00"), current_saved_amount=Decimal("6000.00"),
        )

    # ── Issue 1: progressive empty-timeline values ───────────────────────────

    def test_empty_timeline_is_progressive_month_by_month(self):
        """With no cash timeline, month N must carry N months of the net delta,
        not the full 12-month delta repeated. Exercised directly via a stubbed
        portfolio with an empty cash_timeline."""
        svc = WealthGrowthForecastService(self.user)
        base_portfolio = svc._portfolio()
        empty_portfolio = dict(base_portfolio)
        empty_portfolio["cash_timeline"] = []
        empty_portfolio["monthly_salary"] = 1000.0
        empty_portfolio["monthly_expenses"] = 0.0

        with patch.object(svc, "_portfolio", return_value=empty_portfolio):
            series = svc.forecast_with_overrides("expected", {"monthly_salary_scale": 1.10})

        points = series["points"]
        self.assertGreater(len(points), 3)
        values = [pt["net_worth"] for pt in points]
        # Month 0 is the baseline (cash 0). Each subsequent month adds exactly
        # one month's net delta (10% of 1000 = 100), so the series is linear.
        increment = values[1] - values[0]
        self.assertAlmostEqual(increment, 100.0, delta=1.0)
        for i in range(1, len(values)):
            self.assertAlmostEqual(values[i], values[0] + increment * i, delta=1.0, msg=f"month {i} not progressive")

    # ── Issue 2: numeric validation ───────────────────────────────────────────

    def test_nan_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"salary_change_pct": float("nan")}]}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("finite number", audit["rejection_reason"])

    def test_infinity_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"salary_change_pct": float("inf")}]}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("finite number", audit["rejection_reason"])

    def test_boolean_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"salary_change_pct": True}]}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("finite number", audit["rejection_reason"])

    def test_non_numeric_string_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"salary_change_pct": "abc"}]}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("finite number", audit["rejection_reason"])

    def test_invalid_reinvestment_choice_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"certificate_reinvestment_choice": "hold"}]},
            self.user,
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("reinvest", audit["rejection_reason"])

    def test_valid_reinvestment_choice_accepted(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"certificate_reinvestment_choice": "cashout"}]},
            self.user,
        )
        self.assertTrue(res["ok"], res)
        self.assertTrue(_data(res)["scenarios"][0]["ok"])

    # ── Issue 3: goal-only validation ─────────────────────────────────────────

    def test_goal_only_missing_savings_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"goal_name": "Car fund"}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("extra_monthly_savings", audit["rejection_reason"])

    def test_goal_only_zero_savings_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"goal_name": "Car fund", "extra_monthly_savings": 0}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("extra_monthly_savings", audit["rejection_reason"])

    def test_goal_only_valid_request_succeeds(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"goal_name": "Car fund", "extra_monthly_savings": 1000},
            self.user,
        )
        self.assertTrue(res["ok"], res)
        est = _data(res)["goal_estimate"]
        self.assertTrue(est["found"])
        self.assertEqual(est["months_with_extra_savings"], 6)  # ceil(6000 / 1000)
