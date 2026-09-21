import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from core.integrations.ai_provider import OllamaProvider
from core.models import AppSettings, Company, SalaryEntry
from core.services.ai.direct_answers import _match_salary
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
CHAT_URL = "/api/financial-advisor/ai/chat/"


class MatchSalaryTests(SimpleTestCase):
    def test_simple_month_question(self):
        for q in ("What was my paid salary for January 2026?",
                  "salary in jan 2026",
                  "How much was my salary in March 2025?"):
            self.assertEqual(_match_salary(q), "requested_period_answer", q)

    def test_latest_question(self):
        self.assertEqual(_match_salary("What is my latest paid salary?"), "latest_paid_salary_answer")
        self.assertEqual(_match_salary("last salary"), "latest_paid_salary_answer")

    def test_falls_through_to_llm(self):
        for q in ("Compare my salary January 2026 and February 2026",
                  "What was my salary in January 2026 and what about bonus?",
                  "salary january 2026 february 2026",
                  "Why did my salary drop in January 2026?",
                  "What is my current salary?",
                  "show my salary",
                  "ما هو راتبي في يناير 2026",
                  "What is my cash flow in January 2026?",
                  ""):
            self.assertIsNone(_match_salary(q), q)


class DirectAnswerChatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="da_user", password="pw123456")
        self.other = User.objects.create_user(username="da_other", password="pw123456")
        grant_ai_workspace_access(self.user)
        for owner, paid in ((self.user, "87643.86"), (self.other, "111.00")):
            co = Company.objects.create(owner=owner, name="Acme", display_name="Acme")
            SalaryEntry.objects.create(company=co, year=2026, month="January", paid=paid, expected=paid)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_provider", "ollama")
        self.client.force_login(self.user)

    def _post(self, text):
        return self.client.post(CHAT_URL, json.dumps({"message": text}), content_type="application/json")

    @patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))
    def test_month_question_answers_without_llm(self, gen):
        res = self._post("What was my paid salary for January 2026?")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertIn("87,643.86", data["message"]["content"])
        self.assertNotIn("111.00", data["message"]["content"])  # other tenant's data
        self.assertTrue(data["message"]["tool_calls"][0]["direct_answer"])
        gen.assert_not_called()

    @patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))
    def test_missing_month_is_reported_without_llm(self, gen):
        data = self._post("salary for March 2026").json()
        self.assertIn("No salary entry is recorded for March 2026", data["message"]["content"])

    @patch.object(OllamaProvider, "generate")
    def test_complex_question_still_uses_llm(self, gen):
        gen.return_value = {"content": "LLM answer", "error": None}
        data = self._post("Compare my salary January 2026 and February 2026").json()
        self.assertEqual(data["message"]["content"], "LLM answer")
        self.assertTrue(gen.called)

    @patch.object(OllamaProvider, "generate")
    def test_kill_switch(self, gen):
        gen.return_value = {"content": "LLM answer", "error": None}
        AppSettings.set("ai_direct_answers", "false", user=self.user)
        data = self._post("What was my paid salary for January 2026?").json()
        self.assertEqual(data["message"]["content"], "LLM answer")
