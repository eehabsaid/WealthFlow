from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Budget, Currency, Expense, ExpenseCategory, RecurringTransaction
from core.services.budgets.alert_service import AlertService

User = get_user_model()


class AlertServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alert_owner", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        self.category = ExpenseCategory.objects.create(owner=self.user, name="QA Food", icon="🍔")

    def test_budget_threshold_alert(self):
        Budget.objects.create(
            owner=self.user, name="Food", category=self.category, period="monthly",
            amount=1000, currency=self.egp, amount_base=1000, alert_threshold_percent=80, is_active=True,
        )
        today = date.today()
        Expense.objects.create(
            owner=self.user, date=today, year=today.year, month=today.month,
            category=self.category, amount=850, amount_base=850, currency=self.egp,
        )
        alerts = AlertService.get_alerts(self.user, ref_date=today)
        types = [a["type"] for a in alerts]
        self.assertIn("budget_threshold", types)

    def test_budget_exceeded_alert(self):
        Budget.objects.create(
            owner=self.user, name="Food", category=self.category, period="monthly",
            amount=1000, currency=self.egp, amount_base=1000, alert_threshold_percent=80, is_active=True,
        )
        today = date.today()
        Expense.objects.create(
            owner=self.user, date=today, year=today.year, month=today.month,
            category=self.category, amount=1200, amount_base=1200, currency=self.egp,
        )
        alerts = AlertService.get_alerts(self.user, ref_date=today)
        types = [a["type"] for a in alerts]
        self.assertIn("budget_exceeded", types)
        self.assertNotIn("budget_threshold", types)

    def test_no_alert_below_threshold(self):
        Budget.objects.create(
            owner=self.user, name="Food", category=self.category, period="monthly",
            amount=1000, currency=self.egp, amount_base=1000, alert_threshold_percent=80, is_active=True,
        )
        today = date.today()
        Expense.objects.create(
            owner=self.user, date=today, year=today.year, month=today.month,
            category=self.category, amount=100, amount_base=100, currency=self.egp,
        )
        alerts = AlertService.get_alerts(self.user, ref_date=today)
        self.assertEqual(alerts, [])

    def test_recurring_due_soon_and_overdue_alerts(self):
        ref = date(2026, 6, 15)
        RecurringTransaction.objects.create(
            owner=self.user, name="Netflix", amount=200, currency=self.egp,
            payment_method="Cash", frequency="monthly", interval=1,
            start_date=date(2026, 6, 1), next_run_date=date(2026, 6, 17), is_active=True,
        )
        RecurringTransaction.objects.create(
            owner=self.user, name="Rent", amount=5000, currency=self.egp,
            payment_method="Cash", frequency="monthly", interval=1,
            start_date=date(2026, 6, 1), next_run_date=date(2026, 6, 1), is_active=True,
        )
        alerts = AlertService.get_alerts(self.user, ref_date=ref)
        types = [a["type"] for a in alerts]
        self.assertIn("recurring_due_soon", types)
        self.assertIn("recurring_overdue", types)

    def test_inactive_budget_and_recurring_produce_no_alerts(self):
        Budget.objects.create(
            owner=self.user, name="Food", category=self.category, period="monthly",
            amount=100, currency=self.egp, amount_base=100, alert_threshold_percent=10, is_active=False,
        )
        RecurringTransaction.objects.create(
            owner=self.user, name="Old", amount=50, currency=self.egp,
            payment_method="Cash", frequency="monthly", interval=1,
            start_date=date(2026, 1, 1), next_run_date=date(2026, 1, 1), is_active=False,
        )
        alerts = AlertService.get_alerts(self.user, ref_date=date(2026, 6, 1))
        self.assertEqual(alerts, [])
