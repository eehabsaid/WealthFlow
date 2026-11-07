from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Company, MonthlyIncomeAdjustment, SalaryEntry
from core.services.backup_serializer.export_order import get_model_export_order

User = get_user_model()
SUMMARY = "/api/expenses/summary/"
MANUAL = "/api/expenses/manual-income/"


def _income(client, year, month):
    return client.get(f"{SUMMARY}?year={year}&month={month}").json()["income_summary"]


class MonthlyIncomeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="inc_user", password="pass12345")
        self.other = User.objects.create_user(username="inc_other", password="pass12345")
        self.client.force_login(self.user)
        self.company = Company.objects.create(owner=self.user, name="Acme", display_name="Acme")
        for month, paid in (("september", 1000), ("october", 2000)):
            SalaryEntry.objects.create(
                company=self.company, year=2026, month=month, expected=paid, paid=paid, bonus=0
            )

    def _put(self, year, month, amount):
        return self.client.put(MANUAL, {"year": year, "month": month, "amount": amount}, content_type="application/json")

    def test_each_month_shows_only_its_own_salary(self):
        self.assertEqual(_income(self.client, 2026, 9)["total_income"], 1000.0)
        self.assertEqual(_income(self.client, 2026, 10)["total_income"], 2000.0)

    def test_manual_income_is_per_month(self):
        self.assertEqual(self._put(2026, 10, "500.50").status_code, 200)
        self.assertEqual(_income(self.client, 2026, 10)["total_income"], 2500.5)
        self.assertEqual(_income(self.client, 2026, 9)["total_income"], 1000.0)
        self.assertEqual(_income(self.client, 2026, 9)["manual_income"], 0.0)

    def test_yearly_sums_monthly_manual_income(self):
        self._put(2026, 9, 100)
        self._put(2026, 10, 200)
        summary = self.client.get(f"{SUMMARY}?year=2026").json()["income_summary"]
        self.assertEqual(summary["manual_income"], 300.0)
        self.assertEqual(summary["total_income"], 3300.0)

    def test_put_updates_existing_row_and_get_reads_it(self):
        self._put(2026, 10, 100)
        self._put(2026, 10, 250)
        self.assertEqual(MonthlyIncomeAdjustment.objects.filter(owner=self.user).count(), 1)
        self.assertEqual(self.client.get(f"{MANUAL}?year=2026&month=10").json()["amount"], 250.0)
        self.assertEqual(self.client.get(f"{MANUAL}?year=2026&month=9").json()["amount"], 0.0)

    def test_owner_isolation(self):
        MonthlyIncomeAdjustment.objects.create(owner=self.other, year=2026, month=10, amount=999)
        self.assertEqual(_income(self.client, 2026, 10)["manual_income"], 0.0)
        self.assertEqual(self.client.get(f"{MANUAL}?year=2026&month=10").json()["amount"], 0.0)

    def test_validation_and_auth(self):
        self.assertEqual(self._put(2026, 13, 1).status_code, 400)
        self.assertEqual(self._put(2026, 10, "abc").status_code, 400)
        self.assertEqual(self._put(2026, 10, -5).status_code, 400)
        self.assertEqual(self.client.get(MANUAL).status_code, 400)
        self.client.logout()
        self.assertIn(self.client.get(f"{MANUAL}?year=2026&month=10").status_code, (401, 403))

    def test_model_is_in_backup_export_order(self):
        self.assertIn(MonthlyIncomeAdjustment, [model for _, model, _ in get_model_export_order()])


class MonthlyRentalIncomeTest(TestCase):
    def setUp(self):
        from decimal import Decimal

        from core.models import AssetRental, Currency, FixedAsset, RentReceipt

        self.user = User.objects.create_user(username="rent_user", password="pass12345")
        self.client.force_login(self.user)
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        asset = FixedAsset.objects.create(owner=self.user, name="Flat", asset_type="Real Estate", status="Owned",
            purchase_date=date(2025, 1, 1),
        )
        self.rental = AssetRental.objects.create(
            asset=asset, monthly_rent=Decimal("1000"), occupancy_rate=Decimal("100"),
            contract_start=date(2026, 9, 1), contract_end=date(2026, 11, 30),
        )
        self.receipt_cls, self.currency = RentReceipt, currency

    def test_rental_counts_only_inside_contract(self):
        self.assertEqual(_income(self.client, 2026, 8)["total_rental_income"], 0.0)
        self.assertEqual(_income(self.client, 2026, 10)["total_rental_income"], 1000.0)
        self.assertEqual(_income(self.client, 2026, 12)["total_rental_income"], 0.0)

    def test_receipt_replaces_projection_for_its_month(self):
        self.receipt_cls.objects.create(
            owner=self.user, rental=self.rental, period_start=date(2026, 10, 1),
            received_date=date(2026, 10, 5), currency=self.currency, amount=900,
        )
        self.assertEqual(_income(self.client, 2026, 10)["total_rental_income"], 900.0)
        self.assertEqual(_income(self.client, 2026, 9)["total_rental_income"], 1000.0)

    def test_yearly_rental_is_sum_of_contract_months(self):
        summary = self.client.get(f"{SUMMARY}?year=2026").json()["income_summary"]
        self.assertEqual(summary["total_rental_income"], 3000.0)


class IncomeParityTest(TestCase):
    """The PDF and the on-screen card must report the same income figure."""

    def setUp(self):
        from core.models import BankCertificate, Currency

        self.user = User.objects.create_user(username="parity_user", password="pass12345")
        self.client.force_login(self.user)
        company = Company.objects.create(owner=self.user, name="Acme", display_name="Acme")
        for month, paid in (("september", 1000), ("october", 2000)):
            SalaryEntry.objects.create(company=company, year=2026, month=month, expected=paid, paid=paid, bonus=0)
        currency = Currency.objects.create(code="EGP", symbol="£", name="Egyptian Pound")
        from core.models import BalanceEntry

        BalanceEntry.objects.create(
            owner=self.user, title="Cash (EGP)", balance_type=BalanceEntry.BalanceType.CASH,
            bank=None, currency=currency, amount=100000,
        )
        BankCertificate.objects.create(
            owner=self.user, currency=currency, issue_date=date(2026, 10, 1),
            expiry_date=date(2026, 12, 31), amount=1000, interest_value=300, status="Active",
        )
        MonthlyIncomeAdjustment.objects.create(owner=self.user, year=2026, month=10, amount=50)

    def _pdf_income(self, **kw):
        from core.services.reports.report_service import ReportService

        return ReportService.get_period_income(self.user, **kw)

    def test_monthly_matches_screen(self):
        screen = _income(self.client, 2026, 10)["total_income"]
        self.assertEqual(screen, 2350.0)
        self.assertEqual(self._pdf_income(rtype="monthly", year=2026, month=10), screen)

    def test_yearly_matches_screen(self):
        screen = self.client.get(f"{SUMMARY}?year=2026").json()["income_summary"]["total_income"]
        self.assertEqual(self._pdf_income(rtype="yearly", year=2026, month=1), screen)

    def test_custom_range_matches_screen_and_spans_months(self):
        url = f"{SUMMARY}?year=2026&start=2026-09-15&end=2026-10-20"
        screen = self.client.get(url).json()["income_summary"]["total_income"]
        self.assertEqual(screen, 1000 + 2000 + 300 + 50)
        pdf = self._pdf_income(rtype="custom", year=2026, month=1, start_date="2026-09-15", end_date="2026-10-20")
        self.assertEqual(pdf, screen)

    def test_summary_rejects_bad_dates(self):
        self.assertEqual(self.client.get(f"{SUMMARY}?year=2026&start=nope&end=2026-10-20").status_code, 400)
