"""
Regression tests for the four What-if follow-up fixes:

1. Expense/salary overrides affect forecasts even without cash timeline events.
2. Invalid percentages / numeric values are explicitly rejected with clear errors.
3. gold_allocation_target_pct=0 is treated as a valid explicit value (not a no-op).
4. Goal-only requests (goal_name + extra_monthly_savings) work without scenarios.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from core.models import AppSettings, Goal, SalaryEntry
from ai.services.tools import validate_and_execute_tool
from core.tests.ai_pack.investigation.support import make_user, seed_tenant


def _data(res: dict) -> dict:
    return res.get("data") or {}


class WhatIfRegressionTest(TestCase):
    def setUp(self):
        AppSettings.set("ai_read_only", "false")
        self.user = make_user("whatif_reg")
        tenant = seed_tenant(self.user, "RG", expenses=3)
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

    # ── Issue 1: expense overrides without timeline events ───────────────────

    def test_expense_cut_affects_forecast_without_timeline(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"expenses_change_pct": -10}]},
            self.user,
        )
        self.assertTrue(res["ok"], res)
        sc = _data(res)["scenarios"][0]
        self.assertTrue(sc["ok"])
        self.assertGreater(sc["adjusted"]["net_worth_12m"], sc["baseline"]["net_worth_12m"])

    def test_expense_increase_affects_forecast_without_timeline(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"expenses_change_pct": 20}]},
            self.user,
        )
        self.assertTrue(res["ok"], res)
        sc = _data(res)["scenarios"][0]
        self.assertTrue(sc["ok"])
        self.assertLess(sc["adjusted"]["net_worth_12m"], sc["baseline"]["net_worth_12m"])

    # ── Issue 2: explicit range validation ────────────────────────────────────

    def test_salary_pct_out_of_range_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"salary_change_pct": 150}]}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("between -100 and 100", audit["rejection_reason"])

    def test_expenses_pct_out_of_range_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"expenses_change_pct": -80}]}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("between -50 and 100", audit["rejection_reason"])

    def test_gold_negative_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"gold_allocation_target_pct": -5}]}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn(">= 0", audit["rejection_reason"])

    def test_extra_savings_negative_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"salary_change_pct": 5}], "extra_monthly_savings": -100},
            self.user,
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn(">= 0", audit["rejection_reason"])

    # ── Issue 3: gold_allocation_target_pct=0 is a valid explicit value ───────

    def test_gold_target_zero_is_accepted_as_change(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"gold_allocation_target_pct": 0}]},
            self.user,
        )
        self.assertTrue(res["ok"], res)
        sc = _data(res)["scenarios"][0]
        self.assertTrue(sc["ok"])
        self.assertEqual(sc["parameters"]["gold_allocation_target_pct"], 0.0)

    # ── Issue 4: goal-only scenarios ──────────────────────────────────────────

    def test_goal_only_request_without_scenarios(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"goal_name": "Car fund", "extra_monthly_savings": 500},
            self.user,
        )
        self.assertTrue(res["ok"], res)
        data = _data(res)
        self.assertEqual(data["scenarios"], [])
        est = data["goal_estimate"]
        self.assertTrue(est["found"])
        self.assertEqual(est["remaining"], 6000.0)
        self.assertEqual(est["months_with_extra_savings"], 12)

    def test_no_scenarios_and_no_goal_rejected(self):
        audit, res = validate_and_execute_tool("what_if_scenario", {}, self.user)
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("goal_name", audit["rejection_reason"])

    # ── Gold-allocation rounding bug ──────────────────────────────────────────

    def test_expense_only_simulation_keeps_identical_starting_net_worth(self):
        """An expense-only simulation must not inject a spurious gold override:
        the starting (month 0) net worth must be identical in baseline and
        adjusted series."""
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"expenses_change_pct": -10}]},
            self.user,
        )
        self.assertTrue(res["ok"], res)
        sc = _data(res)["scenarios"][0]
        self.assertTrue(sc["ok"])
        baseline_start = sc["baseline"]["series"][0]["net_worth"]
        adjusted_start = sc["adjusted"]["series"][0]["net_worth"]
        self.assertEqual(baseline_start, adjusted_start)

