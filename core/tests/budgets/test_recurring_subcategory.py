"""Recurring transactions keep a subcategory that always belongs to the chosen category (both come from Expense Categories)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Currency, Expense, ExpenseCategory, ExpenseSubcategory
from core.services.budgets.recurring_service import RecurringService

User = get_user_model()


class RecurringSubcategoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rec_sub", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        BalanceEntry.objects.create(owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH, bank=None, currency=self.egp, amount=10000)
        self.food = ExpenseCategory.objects.create(owner=self.user, name="Food")
        self.rent = ExpenseCategory.objects.create(owner=self.user, name="Rent")
        self.coffee = ExpenseSubcategory.objects.create(category=self.food, name="Coffee")

    def make(self, **over):
        data = {"name": "Coffee club", "amount": 30, "currency_id": self.egp.id, "frequency": "monthly", "start_date": "2026-01-05", "backfill_missed": True,
                "category_id": self.food.id, "subcategory_id": self.coffee.id, **over}
        return RecurringService.create_recurring(data, self.user)

    def test_a_matching_subcategory_is_stored_and_returned(self):
        rec = self.make()
        self.assertEqual(rec.subcategory_id, self.coffee.id)
        self.assertEqual(rec.to_dict()["subcategory_id"], self.coffee.id)

    def test_a_subcategory_of_another_category_or_without_a_category_is_dropped(self):
        self.assertIsNone(self.make(category_id=self.rent.id).subcategory_id)
        self.assertIsNone(self.make(category_id=None).subcategory_id)

    def test_changing_the_category_drops_the_old_subcategory(self):
        rec = self.make()
        RecurringService.update_recurring(rec, {"category_id": self.rent.id})
        rec.refresh_from_db()
        self.assertIsNone(rec.subcategory_id)

    def test_the_posted_expense_carries_the_subcategory(self):
        self.make()
        RecurringService.process_due(self.user, as_of=date(2026, 1, 10))
        self.assertEqual(Expense.objects.get(owner=self.user).subcategory_id, self.coffee.id)
