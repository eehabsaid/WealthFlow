from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from core.models import (
    Bank,
    BalanceEntry,
    Currency,
    CreditCardPayment,
    Expense,
    ExpenseCategory,
)


class CreditCardPaymentBalanceAndMirrorTest(TestCase):
    """Mirrors the AssetExpenseMirrorCoreTest / *ReversalsTest conventions
    used for Fixed Assets, applied to CreditCardPayment.apply_and_mirror /
    reverse_and_unmirror."""

    def setUp(self):
        self.bank = Bank.objects.create(name="NBE")
        self.currency_egp, _ = Currency.objects.get_or_create(
            code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"}
        )
        # Card/Bank Transfer payment methods target a CASH-type BalanceEntry
        # keyed by bank, per expense_service._get_target_cash_balance_entry.
        self.entry = BalanceEntry.objects.create(
            title="NBE Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank,
            currency=self.currency_egp,
            amount=Decimal("1000.00"),
        )

    def _credit_card_category(self):
        return ExpenseCategory.objects.filter(name="Credit Card").first()

    def test_apply_debits_bank_and_creates_mirror(self):
        payment = CreditCardPayment.objects.create(
            payment_date=date(2026, 8, 31),
            bank=self.bank,
            payment_method="Card",
            card_label="Visa 1234",
            amount_egp=Decimal("250.00"),
        )
        payment.apply_and_mirror()

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("750.00"))

        category = self._credit_card_category()
        self.assertIsNotNone(category)
        mirror = Expense.objects.get(source_type="credit_card_payment", source_id=payment.id)
        self.assertEqual(mirror.amount_egp, Decimal("250.00"))
        self.assertEqual(mirror.category_id, category.id)
        self.assertTrue(mirror.is_readonly_mirror)

    def test_reverse_credits_bank_back_and_deletes_mirror(self):
        payment = CreditCardPayment.objects.create(
            payment_date=date(2026, 8, 31),
            bank=self.bank,
            payment_method="Bank Transfer",
            amount_egp=Decimal("400.00"),
        )
        payment.apply_and_mirror()
        payment.reverse_and_unmirror()

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("1000.00"))
        self.assertFalse(
            Expense.objects.filter(source_type="credit_card_payment", source_id=payment.id).exists()
        )

    def test_insufficient_balance_blocks_apply(self):
        self.entry.amount = Decimal("50.00")
        self.entry.save()

        payment = CreditCardPayment.objects.create(
            payment_date=date(2026, 8, 31),
            bank=self.bank,
            payment_method="Card",
            amount_egp=Decimal("500.00"),
        )
        with self.assertRaises(ValueError):
            payment.apply_and_mirror()

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("50.00"))
        self.assertFalse(
            Expense.objects.filter(source_type="credit_card_payment", source_id=payment.id).exists()
        )

    def test_editing_amount_reapplies_correct_delta(self):
        payment = CreditCardPayment.objects.create(
            payment_date=date(2026, 8, 31),
            bank=self.bank,
            payment_method="Card",
            amount_egp=Decimal("100.00"),
        )
        payment.apply_and_mirror()

        payment.reverse_and_unmirror()
        payment.amount_egp = Decimal("300.00")
        payment.save()
        payment.apply_and_mirror()

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("700.00"))
        mirror = Expense.objects.get(source_type="credit_card_payment", source_id=payment.id)
        self.assertEqual(mirror.amount_egp, Decimal("300.00"))


class CreditCardPaymentEndpointTest(TestCase):
    """Real API-verified create/edit/delete, matching crud_verifier.py's
    approach for the other Balance tabs."""

    def setUp(self):
        self.client = Client()
        self.bank = Bank.objects.create(name="CIB")
        self.currency_egp, _ = Currency.objects.get_or_create(
            code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"}
        )
        self.entry = BalanceEntry.objects.create(
            title="CIB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank,
            currency=self.currency_egp,
            amount=Decimal("2000.00"),
        )

    def test_create_via_api_debits_and_mirrors(self):
        res = self.client.post(
            "/api/credit-card-payments/",
            data={
                "payment_date": "2026-08-31",
                "bank_id": self.bank.id,
                "payment_method": "Card",
                "card_label": "Visa 1234",
                "amount_egp": 150,
                "notes": "Groceries",
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("1850.00"))

    def test_update_via_api_reapplies_delta(self):
        payment = CreditCardPayment.objects.create(
            payment_date=date(2026, 8, 31), bank=self.bank, payment_method="Card", amount_egp=Decimal("100.00")
        )
        payment.apply_and_mirror()

        res = self.client.put(
            f"/api/credit-card-payments/{payment.id}/",
            data={"amount_egp": 300},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("1700.00"))

    def test_delete_via_api_reverses_and_removes_mirror(self):
        payment = CreditCardPayment.objects.create(
            payment_date=date(2026, 8, 31), bank=self.bank, payment_method="Card", amount_egp=Decimal("200.00")
        )
        payment.apply_and_mirror()

        res = self.client.delete(f"/api/credit-card-payments/{payment.id}/")
        self.assertEqual(res.status_code, 200)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("2000.00"))
        self.assertFalse(
            Expense.objects.filter(source_type="credit_card_payment", source_id=payment.id).exists()
        )

    def test_create_over_balance_returns_400_with_error_key(self):
        self.entry.amount = Decimal("10.00")
        self.entry.save()

        res = self.client.post(
            "/api/credit-card-payments/",
            data={
                "payment_date": "2026-08-31",
                "bank_id": self.bank.id,
                "payment_method": "Card",
                "amount_egp": 999,
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json().get("error_key"), "insufficient_balance")
        self.assertFalse(CreditCardPayment.objects.exists())
