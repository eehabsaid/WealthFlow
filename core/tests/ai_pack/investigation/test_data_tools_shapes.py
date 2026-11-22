"""Data tools tests: grouping and real query shapes."""


import datetime
from decimal import Decimal


from core.models import (
    AssetAcquisitionCost,
    AssetFurniture,
    AssetRenovation,
    BalanceEntry,
    Bank,
    BankCertificate,
    BankCertificateInterestHistory,
    Currency,
    Expense,
    FixedAsset,
    RealEstateDetails,
    SalaryEntry,
)

from core.tests.ai_pack.investigation.support import seed_tenant
from .data_tools_support import DataToolsBase


class DataToolsQueryShapeTest(DataToolsBase):
    def test_composite_grouping_and_having_find_duplicate_expense_rows(self):
        tenant = seed_tenant(self.a, "D", expenses=0)
        for index in range(2):
            Expense.objects.create(
                owner=self.a,
                date=datetime.date(2026, 9, 10),
                year=2026,
                month=9,
                category=tenant["category"],
                amount=Decimal("25.00"),
                amount_base=Decimal("25.00"),
                currency=tenant["currency"],
                bank=tenant["bank"],
                description=f"duplicate candidate {index}",
            )

        duplicates = self.q(
            self.a,
            model="Expense",
            group_by="date,amount_base,category",
            aggregate={"count": "*"},
            having={"count__gt": 1},
        )
        self.assertEqual(duplicates["group_count"], 1)
        self.assertEqual(sum(row["count"] for row in duplicates["groups"]), 2)

    def test_actual_expense_query_shape_distinguishes_base_and_transaction_currency(self):
        tenant = seed_tenant(self.a, "X", expenses=0)
        euro = Currency.objects.create(owner=self.a, code="EUR", name="Euro")
        Expense.objects.create(
            owner=self.a,
            date=datetime.date(2026, 9, 10),
            year=2026,
            month=9,
            category=tenant["category"],
            amount=Decimal("100.00"),
            amount_base=Decimal("150.00"),
            currency=euro,
            bank=tenant["bank"],
        )

        base_total = self.q(
            self.a,
            model="Expense",
            filters={"category__name__iexact": "Cat X", "date__year": 2026},
            aggregate={"count": "*", "sum": "amount_base"},
        )
        source_total = self.q(
            self.a,
            model="Expense",
            filters={"category__name__iexact": "Cat X", "date__year": 2026},
            aggregate={"sum": "amount"},
        )
        self.assertEqual(base_total["result"]["count"], 1)
        self.assertEqual(Decimal(base_total["result"]["sum_amount_base"]), Decimal("150.00"))
        self.assertEqual(Decimal(source_total["result"]["sum_amount"]), Decimal("100.00"))

    def test_actual_bank_and_certificate_queries_use_related_currency_fields(self):
        bank = Bank.objects.get(owner=self.a, name="Bank A")
        egp, _ = Currency.objects.get_or_create(
            owner=self.a, code="EGP", defaults={"name": "Egyptian Pound"}
        )
        BalanceEntry.objects.create(
            owner=self.a, title="cash", balance_type="cash", bank=bank, currency=egp, amount=Decimal("1000.00")
        )
        BalanceEntry.objects.create(
            owner=self.a, title="bank", balance_type="bank", bank=bank, currency=egp, amount=Decimal("200.00")
        )
        balance = self.q(
            self.a,
            model="BalanceEntry",
            filters={
                "bank__name__icontains": "Bank A",
                "currency__code__iexact": "EGP",
                "balance_type__in": ["cash", "bank"],
            },
            aggregate={"count": "*", "sum": "amount"},
        )
        self.assertEqual(balance["result"]["count"], 2)
        self.assertEqual(Decimal(balance["result"]["sum_amount"]), Decimal("1200.00"))
        grouped = self.q(
            self.a,
            model="BalanceEntry",
            group_by="currency__code",
            aggregate={"sum": "amount"},
        )
        self.assertEqual(grouped["groups"][0]["currency__code"], "EGP")
        self.assertEqual(Decimal(grouped["groups"][0]["sum_amount"]), Decimal("1200.00"))

        certificate = BankCertificate.objects.create(
            owner=self.a, bank=bank, currency=egp, amount=Decimal("1000.00")
        )
        BankCertificateInterestHistory.objects.create(
            certificate=certificate,
            posting_date=datetime.date(2023, 4, 1),
            posting_period="2023-04",
            bank=bank,
            currency=egp,
            interest_amount=Decimal("15.00"),
        )
        interest = self.q(
            self.a,
            model="BankCertificateInterestHistory",
            filters={"currency__code__iexact": "EGP", "posting_date__year": 2023},
            aggregate={"count": "*", "sum": "interest_amount"},
        )
        self.assertEqual(interest["result"]["count"], 1)
        self.assertEqual(Decimal(interest["result"]["sum_interest_amount"]), Decimal("15.00"))

    def test_actual_salary_and_asset_queries_use_their_own_models_and_fields(self):
        salary = SalaryEntry.objects.get(company__owner=self.a)
        salary.year, salary.month = 2026, "September"
        salary.expected, salary.paid = Decimal("1000.00"), Decimal("800.00")
        salary.save()
        salary_total = self.q(
            self.a,
            model="SalaryEntry",
            filters={"year": 2026, "month": "September"},
            aggregate={"sum": "expected", "count": "*"},
        )
        self.assertEqual(salary_total["result"]["count"], 1)
        self.assertEqual(Decimal(salary_total["result"]["sum_expected"]), Decimal("1000.00"))

        asset = FixedAsset.objects.get(owner=self.a)
        AssetFurniture.objects.bulk_create([
            AssetFurniture(asset=asset, name="Sofa", amount_base=Decimal("100.00"), amount_usd=Decimal("10.00"))
        ])
        AssetAcquisitionCost.objects.bulk_create([
            AssetAcquisitionCost(asset=asset, category="Fees", amount_base=Decimal("200.00"), amount_usd=Decimal("20.00"))
        ])
        AssetRenovation.objects.create(
            asset=asset,
            date=datetime.date(2026, 9, 10),
            category="Kitchen",
            amount_base=Decimal("54848.25"),
        )
        RealEstateDetails.objects.create(asset=asset, last_estimated_market_price=Decimal("50000.00"))

        furniture = self.q(self.a, model="AssetFurniture", aggregate={"sum": "amount_usd", "count": "*"})
        acquisition = self.q(self.a, model="AssetAcquisitionCost", aggregate={"sum": "amount_base"})
        renovation = self.q(
            self.a,
            model="AssetRenovation",
            filters={"asset__name__iexact": "Asset A"},
            aggregate={"sum": "amount_base", "count": "*"},
        )
        details = self.q(self.a, model="RealEstateDetails", aggregate={"count": "*"})
        self.assertEqual(Decimal(furniture["result"]["sum_amount_usd"]), Decimal("10.00"))
        self.assertEqual(Decimal(acquisition["result"]["sum_amount_base"]), Decimal("200.00"))
        self.assertEqual(renovation["result"]["count"], 1)
        self.assertEqual(Decimal(renovation["result"]["sum_amount_base"]), Decimal("54848.25"))
        self.assertEqual(details["result"]["count"], 1)
