from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    BalanceEntry,
    BankCertificate,
    Currency,
)
from core.reports.generate_report_generator.data_phase import build_report_data

User = get_user_model()


class CertificateForecastBalanceTest(TestCase):
    def test_forecast_excludes_inactive_certificates_from_balance_metrics(self):
        self.user = User.objects.create_user(username="testuser_certfc", password="pass12345")
        self.client.force_login(self.user)
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        # Matching cash balance entry required for certificate saves to
        # succeed (see certificate_balance_deduction_service.py).
        BalanceEntry.objects.create(
            owner=self.user,
            title="Cash (EGP)",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=currency,
            amount=100000,
        )
        BankCertificate.objects.create(
            owner=self.user,
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=300,
            interest_value=50,
            status="Active",
        )
        BankCertificate.objects.create(
            owner=self.user,
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
        self.user = User.objects.create_user(username="testuser_certro", password="pass12345")
        self.client.force_login(self.user)
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        # Matching cash balance entry required for certificate saves to
        # succeed (see certificate_balance_deduction_service.py).
        BalanceEntry.objects.create(
            owner=self.user,
            title="Cash (EGP)",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=currency,
            amount=100000,
        )
        BankCertificate.objects.create(
            owner=self.user,
            currency=currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 6, 1),
            amount=500,
            interest_value=50,
            status="Active",
        )
        BankCertificate.objects.create(
            owner=self.user,
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

    def test_expense_report_income_includes_only_active_certificate_interest(self):
        user = User.objects.create_user(username="testuser_expense_certro")
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        BalanceEntry.objects.create(
            owner=user,
            title="Cash (EGP)",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=currency,
            amount=100000,
        )
        for status, interest in (
            ("Active", 50),
            ("aCtIvE", 25),
            ("Inactive", 30),
            ("closed", 15),
        ):
            BankCertificate.objects.create(
                owner=user,
                currency=currency,
                issue_date=date(2026, 1, 1),
                expiry_date=date(2026, 6, 1),
                amount=500,
                interest_value=interest,
                status=status,
            )

        report_data = build_report_data(
            {"type": "yearly", "year": 2026},
            "en",
            {},
            user,
        )

        self.assertEqual(report_data["total_inc"], 75.0)
