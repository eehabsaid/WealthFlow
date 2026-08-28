from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Bank, BalanceEntry, BankCertificate, Currency
from core.services.certificate.certificate_balance_deduction_service import (
    CertificateBalanceMappingError,
    CertificateInsufficientBalanceError,
)

User = get_user_model()


class CertificateBalanceDeductionServiceTest(TestCase):
    def setUp(self):
        self.egp = Currency.objects.create(code="EGP", symbol="ج.م", name="Egyptian Pound")
        self.usd = Currency.objects.create(code="USD", symbol="$", name="US Dollar")
        self.enbd = Bank.objects.create(name="ENBD")
        self.qnb = Bank.objects.create(name="QNB")

        self.cash_egp = BalanceEntry.objects.create(
            title="ENBD Bank Account Balance",
            balance_type="Cash",  # mixed case, must still match
            bank=self.enbd,
            currency=self.egp,
            amount=Decimal("100000.00"),
        )
        self.cash_usd = BalanceEntry.objects.create(
            title="Home Balance",
            balance_type="cash",
            bank=None,
            currency=self.usd,
            amount=Decimal("25000.00"),
        )

    def _make_certificate(self, bank, currency, amount, status="Active"):
        return BankCertificate.objects.create(
            bank=bank,
            currency=currency,
            issue_date="2026-01-01",
            expiry_date="2026-07-01",
            amount=amount,
            interest_value=10,
            status=status,
        )

    def test_create_deducts_principal_from_matching_cash_entry(self):
        self._make_certificate(self.enbd, self.egp, Decimal("20000.00"))
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("80000.00"))

    def test_create_blocked_when_no_matching_cash_entry(self):
        with self.assertRaises(CertificateBalanceMappingError):
            self._make_certificate(self.qnb, self.egp, Decimal("1000.00"))
        # No certificate should have been persisted.
        self.assertEqual(BankCertificate.objects.count(), 0)
        # And no balance should have moved.
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("100000.00"))

    def test_status_only_change_does_not_move_balance(self):
        cert = self._make_certificate(self.enbd, self.egp, Decimal("20000.00"))
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("80000.00"))

        cert.status = "Closed"
        cert.save()

        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("80000.00"))

    def test_amount_edit_applies_only_the_delta(self):
        cert = self._make_certificate(self.enbd, self.egp, Decimal("20000.00"))
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("80000.00"))

        cert.amount = Decimal("25000.00")
        cert.save()

        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("75000.00"))

    def test_currency_change_reverses_old_and_deducts_new(self):
        cert = self._make_certificate(self.enbd, self.egp, Decimal("20000.00"))
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("80000.00"))

        cert.bank = None
        cert.currency = self.usd
        cert.save()

        self.cash_egp.refresh_from_db()
        self.cash_usd.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("100000.00"))
        self.assertEqual(self.cash_usd.amount, Decimal("5000.00"))  # 25000 - 20000

    def test_update_blocked_if_new_mapping_missing(self):
        cert = self._make_certificate(self.enbd, self.egp, Decimal("20000.00"))
        cert.bank = self.qnb
        with self.assertRaises(CertificateBalanceMappingError):
            cert.save()
        # Old deduction must remain untouched since the update was blocked.
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("80000.00"))

    def test_delete_reverses_the_deduction(self):
        cert = self._make_certificate(self.enbd, self.egp, Decimal("20000.00"))
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("80000.00"))

        cert.delete()

        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("100000.00"))

    def test_create_blocked_when_amount_exceeds_balance(self):
        with self.assertRaises(CertificateInsufficientBalanceError):
            self._make_certificate(self.enbd, self.egp, Decimal("150000.00"))
        self.assertEqual(BankCertificate.objects.count(), 0)
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("100000.00"))

    def test_create_allowed_when_amount_exactly_matches_balance(self):
        self._make_certificate(self.enbd, self.egp, Decimal("100000.00"))
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("0.00"))

    def test_amount_increase_checks_only_net_delta(self):
        # Balance is 100000, cert takes 80000, leaving 20000 available.
        cert = self._make_certificate(self.enbd, self.egp, Decimal("80000.00"))
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("20000.00"))

        # Bumping to 100000 only needs the extra 20000 covered (net delta),
        # not the full new amount re-checked against the already-reduced
        # balance - this must succeed.
        cert.amount = Decimal("100000.00")
        cert.save()
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("0.00"))

    def test_amount_increase_blocked_when_net_delta_exceeds_available(self):
        cert = self._make_certificate(self.enbd, self.egp, Decimal("80000.00"))
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("20000.00"))

        cert.amount = Decimal("100000.01")
        with self.assertRaises(CertificateInsufficientBalanceError):
            cert.save()
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("20000.00"))

    def test_currency_change_blocked_when_new_entry_lacks_funds(self):
        cert = self._make_certificate(self.enbd, self.egp, Decimal("20000.00"))
        cert.bank = None
        cert.currency = self.usd
        cert.amount = Decimal("30000.00")  # cash_usd only has 25000
        with self.assertRaises(CertificateInsufficientBalanceError):
            cert.save()
        # Old EGP deduction must remain untouched since the update was blocked.
        self.cash_egp.refresh_from_db()
        self.assertEqual(self.cash_egp.amount, Decimal("80000.00"))


class CertificateBalanceDeductionApiErrorTest(TestCase):
    """Confirms the view layer converts the two balance-deduction
    exceptions into clean JSON 400 responses (error_code + error) instead
    of an unhandled 500, so the frontend never receives a raw traceback
    body to display."""

    def setUp(self):
        self.egp = Currency.objects.create(code="EGP", symbol="ج.م", name="Egyptian Pound")
        self.enbd = Bank.objects.create(name="ENBD")
        self.qnb = Bank.objects.create(name="QNB")
        self.cash_egp = BalanceEntry.objects.create(
            title="ENBD Bank Account Balance",
            balance_type="cash",
            bank=self.enbd,
            currency=self.egp,
            amount=Decimal("10000.00"),
        )

    def test_post_returns_json_400_when_mapping_missing(self):
        response = self.client.post(
            "/api/bank-certificates/",
            data=json.dumps({
                "bank_id": self.qnb.id,
                "currency_id": self.egp.id,
                "issue_date": "2026-01-01",
                "expiry_date": "2026-07-01",
                "amount": 1000,
                "status": "Active",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error_code"], "certificate_balance_mapping_missing")
        self.assertIn("error", payload)
        self.assertEqual(BankCertificate.objects.count(), 0)

    def test_post_returns_json_400_when_insufficient_balance(self):
        response = self.client.post(
            "/api/bank-certificates/",
            data=json.dumps({
                "bank_id": self.enbd.id,
                "currency_id": self.egp.id,
                "issue_date": "2026-01-01",
                "expiry_date": "2026-07-01",
                "amount": 50000,
                "status": "Active",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error_code"], "certificate_insufficient_balance")
        self.assertEqual(BankCertificate.objects.count(), 0)

    def test_put_returns_json_400_when_insufficient_balance(self):
        cert = BankCertificate.objects.create(
            bank=self.enbd,
            currency=self.egp,
            issue_date="2026-01-01",
            expiry_date="2026-07-01",
            amount=Decimal("5000.00"),
            status="Active",
        )
        response = self.client.put(
            f"/api/bank-certificates/{cert.id}/",
            data=json.dumps({"amount": 50000}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error_code"], "certificate_insufficient_balance")
        cert.refresh_from_db()
        self.assertEqual(cert.amount, Decimal("5000.00"))
