from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from core.models import (
    Bank,
    BalanceEntry,
    Currency,
    CardRenewalFee,
    Expense,
    ExpenseCategory,
)


class CardRenewalFeeBalanceAndMirrorTest(TestCase):
    """Mirrors CreditCardPaymentBalanceAndMirrorTest, applied to
    CardRenewalFee.apply_and_mirror / reverse_and_unmirror."""

    def setUp(self):
        self.bank = Bank.objects.create(name="NBE")
        self.currency_egp, _ = Currency.objects.get_or_create(
            code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"}
        )
        # CardRenewalFee always uses the internal "Bank" payment method,
        # which targets a CASH-type BalanceEntry keyed by bank, per
        # expense_service._get_target_cash_balance_entry.
        self.entry = BalanceEntry.objects.create(
            title="NBE Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank,
            currency=self.currency_egp,
            amount=Decimal("1000.00"),
        )

    def _card_fee_category(self):
        return ExpenseCategory.objects.filter(name="Card Fees").first()

    def test_apply_debits_bank_and_creates_mirror(self):
        fee = CardRenewalFee.objects.create(
            fee_date=date(2026, 8, 31),
            bank=self.bank,
            card_label="Visa Debit 1234",
            amount_egp=Decimal("50.00"),
        )
        fee.apply_and_mirror()

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("950.00"))

        category = self._card_fee_category()
        self.assertIsNotNone(category)
        mirror = Expense.objects.get(source_type="card_renewal_fee", source_id=fee.id)
        self.assertEqual(mirror.amount_egp, Decimal("50.00"))
        self.assertEqual(mirror.category_id, category.id)
        self.assertTrue(mirror.is_readonly_mirror)

    def test_reverse_credits_bank_back_and_deletes_mirror(self):
        fee = CardRenewalFee.objects.create(
            fee_date=date(2026, 8, 31),
            bank=self.bank,
            amount_egp=Decimal("75.00"),
        )
        fee.apply_and_mirror()
        fee.reverse_and_unmirror()

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("1000.00"))
        self.assertFalse(
            Expense.objects.filter(source_type="card_renewal_fee", source_id=fee.id).exists()
        )

    def test_insufficient_balance_blocks_apply(self):
        self.entry.amount = Decimal("10.00")
        self.entry.save()

        fee = CardRenewalFee.objects.create(
            fee_date=date(2026, 8, 31),
            bank=self.bank,
            amount_egp=Decimal("100.00"),
        )
        with self.assertRaises(ValueError):
            fee.apply_and_mirror()

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("10.00"))
        self.assertFalse(
            Expense.objects.filter(source_type="card_renewal_fee", source_id=fee.id).exists()
        )

    def test_editing_amount_reapplies_correct_delta(self):
        fee = CardRenewalFee.objects.create(
            fee_date=date(2026, 8, 31),
            bank=self.bank,
            amount_egp=Decimal("20.00"),
        )
        fee.apply_and_mirror()

        fee.reverse_and_unmirror()
        fee.amount_egp = Decimal("60.00")
        fee.save()
        fee.apply_and_mirror()

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("940.00"))
        mirror = Expense.objects.get(source_type="card_renewal_fee", source_id=fee.id)
        self.assertEqual(mirror.amount_egp, Decimal("60.00"))


class CardRenewalFeeEndpointTest(TestCase):
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
            "/api/card-renewal-fees/",
            data={
                "fee_date": "2026-08-31",
                "bank_id": self.bank.id,
                "card_label": "Visa Debit 1234",
                "amount_egp": 40,
                "notes": "Annual renewal",
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("1960.00"))

    def test_update_via_api_reapplies_delta(self):
        fee = CardRenewalFee.objects.create(
            fee_date=date(2026, 8, 31), bank=self.bank, amount_egp=Decimal("25.00")
        )
        fee.apply_and_mirror()

        res = self.client.put(
            f"/api/card-renewal-fees/{fee.id}/",
            data={"amount_egp": 55},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("1945.00"))

    def test_delete_via_api_reverses_and_removes_mirror(self):
        fee = CardRenewalFee.objects.create(
            fee_date=date(2026, 8, 31), bank=self.bank, amount_egp=Decimal("30.00")
        )
        fee.apply_and_mirror()

        res = self.client.delete(f"/api/card-renewal-fees/{fee.id}/")
        self.assertEqual(res.status_code, 200)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.amount, Decimal("2000.00"))
        self.assertFalse(
            Expense.objects.filter(source_type="card_renewal_fee", source_id=fee.id).exists()
        )

    def test_create_over_balance_returns_400_with_error_key(self):
        self.entry.amount = Decimal("5.00")
        self.entry.save()

        res = self.client.post(
            "/api/card-renewal-fees/",
            data={
                "fee_date": "2026-08-31",
                "bank_id": self.bank.id,
                "amount_egp": 999,
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json().get("error_key"), "insufficient_balance")
        self.assertFalse(CardRenewalFee.objects.exists())
