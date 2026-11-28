from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Budget, Currency, Expense, ExpenseCategory, RecurringTransaction
from core.services.budgets import BudgetKpiService

User = get_user_model()


class BudgetKpiServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="kpi_owner", password="pass12345")
        self.other = User.objects.create_user(username="kpi_other", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        self.cat = ExpenseCategory.objects.create(owner=self.user, name="QA", icon="x")
        self.today = date.today()

    def _rec(self, owner, days, active=True):
        return RecurringTransaction.objects.create(
            owner=owner, name=f"r{days}", amount=10, currency=self.egp, frequency="monthly",
            start_date=self.today, next_run_date=self.today + timedelta(days=days), is_active=active,
        )

    def test_counts_active_over_due_soon_overdue(self):
        b = Budget.objects.create(
            owner=self.user, name="B", category=self.cat, period="monthly", amount=100,
            currency=self.egp, amount_base=100, alert_threshold_percent=80, is_active=True,
        )
        Budget.objects.create(
            owner=self.user, name="Off", category=self.cat, period="monthly", amount=100,
            currency=self.egp, amount_base=100, alert_threshold_percent=80, is_active=False,
        )
        Expense.objects.create(
            owner=self.user, date=self.today, year=self.today.year, month=self.today.month,
            category=self.cat, amount=150, amount_base=150, currency=self.egp,
        )
        self._rec(self.user, -1)
        self._rec(self.user, 0)
        self._rec(self.user, 7)
        self._rec(self.user, 8)
        self._rec(self.user, -5, active=False)
        self._rec(self.other, -1)
        k = BudgetKpiService.get_kpis(self.user, ref_date=self.today)
        self.assertEqual(k, {"active": 1, "over": 1, "due_soon": 2, "overdue": 1})
        self.assertTrue(b.is_active)

    def test_due_status_values(self):
        self.assertEqual(self._rec(self.user, -1).due_status(), "overdue")
        self.assertEqual(self._rec(self.user, 3).due_status(), "due_soon")
        self.assertEqual(self._rec(self.user, 30).due_status(), "")
        self.assertEqual(self._rec(self.user, 1, active=False).due_status(), "inactive")

    def test_alerts_endpoint_returns_kpis_and_due_status(self):
        self.client.force_login(self.user)
        self._rec(self.user, -2)
        data = self.client.get("/api/budgets/alerts/").json()
        self.assertEqual(data["kpis"]["overdue"], 1)
        rec = self.client.get("/api/recurring-transactions/").json()["recurring_transactions"][0]
        self.assertEqual(rec["due_status"], "overdue")
