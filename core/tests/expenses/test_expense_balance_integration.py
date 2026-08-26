from core.models import Bank
import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import BalanceEntry, Currency, Expense, ExpenseCategory

User = get_user_model()


class ExpenseBalanceIntegrationTest(TestCase):
    def setUp(self):
        self.currency_egp = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.bank_cib = Bank.objects.create(name="CIB")
        self.bank_qnb = Bank.objects.create(name="QNB")
        self.category = ExpenseCategory.objects.create(name="Utilities", icon="💡", color_hex="#0d6efd")

        self.cash_entry = BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=2000,
        )
        self.cib_entry = BalanceEntry.objects.create(
            title="CIB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank_cib,
            currency=self.currency_egp,
            amount=10000,
        )
        self.qnb_entry = BalanceEntry.objects.create(
            title="QNB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank_qnb,
            currency=self.currency_egp,
            amount=5000,
        )

    def test_create_requires_bank_for_card_or_bank_and_deducts_from_matching_balance(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 300,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Card",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 500,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Cash",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.cash_entry.refresh_from_db()
        self.assertEqual(float(self.cash_entry.amount), 1500.0)

        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-02",
                    "category_id": self.category.id,
                    "amount": 1200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Bank",
                    "bank_id": self.bank_cib.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.cib_entry.refresh_from_db()
        self.assertEqual(float(self.cib_entry.amount), 8800.0)

    def test_edit_and_delete_restore_and_apply_correct_balance(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 1200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Bank",
                    "bank_id": self.bank_cib.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        expense_id = response.json()["id"]

        response = self.client.put(
            f"/api/expenses/{expense_id}/",
            data=json.dumps(
                {
                    "amount": 300,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.cib_entry.refresh_from_db()
        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.cib_entry.amount), 10000.0)
        self.assertEqual(float(self.qnb_entry.amount), 4700.0)

        response = self.client.delete(f"/api/expenses/{expense_id}/")
        self.assertEqual(response.status_code, 200)
        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.qnb_entry.amount), 5000.0)
        self.assertFalse(Expense.objects.filter(pk=expense_id).exists())

    def test_create_expense_rejected_when_balance_would_be_negative(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 2500,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Cash",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("error"), "insufficient_balance")
        self.cash_entry.refresh_from_db()
        self.assertEqual(float(self.cash_entry.amount), 2000.0)
        self.assertEqual(Expense.objects.count(), 0)

    def test_edit_expense_rejected_when_new_deduction_would_be_negative(self):
        create_response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        expense_id = create_response.json()["id"]

        edit_response = self.client.put(
            f"/api/expenses/{expense_id}/",
            data=json.dumps(
                {
                    "amount": 6000,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(edit_response.status_code, 400)
        self.assertEqual(edit_response.json().get("error"), "insufficient_balance")

        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.qnb_entry.amount), 4800.0)

        exp = Expense.objects.get(pk=expense_id)
        self.assertEqual(float(exp.amount), 200.0)
        self.assertEqual(exp.bank_id, self.bank_qnb.id)
