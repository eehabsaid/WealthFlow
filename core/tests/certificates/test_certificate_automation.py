from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    BalanceEntry,
    Bank,
    BankCertificate,
    CertificateStatus,
    Currency,
)
from core.services.certificate.certificate_automation_service import CertificateAutomationService

User = get_user_model()


class CertificateAutomationServiceTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="QNB")
        # A matching cash balance entry is required for certificate saves to
        # succeed now that principal deduction is enforced (see
        # certificate_balance_deduction_service.py).
        BalanceEntry.objects.create(
            title="QNB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank,
            currency=self.currency,
            amount=100000,
        )

    def test_close_matured_certificates_uses_closed_lookup_and_skips_non_active(self):
        CertificateStatus.objects.create(name="cLoSeD", is_terminal=True, order=1)

        active_matured = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 7, 1),
            amount=1000,
            interest_value=10,
            status="Active",
        )
        already_closed = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 7, 1),
            amount=1000,
            interest_value=10,
            status="CLOSED",
        )
        inactive_matured = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 7, 1),
            amount=1000,
            interest_value=10,
            status="Renewed",
        )

        result = CertificateAutomationService().close_matured_certificates(today=date(2026, 7, 4))

        active_matured.refresh_from_db()
        already_closed.refresh_from_db()
        inactive_matured.refresh_from_db()

        self.assertEqual(result.closed_certificates, 1)
        self.assertEqual(active_matured.status, "cLoSeD")
        self.assertEqual(already_closed.status, "CLOSED")
        self.assertEqual(inactive_matured.status, "Renewed")
