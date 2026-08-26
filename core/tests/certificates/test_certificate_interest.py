from unittest.mock import patch
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    BalanceEntry,
    Bank,
    BankCertificate,
    BankCertificateInterestHistory,
    Currency,
)
from core.services.certificate.certificate_interest_service import CertificateInterestService

User = get_user_model()


class CertificateInterestSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="QNB")
        self.cash_balance = BalanceEntry.objects.create(
            title="QNB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank,
            currency=self.currency,
            amount=1000,
        )

    def test_service_recovers_missed_periods_and_prevents_duplicates(self):
        certificate = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 15),
            expiry_date=date(2026, 12, 31),
            amount=10000,
            interest_value=100,
            frequency="Monthly",
            status="Active",
            last_interest_posted_date=date(2026, 3, 15),
        )

        service = CertificateInterestService()
        result = service.synchronize(today=date(2026, 7, 20))

        self.assertEqual(result.processed_certificates, 1)
        self.assertEqual(result.posted_periods, 4)
        self.assertEqual(float(result.total_interest_posted), 400.0)

        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1400.0)

        certificate.refresh_from_db()
        self.assertEqual(certificate.last_interest_posted_date, date(2026, 7, 15))
        self.assertEqual(
            BankCertificateInterestHistory.objects.filter(certificate=certificate).count(),
            4,
        )

        second = service.synchronize(today=date(2026, 7, 20))
        self.assertEqual(second.processed_certificates, 0)
        self.assertEqual(second.posted_periods, 0)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1400.0)

    def test_service_ignores_inactive_or_expired_certificates(self):
        inactive = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 31),
            amount=5000,
            interest_value=50,
            frequency="Monthly",
            status="Closed",
        )
        expired = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2025, 1, 1),
            expiry_date=date(2026, 3, 1),
            amount=5000,
            interest_value=50,
            frequency="Monthly",
            status="ACTIVE",
        )

        result = CertificateInterestService().synchronize(today=date(2026, 7, 20))
        self.assertEqual(result.processed_certificates, 0)
        self.assertEqual(result.posted_periods, 0)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1000.0)
        self.assertFalse(BankCertificateInterestHistory.objects.filter(certificate__in=[inactive, expired]).exists())

    def test_balance_view_triggers_interest_sync(self):
        BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 12, 31),
            amount=7000,
            interest_value=75,
            frequency="Quarterly",
            status="active",
            last_interest_posted_date=date(2026, 1, 1),
        )

        with patch("core.services.certificate.certificate_interest_service.timezone.localdate", return_value=date(2026, 7, 3)):
            response = self.client.get("/api/balance/")

        self.assertEqual(response.status_code, 200)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1150.0)

    def test_monthly_posts_only_when_eligible_day_is_reached(self):
        certificate = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2025, 1, 2),
            expiry_date=date(2026, 12, 31),
            amount=7000,
            interest_value=100,
            frequency="Monthly",
            status="Active",
            last_interest_posted_date=date(2026, 6, 2),
        )

        result_before = CertificateInterestService().synchronize(today=date(2026, 7, 1))
        self.assertEqual(result_before.posted_periods, 0)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1000.0)

        result_on_day = CertificateInterestService().synchronize(today=date(2026, 7, 2))
        self.assertEqual(result_on_day.posted_periods, 1)
        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1100.0)
        certificate.refresh_from_db()
        self.assertEqual(certificate.last_interest_posted_date, date(2026, 7, 2))

    def test_quarterly_never_posts_future_period(self):
        certificate = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2025, 1, 2),
            expiry_date=date(2026, 12, 31),
            amount=7000,
            interest_value=75,
            frequency="Quarterly",
            status="Active",
            last_interest_posted_date=date(2026, 7, 2),
        )

        result_before_oct = CertificateInterestService().synchronize(today=date(2026, 9, 30))
        self.assertEqual(result_before_oct.posted_periods, 0)

        result_on_oct = CertificateInterestService().synchronize(today=date(2026, 10, 2))
        self.assertEqual(result_on_oct.posted_periods, 1)

        self.cash_balance.refresh_from_db()
        self.assertEqual(float(self.cash_balance.amount), 1075.0)
        certificate.refresh_from_db()
        self.assertEqual(certificate.last_interest_posted_date, date(2026, 10, 2))

    def test_run_certificate_interest_sync_concurrency_and_error_handling(self):
        from core.views.certificate_views import _run_certificate_interest_sync
        from django.db.utils import OperationalError
        from unittest.mock import patch

        res1 = _run_certificate_interest_sync(force=True)
        self.assertIsNotNone(res1)

        # In production mode (not testing), immediate second call should be debounced and return None
        with patch("core.views.certificate_views._is_testing", return_value=False):
            res2 = _run_certificate_interest_sync(force=False)
            self.assertIsNone(res2)

        # Mock OperationalError (db locked) and ensure it returns None gracefully
        with patch("core.services.certificate.certificate_interest_service.CertificateInterestService.synchronize", side_effect=OperationalError("database is locked")):
            res_locked = _run_certificate_interest_sync(force=True)
            self.assertIsNone(res_locked)
