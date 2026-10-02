import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Currency, Expense, UserProfile
from core.services.budgets import BudgetService, RecurringService

User = get_user_model()


class NonEgpBaseTest(TestCase):
    """A SAR-base user (no EGP currency at all) must never see EGP in
    budgets, recurring postings or imports."""

    def setUp(self):
        self.user = User.objects.create_user(username="sar_owner", password="pass12345")
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.preferred_currency = "SAR"
        profile.save()
        Currency.objects.filter(owner=self.user, code="EGP").delete()
        self.sar, _ = Currency.objects.get_or_create(
            owner=self.user, code="SAR", defaults={"symbol": "SAR", "name": "Saudi Riyal"}
        )
        BalanceEntry.objects.create(
            owner=self.user, title="Cash (SAR)", balance_type=BalanceEntry.BalanceType.CASH,
            bank=None, currency=self.sar, amount=10000,
        )
        self.client.force_login(self.user)

    def test_budget_without_currency_labels_in_user_base(self):
        from core.models import Budget

        b = Budget.objects.create(owner=self.user, name="Overall", period="monthly", amount=500, amount_base=500)
        self.assertEqual(b.to_dict()["currency_code"], "SAR")

    def test_budget_in_sar_has_amount_base_equal_amount(self):
        b = BudgetService.create_budget(
            {"name": "SAR budget", "period": "monthly", "amount": 750, "currency_id": self.sar.id}, self.user
        )
        self.assertEqual(b.amount_base, 750)

    def test_recurring_posts_expense_in_sar(self):
        RecurringService.create_recurring(
            {"name": "Rent", "amount": 100, "currency_id": self.sar.id,
             "frequency": "monthly", "start_date": "2026-01-01", "backfill_missed": True},
            self.user,
        )
        created, skipped = RecurringService.process_due(self.user, as_of=date(2026, 1, 15))
        self.assertEqual(len(created), 1)
        self.assertEqual(skipped, [])
        self.assertEqual(Expense.objects.get(owner=self.user).currency.code, "SAR")

    def test_import_in_sar_creates_sar_expense(self):
        res = self.client.post(
            "/api/import/confirm/",
            data=json.dumps({
                "rows": [{"Date": "2026-02-01", "Amount": "40", "Description": "Fuel"}],
                "mapping": {"date": "Date", "amount": "Amount", "description": "Description"},
                "currency_id": self.sar.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(res.json()["created_count"], 1)
        self.assertEqual(Expense.objects.get(owner=self.user).currency.code, "SAR")
        self.assertFalse(Currency.objects.filter(owner=self.user, code="EGP").exists())
