"""Proactive insights: computed by code from the user's own data."""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Budget, Company, Currency, Expense, SalaryEntry
from ai.services.insights import compute_insights
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
TODAY = datetime.date(2026, 10, 20)


class InsightTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")
        self.other = User.objects.create_user(username="other", password="pw12345!")
        for u in (self.user, self.other):
            grant_ai_workspace_access(u)
        self.egp, _ = Currency.objects.get_or_create(owner=self.user, code="EGP", defaults={"name": "Pound"})

    def spend(self, amount, d, owner=None):
        Expense.objects.create(owner=owner or self.user, date=d, year=d.year, month=d.month, amount=Decimal(amount), amount_base=Decimal(amount), currency=self.egp)

    def types(self, user=None):
        return [i["type"] for i in compute_insights(user or self.user, TODAY)]

    def test_empty_account_has_no_insights(self):
        self.assertEqual(self.types(), [])

    def test_month_vs_last_compares_the_same_days_and_uses_real_numbers(self):
        self.spend("100", datetime.date(2026, 9, 5))
        self.spend("900", datetime.date(2026, 9, 25))     # after day 20: not counted
        self.spend("150", datetime.date(2026, 10, 3))
        item = [i for i in compute_insights(self.user, TODAY) if i["type"] == "month_vs_last"][0]
        self.assertEqual((item["params"]["this_month"], item["params"]["last_month"], item["params"]["change_percent"]), (150.0, 100.0, 50.0))

    def test_no_comparison_without_last_month_data(self):
        self.spend("150", datetime.date(2026, 10, 3))
        self.assertEqual(self.types(), [])

    def test_other_users_data_never_shows(self):
        self.spend("100", datetime.date(2026, 9, 5), owner=self.other)
        self.spend("150", datetime.date(2026, 10, 3), owner=self.other)
        self.assertEqual(self.types(), [])
        self.assertEqual(self.types(self.other), ["month_vs_last"])

    def test_unpaid_salary_for_this_month_only(self):
        company = Company.objects.create(owner=self.user, name="Acme")
        SalaryEntry.objects.create(company=company, year=2026, month="October", expected=Decimal("1000"), paid=Decimal("0"))
        SalaryEntry.objects.create(company=company, year=2026, month="September", expected=Decimal("1000"), paid=Decimal("0"))
        found = [i for i in compute_insights(self.user, TODAY) if i["type"] == "salary_unpaid"]
        self.assertEqual([i["params"]["month"] for i in found], ["October"])

    def test_budget_over_limit_is_a_warning_listed_first(self):
        self.spend("100", datetime.date(2026, 9, 5))
        self.spend("150", datetime.date(2026, 10, 3))
        Budget.objects.create(owner=self.user, name="Total", period="monthly", amount=Decimal("100"), amount_base=Decimal("100"))
        items = compute_insights(self.user, TODAY)
        self.assertEqual((items[0]["type"], items[0]["severity"]), ("budget_exceeded", "warn"))

    def test_endpoint_returns_only_my_insights(self):
        self.client.force_login(self.user)
        self.spend("100", datetime.date(2026, 9, 5))
        res = self.client.get("/api/financial-advisor/ai/insights/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("insights", res.json())
