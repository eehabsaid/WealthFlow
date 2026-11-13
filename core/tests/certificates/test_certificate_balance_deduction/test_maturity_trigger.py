from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Bank, BalanceEntry, BankCertificate, Currency

User = get_user_model()


class CertificateMaturityTriggerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mat_trigger", password="pass12345")
        self.client.force_login(self.user)
        self.egp = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="QNB", owner=self.user)
        self.cash = BalanceEntry.objects.create(
            owner=self.user, title="QNB Cash", balance_type="cash",
            bank=self.bank, currency=self.egp, amount=Decimal("100000.00"),
        )

    def _cert(self, expiry, status="Active"):
        return BankCertificate.objects.create(
            owner=self.user, bank=self.bank, currency=self.egp,
            issue_date=date(2026, 1, 1), expiry_date=expiry,
            amount=Decimal("20000.00"), interest_value=10, status=status,
        )

    def _cash(self):
        self.cash.refresh_from_db()
        return self.cash.amount

    def test_balance_page_closes_matured_certificate_and_returns_principal(self):
        cert = self._cert(date(2026, 3, 1))
        self.assertEqual(self._cash(), Decimal("80000.00"))
        self.assertEqual(self.client.get("/api/balance/").status_code, 200)
        cert.refresh_from_db()
        self.assertEqual(cert.status.lower(), "closed")
        self.assertEqual(self._cash(), Decimal("100000.00"))

    def test_balance_page_does_not_touch_unmatured_certificate(self):
        cert = self._cert(date(2999, 1, 1))
        self.client.get("/api/balance/")
        cert.refresh_from_db()
        self.assertEqual(cert.status, "Active")
        self.assertEqual(self._cash(), Decimal("80000.00"))

    def test_repeated_page_loads_return_principal_once(self):
        self._cert(date(2026, 3, 1))
        for _ in range(3):
            self.client.get("/api/balance/")
        self.assertEqual(self._cash(), Decimal("100000.00"))

    def test_certificate_that_cannot_be_closed_does_not_block_others(self):
        orphan = self._cert(date(2026, 3, 1))
        good = self._cert(date(2026, 3, 1))
        # Remove the cash entry only for the orphan by moving it to another bank.
        other = Bank.objects.create(name="CIB", owner=self.user)
        BankCertificate.objects.filter(pk=orphan.pk).update(bank=other)
        self.assertEqual(self.client.get("/api/balance/").status_code, 200)
        orphan.refresh_from_db()
        good.refresh_from_db()
        self.assertEqual(orphan.status, "Active")
        self.assertEqual(good.status.lower(), "closed")

    def test_maturity_close_failure_never_breaks_the_page(self):
        self._cert(date(2026, 3, 1))
        with patch(
            "core.services.certificate.certificate_automation_service."
            "CertificateAutomationService.close_matured_certificates",
            side_effect=RuntimeError("boom"),
        ):
            self.assertEqual(self.client.get("/api/balance/").status_code, 200)
