from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Budget, Currency, Expense, ExpenseCategory
from core.services.budgets.budget_service import BudgetService

User = get_user_model()


class BudgetServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budget_owner", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        self.category = ExpenseCategory.objects.create(owner=self.user, name="QA Groceries", icon="🛒")

    def test_period_range_monthly(self):
        start, end = BudgetService.period_range("monthly", date(2026, 2, 10))
        self.assertEqual(start, date(2026, 2, 1))
        self.assertEqual(end, date(2026, 2, 28))

    def test_period_range_weekly(self):
        start, end = BudgetService.period_range("weekly", date(2026, 9, 30))  # a Wednesday
        self.assertEqual(start.weekday(), 0)
        self.assertEqual((end - start).days, 6)

    def test_period_range_yearly(self):
        start, end = BudgetService.period_range("yearly", date(2026, 5, 1))
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 12, 31))

    def test_create_budget_computes_amount_base_same_currency(self):
        budget = BudgetService.create_budget(
            {"name": "Food budget", "category_id": self.category.id, "period": "monthly",
             "amount": 2000, "currency_id": self.egp.id},
            self.user,
        )
        self.assertEqual(budget.amount_base, 2000)

    def test_compute_spent_scoped_to_category_and_period(self):
        budget = Budget.objects.create(
            owner=self.user, name="Food", category=self.category, period="monthly",
            amount=1000, currency=self.egp, amount_base=1000,
        )
        Expense.objects.create(
            owner=self.user, date=date(2026, 2, 15), year=2026, month=2,
            category=self.category, amount=300, amount_base=300, currency=self.egp,
        )
        # Different category: must not count.
        other_cat = ExpenseCategory.objects.create(owner=self.user, name="QA Transport", icon="🚗")
        Expense.objects.create(
            owner=self.user, date=date(2026, 2, 16), year=2026, month=2,
            category=other_cat, amount=500, amount_base=500, currency=self.egp,
        )
        # Different month: must not count.
        Expense.objects.create(
            owner=self.user, date=date(2026, 1, 20), year=2026, month=1,
            category=self.category, amount=999, amount_base=999, currency=self.egp,
        )
        spent = BudgetService.compute_spent(budget, ref_date=date(2026, 2, 20))
        self.assertEqual(spent, 300)

    def test_list_with_spend_includes_percent_used(self):
        Budget.objects.create(
            owner=self.user, name="Food", category=self.category, period="monthly",
            amount=1000, currency=self.egp, amount_base=1000, alert_threshold_percent=80,
        )
        Expense.objects.create(
            owner=self.user, date=date.today(), year=date.today().year, month=date.today().month,
            category=self.category, amount=500, amount_base=500, currency=self.egp,
        )
        result = BudgetService.list_with_spend(self.user)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["spent_base"], 500.0)
        self.assertEqual(result[0]["percent_used"], 50.0)
