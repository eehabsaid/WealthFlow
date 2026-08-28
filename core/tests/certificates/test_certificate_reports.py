from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    BalanceEntry,
    BankCertificate,
    Currency,
)

User = get_user_model()


class CertificateForecastBalanceTest(TestCase):
    def test_forecast_excludes_inactive_certificates_from_balance_metrics(self):
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        # Matching cash balance entry required for certificate saves to
        # succeed (see certificate_balance_deduction_service.py).
        BalanceEntry.objects.create(
            title="Cash (EGP)",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=currency,
            amount=100000,
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=300,
            interest_value=50,
            status="Active",
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=700,
            interest_value=150,
            status="Inactive",
        )

        response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["certificate_balance"], 300.0)
        self.assertEqual(payload["monthly_certificate_income"], 50.0)


class CertificateReportActiveOnlyTest(TestCase):
    def test_certificate_report_uses_active_certificates_only(self):
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        # Matching cash balance entry required for certificate saves to
        # succeed (see certificate_balance_deduction_service.py).
        BalanceEntry.objects.create(
            title="Cash (EGP)",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=currency,
            amount=100000,
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 6, 1),
            amount=500,
            interest_value=50,
            status="Active",
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 6, 1),
            amount=300,
            interest_value=30,
            status="Inactive",
        )
        response = self.client.get("/api/reports/certificates/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["summary"]["total_count"], 1)
        self.assertEqual(payload["summary"]["total_amount"], 500.0)
        self.assertEqual(payload["summary"]["total_interest"], 50.0)
        self.assertEqual(payload["summary"]["monthly_interest"], 50.0)

        overdue_buckets = payload["buckets"]["overdue"]
        self.assertEqual(len(overdue_buckets), 1)
        self.assertEqual(overdue_buckets[0]["status"], "Active")
