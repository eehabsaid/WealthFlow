"""Reading an endpoint as the user: the same numbers as the screen's own endpoint, only the user's own data, safe refusals."""

from __future__ import annotations

import json

from django.test import TestCase

from core.services.ai.screen_data import reader
from core.services.ai.tools import validate_and_execute_tool

from datetime import timedelta

from core.services.financial_advisor.cash_flow_forecast_service.custom_projection import compute_custom_cash_projection

from .support import TARGET, TODAY, tenant

CASH = "/api/financial-advisor/cash-flow-custom-projection/"


class SameNumbersAsTheScreenTest(TestCase):
    def setUp(self):
        self.user = tenant("sd_reader_a", "200000", usd="2000")

    def screen(self, **query):
        self.client.force_login(self.user)
        res = self.client.get(CASH, query)
        self.assertEqual(res.status_code, 200)
        return res.json()

    def test_the_tool_returns_exactly_what_the_cash_flow_page_endpoint_returns(self):
        page = self.screen(target_date=TARGET.isoformat())
        tool = reader.read(self.user, CASH, {"target_date": TARGET.isoformat()})
        self.assertEqual(tool["data"], page)
        self.assertEqual(tool["query_used"], {"target_date": TARGET.isoformat()})
        self.assertTrue(any(e["type"] == "certificate_maturity" for e in page["included_events"]))   # the big item a hand estimate missed

    def test_the_questions_choices_change_the_number_like_the_screens_controls_do(self):
        base = reader.read(self.user, CASH, {"target_date": TARGET.isoformat()})["data"]
        total = reader.read(self.user, CASH, {"target_date": TARGET.isoformat(), "currency_scope": "total_liquid"})["data"]
        no_interest = reader.read(self.user, CASH, {"target_date": TARGET.isoformat(), "exclude": ["certificate_maturity"]})["data"]
        self.assertEqual(base["currency_scope"], "base_only")
        self.assertEqual(total["currency_scope"], "total_liquid")
        self.assertEqual(total["currency_scope"], self.screen(target_date=TARGET.isoformat(), currency_scope="total_liquid")["currency_scope"])
        self.assertLess(no_interest["projected_balance"], base["projected_balance"])
        self.assertEqual(total, self.screen(target_date=TARGET.isoformat(), currency_scope="total_liquid"))

    def test_the_query_may_be_given_inside_the_path_or_as_text(self):
        a = reader.read(self.user, f"{CASH}?target_date={TARGET.isoformat()}", None)["data"]
        b = reader.read(self.user, CASH, json.dumps({"target_date": TARGET.isoformat()}))["data"]
        self.assertEqual(a, b)

    def test_the_agent_registry_runs_it_and_audits_it(self):
        audit, res = validate_and_execute_tool("app_screen_data", {"path": CASH, "query": {"days": 10}}, self.user)
        self.assertEqual(audit["status"], "success")
        self.assertTrue(res["ok"])
        self.assertEqual(res["data"]["data"]["currency_scope"], "base_only")


class IsolationAndSafetyTest(TestCase):
    def setUp(self):
        self.a = tenant("sd_iso_a", "200000")
        self.b = tenant("sd_iso_b", "90000")

    def test_each_user_reads_only_their_own_data(self):
        a = reader.read(self.a, CASH, {"days": 5})["data"]
        b = reader.read(self.b, CASH, {"days": 5})["data"]
        self.assertEqual(a["starting_balance"], compute_custom_cash_projection(self.a, TODAY, TODAY + timedelta(days=5))["starting_balance"])
        self.assertEqual(b["starting_balance"], compute_custom_cash_projection(self.b, TODAY, TODAY + timedelta(days=5))["starting_balance"])
        self.assertNotEqual(a["starting_balance"], b["starting_balance"])
        for path in ("/api/banks/", "/api/balance/"):
            text = json.dumps(reader.read(self.b, path, None))
            self.assertNotIn("Bank sd_iso_a", text)

    def test_refusals_are_messages_not_crashes(self):
        for path in ("/api/auth/me/", "/api/settings/", "/api/gold/refresh/", "/accounts/login/", "/api/financial-advisor/ai/chat/", "/static/x.js"):
            self.assertIn("error", reader.read(self.a, path, None), path)
        self.assertIn("no such endpoint", reader.read(self.a, "/api/not-a-thing/", None)["error"])
        self.assertIn("404", reader.read(self.a, "/api/bank-certificates/999999/", None)["error"])
        self.assertIn("error", reader.read(self.a, "/api/salary/generate-current/", None))   # a POST-only action

    def test_a_view_that_fails_reaches_the_model_as_a_message(self):
        from unittest.mock import patch

        with patch("core.services.financial_advisor.cash_flow_forecast_service.custom_projection.CashFlowForecastService",
                   side_effect=RuntimeError("boom")), self.assertLogs("core.ai.pipeline", level="WARNING"):
            res = reader.read(self.a, CASH, {"days": 5})
        self.assertIn("failed", res["error"])
        self.assertNotIn("boom", json.dumps(res))


class WholeAppCoverageTest(TestCase):
    """Every endpoint the tool offers answers for a real user: data, or the view's own message (never a crash)."""

    def test_every_endpoint_without_ids_answers(self):
        import re

        from core.services.ai.screen_data import catalog

        user = tenant("sd_cover", "80000", usd="100", sysadmin=True)
        crashed, answered = [], 0
        for e in catalog.endpoints():
            if re.search(r"<[^>]+>", e.path):
                continue
            res = reader.read(user, e.path, None)
            answered += 1
            if "calculation failed" in str(res.get("error", "")) or "unreadable" in str(res.get("error", "")):
                crashed.append((e.path, res["error"]))
        self.assertGreater(answered, 40)
        self.assertEqual(crashed, [])
