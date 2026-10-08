"""Salary yearly summary through the query engine: 0 LLM calls, en/ar/fr/de phrasing, tenant isolation."""

from unittest.mock import patch

from django.test import TestCase

from core.models import Company, SalaryEntry
from core.integrations.ai_provider import OllamaProvider
from . import qe_fixtures as fx

NO_LLM = patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))
PHRASINGS = [
    "yearly salary summary", "salary by year", "what is my salary per year", "annual salary",
    "الراتب سنويا", "راتبي حسب السنة",
    "salaire par an", "mon salaire annuel",
    "Gehalt pro Jahr", "jährliches Gehalt",
]


class SalaryYearlyTests(TestCase):
    def setUp(self):
        fx.build(self)
        co = Company.objects.get(owner=self.user)
        SalaryEntry.objects.create(company=co, year=2025, month="December", paid="80000", expected="80000", bonus="0")

    def test_phrasings_answer_without_llm_with_yoy_and_no_leaks(self):
        for q in PHRASINGS:
            with self.subTest(q=q), NO_LLM as gen:
                data = fx.ask(self, q)
                text = data["message"]["content"]
                for needle in ("2025", "2026", "80,000.00", "87,643.86", "+9.55%", "167,643.86"):
                    self.assertIn(needle, text)
                self.assertNotIn("111.00", text)
                call = data["message"]["tool_calls"][0]
                self.assertTrue(call["direct_answer"])
                self.assertEqual(call["llm_calls"], 0)
                gen.assert_not_called()

    def test_year_named_restricts_the_table(self):
        with NO_LLM:
            text = fx.ask(self, "salary by year for 2026")["message"]["content"]
        self.assertIn("87,643.86", text)
        self.assertNotIn("80,000.00", text)

    def test_other_tenant_sees_only_own_years(self):
        from core.tests.billing.test_support import grant_ai_workspace_access

        grant_ai_workspace_access(self.other)
        self.client.force_login(self.other)
        with NO_LLM:
            text = fx.ask(self, "yearly salary summary")["message"]["content"]
        self.assertIn("111.00", text)
        self.assertNotIn("87,643.86", text)

    def test_monthly_salary_questions_unchanged(self):
        with NO_LLM:
            self.assertIn("87,643.86", fx.ask(self, "What was my paid salary for January 2026?")["message"]["content"])
