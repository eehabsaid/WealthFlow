"""
Tests for the dedicated what_if_scenario AI tool and the What-If simulator fixes.

Covers: tool registration/schema, execution (single + multi-scenario), goal
estimate, validation rejections, and the cash-coverage salary fix.
Tenant isolation, missing-data clarification and read-only guarantee tests
live in test_whatif_isolation.py; intent tests in test_whatif_intent.py.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.test import TestCase

from core.models import AppSettings, Goal, SalaryEntry
from core.services.ai.tools import get_registered_tool_schemas, validate_and_execute_tool
from core.services.financial_advisor.what_if_simulator_service import WhatIfSimulatorService
from core.tests.ai.investigation.support import make_user, seed_tenant


def _data(res: dict) -> dict:
    """validate_and_execute_tool wraps the handler result in res['data']."""
    return res.get("data") or {}


class WhatIfScenarioToolTest(TestCase):
    def setUp(self):
        AppSettings.set("ai_read_only", "false")
        self.user = make_user("whatif_tool")
        tenant = seed_tenant(self.user, "WI", expenses=3)
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
            target_date=datetime.date(2027, 6, 1),
        )

    # ── Registration ──────────────────────────────────────────────────────────

    def test_tool_is_registered_with_read_tier(self):
        from core.services.ai.tools.defs import AI_TOOL_REGISTRY

        tool = AI_TOOL_REGISTRY["what_if_scenario"]
        self.assertTrue(tool["is_read_only"])
        self.assertEqual(tool["tier"], "read")
        names = [s["function"]["name"] for s in get_registered_tool_schemas()]
        self.assertIn("what_if_scenario", names)

    # ── Execution ─────────────────────────────────────────────────────────────

    def test_salary_raise_scenario_returns_baseline_and_adjusted(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"salary_change_pct": 15}]},
            self.user,
        )
        self.assertEqual(audit["status"], "success", res)
        self.assertTrue(res["ok"])
        data = _data(res)
        self.assertTrue(data["read_only"])
        sc = data["scenarios"][0]
        self.assertTrue(sc["ok"])
        self.assertEqual(sc["parameters"]["salary_change_pct"], 15.0)
        self.assertIn("baseline", sc)
        self.assertIn("adjusted", sc)
        self.assertIn("delta", sc)
        # A 15% raise must improve the 12-month net worth vs baseline.
        self.assertGreater(sc["adjusted"]["net_worth_12m"], sc["baseline"]["net_worth_12m"])

    def test_expense_change_scenario_executes(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"expenses_change_pct": 20}]},
            self.user,
        )
        self.assertTrue(res["ok"])
        sc = _data(res)["scenarios"][0]
        self.assertTrue(sc["ok"])
        self.assertEqual(sc["parameters"]["expenses_change_pct"], 20.0)

    def test_multi_scenario_comparison(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [
                {"salary_change_pct": 10},
                {"expenses_change_pct": -10},
            ]},
            self.user,
        )
        self.assertTrue(res["ok"])
        scenarios = _data(res)["scenarios"]
        self.assertEqual(len(scenarios), 2)
        self.assertTrue(all(s["ok"] for s in scenarios))

    def test_goal_estimate_uses_real_remaining(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"salary_change_pct": 5}], "goal_name": "Car fund", "extra_monthly_savings": 500},
            self.user,
        )
        self.assertTrue(res["ok"])
        est = _data(res)["goal_estimate"]
        self.assertTrue(est["found"])
        self.assertEqual(est["remaining"], 6000.0)
        self.assertEqual(est["months_with_extra_savings"], 12)  # ceil(6000 / 500)

    def test_goal_not_found_is_reported(self):
        _audit, res = validate_and_execute_tool(
            "what_if_scenario",
            {"scenarios": [{"salary_change_pct": 5}], "goal_name": "No such goal", "extra_monthly_savings": 500},
            self.user,
        )
        self.assertTrue(res["ok"])
        self.assertFalse(_data(res)["goal_estimate"]["found"])

    # ── Validation ────────────────────────────────────────────────────────────

    def test_empty_scenarios_rejected(self):
        audit, res = validate_and_execute_tool("what_if_scenario", {"scenarios": []}, self.user)
        self.assertEqual(audit["status"], "rejected")
        self.assertFalse(res["ok"])

    def test_scenario_without_hypothetical_change_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"salary_change_pct": 0}]}, self.user
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertFalse(res["ok"])

    def test_anonymous_user_rejected(self):
        audit, res = validate_and_execute_tool(
            "what_if_scenario", {"scenarios": [{"salary_change_pct": 10}]}, None
        )
        self.assertEqual(audit["status"], "rejected")
        self.assertIn("authentication", audit["rejection_reason"].lower())

    # ── Cash-coverage computation fix ─────────────────────────────────────────

    def test_cash_coverage_uses_real_salary_not_cash_proxy(self):
        svc = WhatIfSimulatorService(self.user)
        # Real salary 1000/month, +100% => +12000 over 12 months.
        with_salary = svc._compute_cash_coverage(
            cash_balance=100.0, avg_monthly_expenses=100.0,
            salary_change_pct=100.0, expenses_change_pct=0.0, monthly_salary=1000.0,
        )
        self.assertEqual(with_salary, 121.0)  # (100 + 12000) / 100
        # Without a real salary the legacy proxy applies: 100 * 1.0 = 200.
        without_salary = svc._compute_cash_coverage(
            cash_balance=100.0, avg_monthly_expenses=100.0,
            salary_change_pct=100.0, expenses_change_pct=0.0, monthly_salary=0.0,
        )
        self.assertEqual(without_salary, 2.0)  # (100 + 100) / 100

