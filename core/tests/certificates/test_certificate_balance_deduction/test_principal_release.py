from datetime import date
from decimal import Decimal

from django.test import TestCase

from core.models import Bank, BalanceEntry, BankCertificate, Currency
from core.services.certificate.certificate_automation_service import (
    CertificateAutomationService,
)
from core.services.certificate.certificate_balance_deduction_service import (
    CertificateInsufficientBalanceError,
)


class CertificatePrincipalReleaseTest(TestCase):
    def setUp(self):
        self.egp = Currency.objects.create(code="EGP", symbol="ج.م", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="ENBD")
        self.cash = BalanceEntry.objects.create(
            title="ENBD Cash",
            balance_type="cash",
            bank=self.bank,
            currency=self.egp,
            amount=Decimal("100000.00"),
        )

    def _cert(self, amount="20000.00", status="Active"):
        return BankCertificate.objects.create(
            bank=self.bank,
            currency=self.egp,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 7, 1),
            amount=Decimal(amount),
            interest_value=10,
            status=status,
        )

    def _cash(self):
        self.cash.refresh_from_db()
        return self.cash.amount

    def test_manual_close_returns_principal(self):
        cert = self._cert()
        self.assertEqual(self._cash(), Decimal("80000.00"))
        cert.status = "Closed"
        cert.save()
        self.assertEqual(self._cash(), Decimal("100000.00"))

    def test_close_is_case_insensitive_and_idempotent(self):
        cert = self._cert()
        cert.status = "CLOSED"
        cert.save()
        cert.save()
        self.assertEqual(self._cash(), Decimal("100000.00"))

    def test_auto_maturity_close_returns_principal(self):
        self._cert()
        result = CertificateAutomationService().close_matured_certificates(
            today=date(2026, 7, 4)
        )
        self.assertEqual(result.closed_certificates, 1)
        self.assertEqual(self._cash(), Decimal("100000.00"))
        # A second run must not release it twice.
        CertificateAutomationService().close_matured_certificates(today=date(2026, 7, 5))
        self.assertEqual(self._cash(), Decimal("100000.00"))

    def test_reopen_deducts_principal_again(self):
        cert = self._cert()
        cert.status = "Closed"
        cert.save()
        cert.status = "Active"
        cert.save()
        self.assertEqual(self._cash(), Decimal("80000.00"))

    def test_reopen_blocked_when_cash_no_longer_covers_principal(self):
        cert = self._cert()
        cert.status = "Closed"
        cert.save()
        self.cash.amount = Decimal("1000.00")
        self.cash.save(update_fields=["amount"])
        cert.status = "Active"
        with self.assertRaises(CertificateInsufficientBalanceError):
            cert.save()
        self.assertEqual(self._cash(), Decimal("1000.00"))

    def test_amount_edit_on_closed_certificate_moves_nothing(self):
        cert = self._cert()
        cert.status = "Closed"
        cert.save()
        cert.amount = Decimal("50000.00")
        cert.save()
        self.assertEqual(self._cash(), Decimal("100000.00"))

    def test_delete_closed_certificate_does_not_double_return(self):
        cert = self._cert()
        cert.status = "Closed"
        cert.save()
        cert.delete()
        self.assertEqual(self._cash(), Decimal("100000.00"))

    def test_delete_active_certificate_still_returns_principal(self):
        cert = self._cert()
        cert.delete()
        self.assertEqual(self._cash(), Decimal("100000.00"))

    def test_create_as_closed_holds_nothing(self):
        self._cert(status="Closed")
        self.assertEqual(self._cash(), Decimal("100000.00"))
