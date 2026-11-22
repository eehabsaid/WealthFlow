"""Instant AI answers for Budgets and Recurring transactions: owner-scoped, base-currency, Gulf-safe."""


from datetime import timedelta


from core.models import Currency, RecurringTransaction
from core.ai_pack.providers.budgets_provider import BudgetsDataProvider
from ai.services.query_engine import get_capability, route
from core.ai_pack.executors.budgets import run_budgets, run_recurring
from ai.services.query_engine.spec import QueryRequest
from .query_engine_budgets_support import TODAY, _Base, _req


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
