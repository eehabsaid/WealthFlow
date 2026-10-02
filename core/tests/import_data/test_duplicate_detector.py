from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Currency, Expense
from core.services.import_data.duplicate_detector import find_duplicates

User = get_user_model()


class DuplicateDetectorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dup_owner", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")

    def test_exact_match_flagged_as_duplicate(self):
        Expense.objects.create(
            owner=self.user, date=date(2026, 3, 1), year=2026, month=3,
            amount=100, amount_base=100, currency=self.egp, description="Groceries",
        )
        rows = [{"date": date(2026, 3, 1), "amount": 100, "description": "Groceries"}]
        self.assertEqual(find_duplicates(self.user, rows), {0})

    def test_different_amount_not_a_duplicate(self):
        Expense.objects.create(
            owner=self.user, date=date(2026, 3, 1), year=2026, month=3,
            amount=100, amount_base=100, currency=self.egp, description="Groceries",
        )
        rows = [{"date": date(2026, 3, 1), "amount": 150, "description": "Groceries"}]
        self.assertEqual(find_duplicates(self.user, rows), set())

    def test_different_description_not_a_duplicate(self):
        Expense.objects.create(
            owner=self.user, date=date(2026, 3, 1), year=2026, month=3,
            amount=100, amount_base=100, currency=self.egp, description="Groceries",
        )
        rows = [{"date": date(2026, 3, 1), "amount": 100, "description": "Something else"}]
        self.assertEqual(find_duplicates(self.user, rows), set())

    def test_another_owners_expense_is_not_a_match(self):
        other = User.objects.create_user(username="other", password="pass12345")
        Expense.objects.create(
            owner=other, date=date(2026, 3, 1), year=2026, month=3,
            amount=100, amount_base=100, currency=self.egp, description="Groceries",
        )
        rows = [{"date": date(2026, 3, 1), "amount": 100, "description": "Groceries"}]
        self.assertEqual(find_duplicates(self.user, rows), set())

    def test_rows_without_date_are_skipped_not_flagged(self):
        rows = [{"date": None, "amount": 100, "description": "Groceries"}]
        self.assertEqual(find_duplicates(self.user, rows), set())
