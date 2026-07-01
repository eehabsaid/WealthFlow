import json
from datetime import date
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from core.models import BankCertificate, Company, Currency, SalaryEntry


class BalanceRecommendationTranslationsTest(SimpleTestCase):
    def test_recommendation_translation_keys_exist(self):
        base_dir = Path(__file__).resolve().parent.parent
        locale_path = base_dir / "static" / "i18n" / "en.json"

        with locale_path.open(encoding="utf-8") as fh:
            translations = json.load(fh)

        required_keys = [
            "recommend_gold_downtrend",
            "recommend_gold_uptrend",
            "recommend_gold_strong_uptrend",
            "recommend_gold_strong_downtrend",
            "recommend_gold_neutral",
            "recommend_maturity_soon",
            "recommend_maturity_very_soon",
            "recommend_large_maturity_90",
            "recommend_idle_cash",
            "recommend_certificate_concentration",
            "recommend_low_liquidity",
            "recommend_high_cash_position",
            "recommend_high_foreign_currency_exposure",
            "recommend_low_emergency_fund",
            "recommend_excess_cash",
            "recommend_low_certificate_allocation",
            "recommend_asset_allocation_balanced",
            "action_renew_certificate",
            "action_gold_certificate_cash",
            "action_gold_cash",
            "action_gold_certificate",
        ]

        missing = [key for key in required_keys if not translations.get(key)]
        self.assertEqual([], missing, f"Missing translation keys: {missing}")


class CertificateForecastBalanceTest(TestCase):
    def test_forecast_excludes_inactive_certificates_from_balance_metrics(self):
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
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
        self.assertEqual(payload["summary"]["monthly_interest"], 50.0 / 12)

        overdue_buckets = payload["buckets"]["overdue"]
        self.assertEqual(len(overdue_buckets), 1)
        self.assertEqual(overdue_buckets[0]["status"], "Active")


class ExpenseSummaryIncomeTest(TestCase):
    def test_income_summary_uses_previous_month_salary_and_certificate_interest_window(self):
        company = Company.objects.create(name="Acme", display_name="Acme")
        SalaryEntry.objects.create(
            company=company,
            year=2026,
            month="june",
            expected=10000,
            paid=5000,
            bonus=0,
        )
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")

        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=1000,
            interest_value=100,
            status="Active",
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 6, 1),
            expiry_date=date(2026, 8, 31),
            amount=1000,
            interest_value=200,
            status="Inactive",
        )
        BankCertificate.objects.create(
            currency=currency,
            issue_date=date(2026, 9, 1),
            expiry_date=date(2026, 10, 31),
            amount=1000,
            interest_value=999,
            status="Active",
        )

        response = self.client.get("/api/expenses/summary/?year=2026&month=7")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        income_summary = payload["income_summary"]

        self.assertEqual(income_summary["total_salary"], 5000.0)
        self.assertEqual(income_summary["total_interest"], 300.0)
        self.assertEqual(income_summary["total_income"], 5300.0)
