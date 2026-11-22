"""Budget answer tests: Gulf, provider registration and chat end to end."""


from datetime import date, timedelta

from django.test import TestCase

from core.models import Budget, Currency, Expense, ExpenseCategory, RecurringTransaction
from core.ai_pack.providers.budgets_provider import BudgetsDataProvider
from core.ai_pack.executors.budgets import run_budgets, run_recurring
from core.services.shared.base_currency import set_user_base_currency
from core.services.shared.market_profile import ensure_base_catalog, prune_egp_for_gulf_user
from .query_engine_budgets_support import TODAY, _Base, _req


class GulfBudgetAnswerTests(_Base):
    def test_sar_user_sees_sar_and_never_egp(self):
        ensure_base_catalog(self.user, "SAR")
        set_user_base_currency(self.user, "SAR")
        prune_egp_for_gulf_user(self.user)
        sar = Currency.objects.get(owner=self.user, code="SAR")
        Budget.objects.create(owner=self.user, name="Groceries", period="monthly", amount=500, amount_base=500, currency=sar)
        RecurringTransaction.objects.create(owner=self.user, name="Netflix", amount=40, currency=sar, frequency="monthly",
                                            interval=1, start_date=TODAY, next_run_date=TODAY + timedelta(days=3))
        b = run_budgets(self.user, _req("budgets", "status"))
        r = run_recurring(self.user, _req("recurring", "total"))
        for text in (b.intro, r.intro, " ".join(" ".join(row.cells) for row in b.rows)):
            self.assertNotIn("EGP", text)
        self.assertIn("SAR", b.intro)
        self.assertIn("40.00 SAR", r.intro)


class ProviderRegistrationTests(_Base):
    def test_provider_is_discovered_and_read_only(self):
        from ai.services.providers.registry import autodiscover_providers

        provider = autodiscover_providers()["budgets"]
        self.assertTrue(provider.is_read_only)
        self.assertEqual({c.key for c in provider.get_query_capabilities()}, {"budgets", "recurring"})

    def test_anonymous_user_gets_empty_data(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(BudgetsDataProvider().get_data(AnonymousUser())["budgets"], [])


class BudgetChatEndToEndTests(TestCase):
    """The real chat endpoint answers budget/recurring questions with the LLM forbidden and never leaks another user's rows."""

    def setUp(self):
        import core.tests.ai_pack.qe_fixtures as fx

        fx.build(self)
        self.fx = fx
        egp = Currency.objects.get(owner=self.user, code="EGP")
        food = ExpenseCategory.objects.get(owner=self.user, name="Food")
        today = date.today()
        Budget.objects.create(owner=self.user, name="Groceries cap", category=food, period="monthly", amount=100, amount_base=100, currency=egp)
        Budget.objects.create(owner=self.other, name="SECRET budget", period="monthly", amount=1, amount_base=1, currency=Currency.objects.get(owner=self.other, code="EGP"))
        Expense.objects.create(owner=self.user, date=today, year=today.year, month=today.month, category=food, amount=150, amount_base=150, currency=egp)
        RecurringTransaction.objects.create(owner=self.user, name="Gym", amount=300, currency=egp, frequency="monthly", interval=1,
                                            start_date=today, next_run_date=today + timedelta(days=4))
        RecurringTransaction.objects.create(owner=self.other, name="SECRET sub", amount=9, frequency="monthly", interval=1,
                                            start_date=today, next_run_date=today + timedelta(days=4))

    def _ask(self, text):
        from unittest.mock import patch

        from ai.integrations.ai_provider import OllamaProvider

        with patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called")):
            return self.fx.ask(self, text, conversation=False)["message"]["content"]

    def test_over_budget_question(self):
        text = self._ask("which budgets am I over")
        self.assertIn("Groceries cap", text)
        self.assertNotIn("SECRET", text)

    def test_budget_remaining_question_arabic(self):
        text = self._ask("هل تجاوزت ميزانيتي")
        self.assertIn("Groceries cap", text)
        self.assertNotIn("SECRET", text)

    def test_subscription_questions(self):
        self.assertIn("Gym", self._ask("upcoming subscriptions"))
        total = self._ask("how much do my subscriptions cost per month")
        self.assertIn("300.00 EGP", total)
        self.assertNotIn("SECRET", total)

    def test_advice_about_budgets_still_goes_to_the_model(self):
        from unittest.mock import patch

        from ai.integrations.ai_provider import OllamaProvider

        with patch.object(OllamaProvider, "generate", return_value={"content": "LLM answer", "tool_calls": None, "error": None}) as gen:
            data = self.fx.ask(self, "how can I stay within my budget", conversation=False)
        self.assertTrue(gen.called)
        self.assertTrue(data["message"]["content"].startswith("LLM answer"))
