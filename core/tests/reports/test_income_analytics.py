"""Income Analytics: service + API tests (test DB, expected totals computed from the seed)."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import (
    AssetRental,
    AssetSale,
    Bank,
    BankCertificate,
    BankCertificateInterestHistory,
    BankInterest,
    BalanceEntry,
    Company,
    Currency,
    FixedAsset,
    MonthlyIncomeAdjustment,
    PerDiem,
    RentReceipt,
    SalaryEntry,
)

# The seed (owner's rows), year 2025 — expected totals are computed from this dict.
SEED_2025 = {
    "salary": [11000, 12000, 13000],
    "bonus": [7000],
    "perdiem": [2500],
    "cert": [9000, 9000],
    "bank": [1000],
    "rent": [3000],
    "manual": [1500],
    "sale": [50000],
}


def seed_owner(user):
    cur, _ = Currency.objects.get_or_create(owner=user, code="EGP", defaults={"name": "Egyptian Pound"})
    co = Company.objects.create(owner=user, name="Acme", display_name="Acme")
    rows = [
        (2024, "January", "10000", "10000", None, "0"),
        (2024, "February", "12000", "12000", None, "5000"),
        (2025, "January", "11000", "11000", "13000", "0"),
        (2025, "February", "12000", "12000", None, "0"),
        (2025, "March", "13000", "13000", "15000", "7000"),
        (2026, "January", "14000", "14000", None, "0"),
    ]
    for year, month, paid, expected, gross, bonus in rows:
        SalaryEntry.objects.create(
            company=co, year=year, month=month, paid=Decimal(paid),
            expected=Decimal(expected), gross=Decimal(gross) if gross else None,
            bonus=Decimal(bonus),
        )
    PerDiem.objects.create(
        company=co, year=2025, date=date(2025, 6, 15), currency=cur,
        amount=Decimal("2500"), amount_base=Decimal("2500"),
    )
    bank = Bank.objects.create(owner=user, name="Test Bank")
    BalanceEntry.objects.create(
        owner=user, title="Cash", balance_type="cash", bank=bank, currency=cur,
        amount=Decimal("1000000"),
    )
    cert = BankCertificate.objects.create(
        owner=user, bank=bank, currency=cur, issue_date=date(2024, 4, 1), expiry_date=date(2027, 4, 1),
        amount=Decimal("900000"), interest_rate=Decimal("12"), interest_value=Decimal("108000"),
        frequency="Monthly", status="Active",
    )
    BankCertificateInterestHistory.objects.create(
        certificate=cert, posting_date=date(2025, 4, 1), posting_period="2025-04",
        interest_amount=Decimal("9000"),
    )
    BankCertificateInterestHistory.objects.create(
        certificate=cert, posting_date=date(2025, 5, 1), posting_period="2025-05",
        interest_amount=Decimal("9000"),
    )
    BankInterest.objects.create(owner=user, interest_date=date(2025, 7, 1), currency=cur, amount=Decimal("1000"))
    asset = FixedAsset.objects.create(
        owner=user, name="Rental Apartment", asset_type="Real Estate", status="Active",
        purchase_date=date(2020, 1, 1), purchase_price=Decimal("2000000"),
        purchase_usd_rate=Decimal("50"), purchase_price_usd=Decimal("40000"),
        current_market_value=Decimal("2200000"),
    )
    rental = AssetRental.objects.create(
        asset=asset, monthly_rent=Decimal("3000"), occupancy_rate=Decimal("1"),
        tenant_name="T", contract_start=date(2025, 1, 1), contract_end=date(2026, 1, 1),
        receive_method="Bank",
    )
    RentReceipt.objects.create(
        owner=user, rental=rental, period_start=date(2025, 8, 1), received_date=date(2025, 8, 1),
        currency=cur, amount=Decimal("3000"),
    )
    MonthlyIncomeAdjustment.objects.create(owner=user, year=2025, month=9, amount=Decimal("1500"))
    asset2 = FixedAsset.objects.create(
        owner=user, name="Old Car", asset_type="Vehicle", status="Sold",
        purchase_date=date(2018, 1, 1), purchase_price=Decimal("300000"),
        purchase_usd_rate=Decimal("50"), purchase_price_usd=Decimal("6000"),
        current_market_value=Decimal("50000"),
    )
    AssetSale.objects.create(
        asset=asset2, sale_date=date(2025, 10, 5), sale_price=Decimal("55000"),
        selling_expenses=Decimal("5000"), net_sale_amount=Decimal("50000"), deposit_method="Bank",
    )
    return co


class IncomeAnalyticsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="inc_owner", password="pw123456")
        self.other = User.objects.create_user(username="inc_other", password="pw123456")
        seed_owner(self.user)
        oco = Company.objects.create(owner=self.other, name="OtherCo", display_name="OtherCo")
        SalaryEntry.objects.create(
            company=oco, year=2025, month="January", paid=Decimal("999999"),
            expected=Decimal("999999"), bonus=Decimal("0"),
        )

    def api(self, user=None, **qs):
        if user:
            self.client.force_login(user)
        params = "&".join(f"{k}={v}" for k, v in qs.items())
        return self.client.get("/api/reports/income/" + (f"?{params}" if params else ""))

    def test_off_mode_totals_per_source_match_seed(self):
        r = self.api(user=self.user, mode="off", year="2025")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        expected = {k: round(sum(v), 2) for k, v in SEED_2025.items()}
        for g in data["groups"]:
            self.assertEqual(g["amount_a"], expected[g["source"]], g["source"])
        self.assertEqual(data["grand"]["total_a"], round(sum(expected.values()), 2))
        self.assertEqual(data["stats_a"]["records"], sum(len(v) for v in SEED_2025.values()))

    def test_yoy_mode_totals_and_change(self):
        r = self.api(user=self.user, mode="yoy", ya="2024", yb="2025")
        data = r.json()
        self.assertEqual(data["grand"]["total_a"], 27000.0)  # 10000 + 12000 + 5000 bonus
        self.assertEqual(data["grand"]["total_b"], round(sum(v for vs in SEED_2025.values() for v in vs), 2))

    def test_mom_mode_and_same_year_months(self):
        r = self.api(user=self.user, mode="mom", ma="1", mya="2025", mb="2", myb="2025")
        data = r.json()
        self.assertEqual(data["grand"]["total_a"], 11000.0)
        self.assertEqual(data["grand"]["total_b"], 12000.0)
        r2 = self.api(user=self.user, mode="mom", ma="1", mya="2025", mb="3", myb="2025")
        self.assertEqual(r2.json()["grand"]["total_b"], 20000.0)  # 13000 salary + 7000 bonus

    def test_months_filter(self):
        r = self.api(user=self.user, mode="off", year="2025", months="1,2")
        data = r.json()
        self.assertEqual(data["grand"]["total_a"], 23000.0)

    def test_sources_filter(self):
        r = self.api(user=self.user, mode="off", year="2025", sources="salary,bonus")
        data = r.json()
        self.assertEqual(data["grand"]["total_a"], 43000.0)
        self.assertEqual({g["source"] for g in data["groups"]}, {"salary", "bonus"})

    def test_gross_basis_used_when_filled_else_net(self):
        r = self.api(user=self.user, mode="off", year="2025", basis="gross")
        data = r.json()
        salary = next(g for g in data["groups"] if g["source"] == "salary")
        self.assertEqual(salary["amount_a"], 40000.0)  # 13000 + 12000 (net fallback) + 15000
        self.assertTrue(data["salary_gross_missing"])

    def test_cert_counts_real_postings_only(self):
        r = self.api(user=self.user, mode="off", year="2025")
        cert = next(g for g in r.json()["groups"] if g["source"] == "cert")
        self.assertEqual(cert["amount_a"], 18000.0)
        self.assertEqual(cert["count_a"], 2)

    def test_owner_isolation(self):
        r = self.api(user=self.other, mode="off", year="2025")
        self.assertEqual(r.json()["grand"]["total_a"], 999999.0)
        r2 = self.api(user=self.user, mode="off", year="2025")
        self.assertNotIn(999999.0, [g["amount_a"] for g in r2.json()["groups"]])

    def test_auth_required(self):
        r = self.client.get("/api/reports/income/")
        self.assertEqual(r.status_code, 401)
