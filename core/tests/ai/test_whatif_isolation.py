"""Tenant-isolation and missing-data tests for the what_if_scenario tool."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, Expense, Goal, SalaryEntry
from core.services.ai.tools import validate_and_execute_tool
from core.tests.ai.investigation.support import make_user, seed_tenant

User = get_user_model()


def _data(res: dict) -> dict:
    return res.get("data") or {}


class WhatIfIsolationTest(TestCase):
    def setUp(self):
        AppSettings.set("ai_read_only", "false")
        self.user = make_user("whatif_iso")
        tenant = seed_tenant(self.user, "IS", expenses=3)
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

    def test_other_tenant_cannot_see_this_goal(self):
        other = make_user("whatif_iso_other")
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"salary_change_pct": 5}], "goal_name": "Car fund", "extra_monthly_savings": 500},
            other,
        )
        data = _data(res)
        if data.get("ok"):
            self.assertFalse(data["goal_estimate"]["found"])
        else:
            est = data.get("goal_estimate")
            self.assertTrue(data.get("needs_clarification") or est is not None)
            if est:
                self.assertFalse(est["found"])

    def test_missing_financial_data_requests_clarification(self):
        bare = User.objects.create_user(username="whatif_iso_bare", password="pw123456", email="bare@x.io")
        _audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"salary_change_pct": 10}]}, bare
        )
        data = _data(res)
        self.assertFalse(data.get("ok", True))
        self.assertTrue(data.get("needs_clarification"))
        self.assertIn("salary", data["error"].lower())

    def test_simulation_does_not_modify_real_records(self):
        before = {
            "expenses": Expense.objects.filter(owner=self.user).count(),
            "salary_paid": SalaryEntry.objects.get(pk=self.salary.pk).paid,
            "goal_saved": Goal.objects.get(pk=self.goal.pk).current_saved_amount,
        }
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [
                {"salary_change_pct": 25},
                {"expenses_change_pct": 20},
                {"certificate_reinvestment_choice": "cashout"},
            ]},
            self.user,
        )
        self.assertTrue(res["ok"])
        after = {
            "expenses": Expense.objects.filter(owner=self.user).count(),
            "salary_paid": SalaryEntry.objects.get(pk=self.salary.pk).paid,
            "goal_saved": Goal.objects.get(pk=self.goal.pk).current_saved_amount,
        }
        self.assertEqual(before, after)
