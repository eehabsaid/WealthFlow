import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Budget, Currency, Expense, ExpenseCategory, RecurringTransaction

User = get_user_model()


class BudgetViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="budget_view_owner", password="pass12345")
        self.client.force_login(self.user)
        self.egp = Currency.objects.create(code="EGP", symbol="EGP", name="Egyptian Pound")
        self.category = ExpenseCategory.objects.create(owner=self.user, name="QA Food", icon="🍔")
        BalanceEntry.objects.create(
            owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH,
            bank=None, currency=self.egp, amount=10000,
        )

    def test_requires_authentication(self):
        self.client.logout()
        res = self.client.get("/api/budgets/")
        self.assertNotEqual(res.status_code, 200)

    def test_create_list_update_delete_budget(self):
        res = self.client.post(
            "/api/budgets/", data=json.dumps({
                "name": "Food budget", "category_id": self.category.id, "period": "monthly",
                "amount": 1000, "currency_id": self.egp.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        budget_id = res.json()["id"]

        res = self.client.get("/api/budgets/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["budgets"]), 1)

        res = self.client.put(
            f"/api/budgets/{budget_id}/", data=json.dumps({"amount": 1500}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["amount"], 1500.0)

        res = self.client.delete(f"/api/budgets/{budget_id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Budget.objects.count(), 0)

    def test_budget_belongs_to_owner_only(self):
        other = User.objects.create_user(username="other_owner", password="pass12345")
        budget = Budget.objects.create(
            owner=other, name="Not yours", period="monthly", amount=100,
            currency=self.egp, amount_base=100,
        )
        res = self.client.put(
            f"/api/budgets/{budget.id}/", data=json.dumps({"amount": 999}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_create_and_process_due_recurring_transaction(self):
        res = self.client.post(
            "/api/recurring-transactions/", data=json.dumps({
                "name": "Netflix", "amount": 200, "currency_id": self.egp.id,
                "frequency": "monthly", "start_date": "2026-01-01", "backfill_missed": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(RecurringTransaction.objects.count(), 1)

        res = self.client.get("/api/recurring-transactions/due-preview/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()["due"]), 1)
        self.assertEqual(Expense.objects.filter(owner=self.user).count(), 0)  # preview writes nothing

        res = self.client.post("/api/recurring-transactions/process-due/")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertGreaterEqual(len(payload["created"]), 1)

    def test_alerts_endpoint(self):
        res = self.client.get("/api/budgets/alerts/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("alerts", res.json())
