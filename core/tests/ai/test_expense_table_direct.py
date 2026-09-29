"""Multi-month detailed expense table answered by code (no LLM): month total rows + grand total."""

import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from core.integrations.ai_provider import OllamaProvider
from core.models import AppSettings, Expense, ExpenseCategory
from core.services.ai.expense_table_direct import match_expense_table_intent
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
CHAT_URL = "/api/financial-advisor/ai/chat/"
EHAB_Q = ("give me a detailed expenses in a organized table for:\nJun 2026\nJul 2026\nAug 2026\nSept 2026\n"
          "and the total row after the end of each month, and grand total row after the all months")


class TableIntentTests(SimpleTestCase):
    def test_matches_real_question(self):
        mode, periods = match_expense_table_intent(EHAB_Q)
        self.assertEqual(mode, "transactions")
        self.assertEqual(periods, [(2026, 6), (2026, 7), (2026, 8), (2026, 9)])

    def test_category_mode_and_fallthrough(self):
        self.assertEqual(match_expense_table_intent("expenses breakdown by category table for Aug 2026 and Sept 2026")[0], "category")
        for q in ("compare expenses table Aug 2026 and Sept 2026", "why did my expenses table for Jun 2026 grow",
                  "detailed expenses table", "salary table for Jun 2026", "جدول المصروفات Jun 2026"):
            self.assertIsNone(match_expense_table_intent(q), q)


class TableChatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tbl_user", password="pw123456")
        self.other = User.objects.create_user(username="tbl_other", password="pw123456")
        grant_ai_workspace_access(self.user)
        for owner, name in ((self.user, "Food"), (self.other, "Secret")):
            c = ExpenseCategory.objects.create(owner=owner, name=name)
            for m, d, amt, desc in ((6, 1, "100.00", "Rice"), (6, 2, "50.50", "Milk"), (8, 5, "20.00", "Tea"), (9, 1, "1000.00", "Rent")):
                Expense.objects.create(owner=owner, category=c, date=date(2026, m, d), year=2026, month=m,
                                       amount=amt, amount_base=amt, description=desc)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_provider", "ollama")
        self.client.force_login(self.user)

    @patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))
    def test_table_with_month_and_grand_totals_no_llm(self, gen):
        res = self.client.post(CHAT_URL, json.dumps({"message": EHAB_Q}), content_type="application/json").json()
        text = res["message"]["content"]
        self.assertIn("| Jun 2026 | 2026-06-01 | Food | Rice | 100.00", text)
        self.assertIn("**Total Jun 2026**", text)
        self.assertIn("150.50", text)
        self.assertIn("**Total Jul 2026**", text)  # empty month still gets a total row (0.00)
        self.assertIn("No expenses are recorded for: Jul 2026", text)
        self.assertIn("**Grand Total**", text)
        self.assertIn("1,170.50", text.replace("1170.50", "1,170.50"))
        self.assertLess(text.index("Total Jun 2026"), text.index("Aug 2026 |"))
        self.assertGreater(text.index("Grand Total"), text.index("Total Sep 2026"))
        self.assertNotIn("Secret", text)
        self.assertTrue(res["message"]["tool_calls"][0]["direct_answer"])
        gen.assert_not_called()
