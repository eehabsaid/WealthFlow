import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import (
    BalanceEntry,
    Bank,
    BankCertificate,
    BankCertificateInterestHistory,
    Company,
    Currency,
    Expense,
    ExpenseCategory,
    FixedAsset,
    AssetMortgage,
    AssetRental,
    AssetSale,
    SalaryEntry,
)
from core.services.certificate_interest_service import CertificateInterestService


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


class ExpenseBalanceIntegrationTest(TestCase):
    def setUp(self):
        self.currency_egp = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.bank_cib = Bank.objects.create(name="CIB")
        self.bank_qnb = Bank.objects.create(name="QNB")
        self.category = ExpenseCategory.objects.create(name="Utilities", icon="💡", color_hex="#0d6efd")

        self.cash_entry = BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=2000,
        )
        self.cib_entry = BalanceEntry.objects.create(
            title="CIB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank_cib,
            currency=self.currency_egp,
            amount=10000,
        )
        self.qnb_entry = BalanceEntry.objects.create(
            title="QNB Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=self.bank_qnb,
            currency=self.currency_egp,
            amount=5000,
        )

    def test_create_requires_bank_for_card_or_bank_and_deducts_from_matching_balance(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 300,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Card",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 500,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Cash",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.cash_entry.refresh_from_db()
        self.assertEqual(float(self.cash_entry.amount), 1500.0)

        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-02",
                    "category_id": self.category.id,
                    "amount": 1200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Bank",
                    "bank_id": self.bank_cib.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.cib_entry.refresh_from_db()
        self.assertEqual(float(self.cib_entry.amount), 8800.0)

    def test_edit_and_delete_restore_and_apply_correct_balance(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 1200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Bank",
                    "bank_id": self.bank_cib.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        expense_id = response.json()["id"]

        response = self.client.put(
            f"/api/expenses/{expense_id}/",
            data=json.dumps(
                {
                    "amount": 300,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.cib_entry.refresh_from_db()
        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.cib_entry.amount), 10000.0)
        self.assertEqual(float(self.qnb_entry.amount), 4700.0)

        response = self.client.delete(f"/api/expenses/{expense_id}/")
        self.assertEqual(response.status_code, 200)
        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.qnb_entry.amount), 5000.0)
        self.assertFalse(Expense.objects.filter(pk=expense_id).exists())

    def test_create_expense_rejected_when_balance_would_be_negative(self):
        response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 2500,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Cash",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("error"), "insufficient_balance")
        self.cash_entry.refresh_from_db()
        self.assertEqual(float(self.cash_entry.amount), 2000.0)
        self.assertEqual(Expense.objects.count(), 0)

    def test_edit_expense_rejected_when_new_deduction_would_be_negative(self):
        create_response = self.client.post(
            "/api/expenses/",
            data=json.dumps(
                {
                    "date": "2026-07-01",
                    "category_id": self.category.id,
                    "amount": 200,
                    "currency_id": self.currency_egp.id,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        expense_id = create_response.json()["id"]

        edit_response = self.client.put(
            f"/api/expenses/{expense_id}/",
            data=json.dumps(
                {
                    "amount": 6000,
                    "payment_method": "Card",
                    "bank_id": self.bank_qnb.id,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(edit_response.status_code, 400)
        self.assertEqual(edit_response.json().get("error"), "insufficient_balance")

        self.qnb_entry.refresh_from_db()
        self.assertEqual(float(self.qnb_entry.amount), 4800.0)

        exp = Expense.objects.get(pk=expense_id)
        self.assertEqual(float(exp.amount), 200.0)
        self.assertEqual(exp.bank_id, self.bank_qnb.id)


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

        with patch("core.services.certificate_interest_service.timezone.localdate", return_value=date(2026, 7, 3)):
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


class NetWorthIntegrationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="L", name="Egyptian Pound")
        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.currency,
            amount=1000,
        )

    def test_balance_grand_total_includes_fixed_assets_current_market_value(self):
        FixedAsset.objects.create(
            name="Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2024, 1, 1),
            purchase_price=500000,
            current_market_value=800000,
        )

        response = self.client.get("/api/balance/")
        self.assertEqual(response.status_code, 200)
        summary = response.json().get("summary", {})

        self.assertEqual(summary.get("fixed_assets_total"), 800000.0)
        self.assertEqual(summary.get("grand_total"), 1000.0)
        self.assertEqual(summary.get("net_worth"), 801000.0)
        expected_formula_total = (
            float((summary.get("totals_by_currency") or {}).get("EGP") or 0)
            + float(summary.get("usd_value") or 0)
            + float(summary.get("eur_value") or 0)
            + float(summary.get("sar_value") or 0)
            + float(summary.get("gold_value") or 0)
        )
        self.assertEqual(summary.get("grand_total"), expected_formula_total)


class RentalIncomeSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.asset = FixedAsset.objects.create(
            name="Rental Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=600000,
        )

    def test_rental_income_updates_balance_forecast_and_reports_income(self):
        rental = AssetRental.objects.create(
            asset=self.asset,
            monthly_rent=1000,
            occupancy_rate=80,
            tenant_name="Tenant A",
        )

        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:rental-income:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        balance_payload = balance_response.json()
        self.assertEqual(balance_payload["summary"]["grand_total"], 800.0)

        forecast_response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(forecast_response.status_code, 200)
        forecast_payload = forecast_response.json()
        self.assertEqual(forecast_payload["monthly_rental_income"], 800.0)

        report_response = self.client.get("/api/expenses/summary/?year=2026&month=7")
        self.assertEqual(report_response.status_code, 200)
        report_payload = report_response.json()["income_summary"]
        self.assertEqual(report_payload["total_rental_income"], 800.0)
        self.assertEqual(report_payload["total_income"], 800.0)

        rental.delete()
        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:rental-income:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["grand_total"], 0.0)


class MortgageSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.asset = FixedAsset.objects.create(
            name="Mortgage Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=600000,
        )

    def test_mortgage_updates_balance_and_clears_on_delete(self):
        mortgage = AssetMortgage.objects.create(
            asset=self.asset,
            loan_amount=300000,
            remaining_balance=240000,
            monthly_installment=5000,
            interest_rate=8.5,
            start_date=date(2026, 1, 1),
        )

        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:mortgage-liability:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 360000.0)

        mortgage.remaining_balance = 200000
        mortgage.save()

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 400000.0)

        mortgage.delete()
        self.assertFalse(
            BalanceEntry.objects.filter(notes__startswith="wealthflow:mortgage-liability:asset:").exists()
        )

        balance_response = self.client.get("/api/balance/")
        self.assertEqual(balance_response.status_code, 200)
        self.assertEqual(balance_response.json()["summary"]["net_worth"], 600000.0)


class AssetSaleSynchronizationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        self.deposit_balance = BalanceEntry.objects.create(
            title="Deposit",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.currency,
            amount=1000,
        )
        self.asset = FixedAsset.objects.create(
            name="Sold Car",
            asset_type="Vehicles",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=400000,
            current_market_value=450000,
        )

    def test_asset_sale_updates_selected_balance_and_reverses_on_delete(self):
        sale = AssetSale.objects.create(
            asset=self.asset,
            sale_date=date(2026, 7, 1),
            sale_price=300000,
            selling_expenses=5000,
            net_sale_amount=295000,
            deposit_balance=self.deposit_balance,
        )

        self.deposit_balance.refresh_from_db()
        self.assertEqual(float(self.deposit_balance.amount), 296000.0)

        sale.net_sale_amount = 300000
        sale.save()

        self.deposit_balance.refresh_from_db()
        self.assertEqual(float(self.deposit_balance.amount), 301000.0)

        sale.delete()

        self.deposit_balance.refresh_from_db()
        self.assertEqual(float(self.deposit_balance.amount), 1000.0)


class FixedAssetSnapshotTest(TestCase):
    def test_certificate_forecast_exposes_fixed_assets_snapshot(self):
        FixedAsset.objects.create(
            name="Car",
            asset_type="Vehicles",
            status="Owned",
            purchase_date=date(2025, 6, 1),
            purchase_price=300000,
            current_market_value=250000,
        )

        response = self.client.get("/api/certificate-forecast/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertIn("fixed_assets_balance", payload)
        self.assertIn("fixed_assets_snapshot", payload)
        self.assertGreaterEqual(float(payload.get("fixed_assets_balance") or 0), 250000.0)

    def test_fixed_assets_list_returns_portfolio_snapshot(self):
        FixedAsset.objects.create(
            name="Studio",
            asset_type="Other Assets",
            status="Owned",
            purchase_date=date(2025, 1, 1),
            purchase_price=100000,
            current_market_value=120000,
        )

        response = self.client.get("/api/fixed-assets/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertIn("portfolio_snapshot", payload)
        self.assertEqual(payload["portfolio_snapshot"]["total_fixed_assets_value"], 120000.0)


class DocumentManagementApiTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="L", name="Egyptian Pound")
        self.bank = Bank.objects.create(name="QNB")
        self.asset = FixedAsset.objects.create(
            name="Doc Asset",
            asset_type="Other Assets",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=1000,
            current_market_value=1200,
        )
        self.certificate = BankCertificate.objects.create(
            bank=self.bank,
            currency=self.currency,
            issue_date=date(2026, 1, 1),
            expiry_date=date(2027, 1, 1),
            amount=5000,
            interest_value=500,
            frequency="Monthly",
            status="Active",
        )

    def test_upload_list_download_replace_and_delete_document(self):
        upload = SimpleUploadedFile(
            "contract.pdf",
            b"test-pdf-content",
            content_type="application/pdf",
        )

        response = self.client.post(
            f"/api/documents/fixed_asset/{self.asset.id}/",
            {
                "file": upload,
                "document_category": "Purchase Contracts",
                "notes": "Initial document",
            },
        )
        self.assertEqual(response.status_code, 201)
        created = response.json()
        doc_id = created["id"]

        list_response = self.client.get(f"/api/documents/fixed_asset/{self.asset.id}/")
        self.assertEqual(list_response.status_code, 200)
        docs = list_response.json().get("documents", [])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["document_category"], "Purchase Contracts")

        inline_response = self.client.get(f"/api/documents/file/{doc_id}/?disposition=inline")
        self.assertEqual(inline_response.status_code, 200)
        self.assertIn("inline;", inline_response["Content-Disposition"])

        replace = SimpleUploadedFile(
            "contract-new.pdf",
            b"new-pdf-content",
            content_type="application/pdf",
        )
        replace_response = self.client.post(
            f"/api/documents/file/{doc_id}/",
            {
                "file": replace,
            },
        )
        self.assertEqual(replace_response.status_code, 200)
        self.assertEqual(replace_response.json()["original_file_name"], "contract-new.pdf")

        delete_response = self.client.delete(f"/api/documents/file/{doc_id}/")
        self.assertEqual(delete_response.status_code, 200)

        final_list = self.client.get(f"/api/documents/fixed_asset/{self.asset.id}/")
        self.assertEqual(final_list.status_code, 200)
        self.assertEqual(final_list.json().get("documents", []), [])

    def test_document_categories_and_validation(self):
        categories_response = self.client.get("/api/documents/categories/?parent_type=bank_certificate")
        self.assertEqual(categories_response.status_code, 200)
        categories = categories_response.json().get("categories", [])
        self.assertIn("Certificate Documents", categories)

        invalid_upload = SimpleUploadedFile(
            "notes.txt",
            b"invalid-extension",
            content_type="text/plain",
        )
        invalid_response = self.client.post(
            f"/api/documents/bank_certificate/{self.certificate.id}/",
            {
                "file": invalid_upload,
                "document_category": "Certificate Documents",
            },
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(invalid_response.json().get("error"), "invalid_file_type")
