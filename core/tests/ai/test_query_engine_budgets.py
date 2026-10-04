"""Instant AI answers for Budgets and Recurring transactions: owner-scoped, base-currency, Gulf-safe."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Budget, Currency, Expense, ExchangeRate, ExpenseCategory, RecurringTransaction
from core.services.ai.providers.budgets_provider import BudgetsDataProvider
from core.services.ai.query_engine import get_capability, route
from core.services.ai.query_engine.executors.budgets import run_budgets, run_recurring
from core.services.ai.query_engine.spec import QueryRequest
from core.services.shared.base_currency import set_user_base_currency
from core.services.shared.market_profile import ensure_base_catalog, prune_egp_for_gulf_user

User = get_user_model()
TODAY = date.today()


def _req(cap, metric="", **filters):
    return QueryRequest(capability=cap, metric=metric, filters=filters)


class _Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="qe_bud", password="pw-12345-x")
        self.other = User.objects.create_user(username="qe_bud_other", password="pw-12345-x")
        for code, rate in (("USD", "50"), ("SAR", "13.333333"), ("AED", "13.6")):
            ExchangeRate.objects.create(currency_code=code, currency_name=code, buy_rate=Decimal(rate),
                                        sell_rate=Decimal(rate), mid_rate=Decimal(rate))
        self.egp, _ = Currency.objects.get_or_create(owner=self.user, code="EGP", defaults={"name": "Egyptian Pound"})
        self.food, _ = ExpenseCategory.objects.get_or_create(owner=self.user, name="Food")

    def budget(self, owner=None, name="Food budget", amount=1000, category=None, **kw):
        return Budget.objects.create(owner=owner or self.user, name=name, category=category, period="monthly",
                                     amount=amount, amount_base=amount, currency=self.egp, **kw)

    def spend(self, amount, category=None):
        Expense.objects.create(owner=self.user, date=TODAY, year=TODAY.year, month=TODAY.month, category=category,
                               amount=amount, amount_base=amount, currency=self.egp)


class BudgetAnswerTests(_Base):
    def test_status_shows_spend_and_percent(self):
        self.budget(category=self.food)
        self.spend(250, self.food)
        res = run_budgets(self.user, _req("budgets", "status"))
        self.assertEqual(res.rows[0].cells[0], "Food budget")
        self.assertEqual(res.rows[0].cells[-1], "25.0%")
        self.assertEqual(res.facts["over"], 0)

    def test_over_lists_only_exceeded_and_near_budgets(self):
        self.budget(name="Tight", amount=100, category=self.food)
        self.budget(name="Roomy", amount=100000)
        self.spend(120, self.food)
        res = run_budgets(self.user, _req("budgets", "over"))
        self.assertEqual([r.cells[0] for r in res.rows], ["Tight"])
        self.assertEqual(res.facts["over"], 1)

    def test_over_when_everything_is_fine(self):
        self.budget(amount=100000)
        res = run_budgets(self.user, _req("budgets", "over"))
        self.assertIn("within their limits", res.intro)
        self.assertEqual(res.rows, [])

    def test_remaining_never_counts_overspend_as_negative_room(self):
        self.budget(name="A", amount=100, category=self.food)
        self.budget(name="B", amount=500)
        self.spend(300, self.food)   # A is 200 over, B is 300 spent of 500 (shared: overall budget counts all spend)
        res = run_budgets(self.user, _req("budgets", "remaining"))
        self.assertIn("200.00 EGP", res.intro)  # only B's room (500 - 300); A contributes 0, not -200

    def test_category_filter_and_unknown_category(self):
        self.budget(category=self.food)
        self.budget(name="Overall", amount=5000)
        only = run_budgets(self.user, _req("budgets", "status", category="Food"))
        self.assertEqual([r.cells[0] for r in only.rows], ["Food budget"])
        missing = run_budgets(self.user, _req("budgets", "status", category="Fuel"))
        self.assertIn("Fuel", missing.intro)

    def test_other_users_budgets_are_never_visible(self):
        self.budget(owner=self.other, name="Secret")
        self.assertIn("No active budgets", run_budgets(self.user, _req("budgets", "status")).intro)
        provider_names = [b["name"] for b in BudgetsDataProvider().get_data(self.user)["budgets"]]
        self.assertNotIn("Secret", provider_names)

    def test_inactive_budgets_are_ignored(self):
        self.budget(is_active=False)
        self.assertIn("No active budgets", run_budgets(self.user, _req("budgets", "status")).intro)

    def test_past_month_is_refused_not_answered_with_todays_figures(self):
        self.budget()
        past = (TODAY.year, TODAY.month - 1) if TODAY.month > 1 else (TODAY.year - 1, 12)
        req = QueryRequest(capability="budgets", periods=[past])
        self.assertIn("current state", run_budgets(self.user, req).intro)
        current = QueryRequest(capability="budgets", periods=[(TODAY.year, TODAY.month)])
        self.assertNotIn("current state", run_budgets(self.user, current).intro)

    def test_arabic_answer(self):
        self.budget()
        res = run_budgets(self.user, QueryRequest(capability="budgets", lang="ar"))
        self.assertIn("حالة الميزانيات", res.intro)

    def test_routing_end_to_end(self):
        r = route("which budgets am I over")
        self.assertEqual((r.status, r.capability, r.request.metric), ("ready", "budgets", "over"))
        self.assertIs(get_capability("budgets").executor, run_budgets)


class RecurringAnswerTests(_Base):
    def rec(self, name, amount, days_ahead, owner=None, frequency="monthly", interval=1, currency=None, **kw):
        return RecurringTransaction.objects.create(
            owner=owner or self.user, name=name, amount=amount, currency=currency or self.egp, frequency=frequency,
            interval=interval, start_date=TODAY, next_run_date=TODAY + timedelta(days=days_ahead), **kw)

    def test_list_is_sorted_by_next_due_and_owner_scoped(self):
        self.rec("Later", 10, 20)
        self.rec("Sooner", 20, 2)
        self.rec("Hidden", 99, 1, owner=self.other)
        res = run_recurring(self.user, _req("recurring", "list"))
        self.assertEqual([r.cells[0] for r in res.rows], ["Sooner", "Later"])

    def test_upcoming_only_within_30_days(self):
        self.rec("Soon", 10, 5)
        self.rec("Far", 10, 90)
        res = run_recurring(self.user, _req("recurring", "upcoming"))
        self.assertEqual([r.cells[0] for r in res.rows], ["Soon"])
        self.rec("Soon2", 1, 1)
        RecurringTransaction.objects.filter(name="Soon").update(is_active=False)
        RecurringTransaction.objects.filter(name="Soon2").update(is_active=False)
        self.assertIn("Nothing recurring", run_recurring(self.user, _req("recurring", "upcoming")).intro)

    def test_monthly_total_normalizes_frequency_and_interval(self):
        self.rec("Rent", 1000, 3)                                   # 1000 / month
        self.rec("Weekly gym", 12, 3, frequency="weekly")           # 12 * 52/12 = 52
        self.rec("Insurance", 1200, 3, frequency="yearly")          # 100 / month
        self.rec("Bi-monthly", 600, 3, interval=2)                  # 300 / month
        res = run_recurring(self.user, _req("recurring", "total"))
        self.assertAlmostEqual(res.facts["monthly_total"], 1000 + 52 + 100 + 300, places=2)

    def test_total_converts_to_base_and_skips_unrated_currency(self):
        usd, _ = Currency.objects.get_or_create(owner=self.user, code="USD", defaults={"name": "US Dollar"})
        gbp, _ = Currency.objects.get_or_create(owner=self.user, code="GBP", defaults={"name": "Pound"})
        self.rec("US service", 10, 3, currency=usd)     # 10 USD * 50 = 500 EGP
        self.rec("UK service", 10, 3, currency=gbp)     # no GBP rate stored: left out, never guessed
        res = run_recurring(self.user, _req("recurring", "total"))
        self.assertAlmostEqual(res.facts["monthly_total"], 500.0, places=1)
        self.assertIn("left out", res.intro)

    def test_empty_state(self):
        self.assertIn("No active recurring", run_recurring(self.user, _req("recurring", "list")).intro)

    def test_routing_end_to_end(self):
        r = route("how much do my subscriptions cost per month")
        self.assertEqual((r.status, r.capability, r.request.metric), ("ready", "recurring", "total"))


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
        from core.services.ai.providers.registry import autodiscover_providers

        provider = autodiscover_providers()["budgets"]
        self.assertTrue(provider.is_read_only)
        self.assertEqual({c.key for c in provider.get_query_capabilities()}, {"budgets", "recurring"})

    def test_anonymous_user_gets_empty_data(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(BudgetsDataProvider().get_data(AnonymousUser())["budgets"], [])


class BudgetChatEndToEndTests(TestCase):
    """The real chat endpoint answers budget/recurring questions with the LLM forbidden and never leaks another user's rows."""

    def setUp(self):
        from . import qe_fixtures as fx

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

        from core.integrations.ai_provider import OllamaProvider

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

        from core.integrations.ai_provider import OllamaProvider

        with patch.object(OllamaProvider, "generate", return_value={"content": "LLM answer", "tool_calls": None, "error": None}) as gen:
            data = self.fx.ask(self, "how can I stay within my budget", conversation=False)
        self.assertTrue(gen.called)
        self.assertTrue(data["message"]["content"].startswith("LLM answer"))
