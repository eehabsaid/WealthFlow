import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from core.integrations.ai_provider import OllamaProvider
from core.models import AppSettings, Expense, ExpenseCategory
from core.services.ai.expense_direct import match_expense_intent
from core.services.ai.period_parser import find_periods
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
CHAT_URL = "/api/financial-advisor/ai/chat/"


class PeriodParserTests(SimpleTestCase):
    def test_formats(self):
        today = date(2026, 1, 15)
        self.assertEqual(find_periods("Sept-2026"), [(2026, 9)])
        self.assertEqual(find_periods("sept 2026"), [(2026, 9)])
        self.assertEqual(find_periods("September 2026"), [(2026, 9)])
        self.assertEqual(find_periods("jan/2026"), [(2026, 1)])
        self.assertEqual(find_periods("2026-09"), [(2026, 9)])
        self.assertEqual(find_periods("09/2026"), [(2026, 9)])
        self.assertEqual(find_periods("this month", today), [(2026, 1)])
        self.assertEqual(find_periods("last month", today), [(2025, 12)])
        self.assertEqual(find_periods("Aug 2026 and Sep 2026"), [(2026, 8), (2026, 9)])
        self.assertEqual(find_periods("in 2026"), [])
        self.assertEqual(find_periods("may I ask"), [])


class ExpenseIntentTests(SimpleTestCase):
    def test_matches(self):
        self.assertEqual(match_expense_intent("what is my total expenses in Sept-2026"), ("total", (2026, 9)))
        self.assertEqual(match_expense_intent("how much did I spend in 2026-08"), ("total", (2026, 8)))
        self.assertEqual(
            match_expense_intent("can you detail it to list me the daily expenses for Sept-2026"), ("daily", (2026, 9)))
        self.assertEqual(match_expense_intent("expenses by category for September 2026"), ("category", (2026, 9)))

    def test_falls_through(self):
        for q in ("compare expenses Aug 2026 and Sept 2026", "show my expenses", "total expenses",
                  "why are my expenses high in Sept 2026", "what is my top expense in Sept 2026",
                  "daily expenses by category for Sept 2026", "المصروفات في سبتمبر 2026",
                  "what is my salary in Sept 2026", ""):
            self.assertIsNone(match_expense_intent(q), q)


class ExpenseDirectChatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ex_user", password="pw123456")
        self.other = User.objects.create_user(username="ex_other", password="pw123456")
        grant_ai_workspace_access(self.user)
        for owner, cat in ((self.user, "Food"), (self.other, "Secret")):
            c = ExpenseCategory.objects.create(owner=owner, name=cat) if _has_owner() else ExpenseCategory.objects.create(name=cat)
            for d, amt, desc in ((1, "100.00", "Rice"), (1, "50.50", "Milk"), (3, "20.00", "Tea")):
                Expense.objects.create(owner=owner, category=c, date=date(2026, 9, d), year=2026, month=9,
                                       amount=amt, amount_egp=amt, description=desc)
        Expense.objects.create(owner=self.user, category=Expense.objects.filter(owner=self.user).first().category,
                               date=date(2026, 8, 5), year=2026, month=8, amount="999.00", amount_egp="999.00")
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_provider", "ollama")
        self.client.force_login(self.user)

    def _post(self, text):
        return self.client.post(CHAT_URL, json.dumps({"message": text}), content_type="application/json")

    @patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))
    def test_total_daily_category_without_llm(self, gen):
        total = self._post("what is my total expenses in Sept-2026").json()["message"]["content"]
        self.assertIn("170.50", total)
        self.assertIn("3 transactions", total)
        daily = self._post("list me the daily expenses for Sept-2026").json()
        self.assertIn("| 2026-09-01 | 150.50", daily["message"]["content"])
        self.assertIn("| 2026-09-03 | 20.00", daily["message"]["content"])
        self.assertNotIn("Secret", daily["message"]["content"])
        self.assertTrue(daily["message"]["tool_calls"][0]["direct_answer"])
        cat = self._post("expenses by category for September 2026").json()["message"]["content"]
        self.assertIn("| Food |", cat)
        self.assertNotIn("Secret", cat)
        none = self._post("total expenses in March 2026").json()["message"]["content"]
        self.assertEqual(none, "No expenses are recorded for March 2026.")
        gen.assert_not_called()

    @patch.object(OllamaProvider, "generate")
    def test_other_questions_use_llm(self, gen):
        gen.return_value = {"content": "LLM answer", "error": None}
        data = self._post("compare expenses Aug 2026 and Sept 2026").json()
        self.assertEqual(data["message"]["content"], "LLM answer")


def _has_owner():
    return any(f.name == "owner" for f in ExpenseCategory._meta.get_fields())
