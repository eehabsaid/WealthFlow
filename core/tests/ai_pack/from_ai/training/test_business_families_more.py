"""Business family tests: per diem, rent, assets and month questions."""


import datetime
from decimal import Decimal


from ai.training.services import phrasing
from core.ai_pack.training_families import assets, income
from core.models import (
    AssetFurniture,
    AssetMortgage,
    AssetRental,
    Currency,
    PerDiem,
    RentReceipt,
)
from .business_families_support import BusinessFamilyBase


class BusinessFamilyMoreTest(BusinessFamilyBase):
    def test_per_diem_and_rent_stay_available_when_salary_currency_is_not_comparable(self):
        PerDiem.objects.create(
            company=self.company, year=2025, date=datetime.date(2025, 2, 1), currency=self.currency,
            amount=Decimal("100.00"), amount_base=Decimal("100.00"),
        )
        rental = AssetRental.objects.create(
            asset=self.asset, monthly_rent=Decimal("500.00"), occupancy_rate=Decimal("80.00")
        )
        RentReceipt.objects.create(
            owner=self.user, rental=rental, period_start=datetime.date(2025, 1, 1),
            received_date=datetime.date(2025, 1, 5), currency=self.currency, amount=Decimal("200.00"),
        )
        foreign, _ = Currency.objects.get_or_create(
            owner=self.user, code="OTHER", defaults={"name": "Other currency"}
        )
        self.company.current_salary_currency = foreign
        self.company.save(update_fields=["current_salary_currency"])

        training = self._cases(income, "train", self.user)
        other_income = self._assert_four_languages(training, "other_income_year:2025")
        self.assertEqual(other_income.expected["values"], ["100.00", "200.00", "300.00"])
        self.assertFalse(any(case.key.startswith("income_stream_year:") for case in training))

    def test_asset_equity_and_furniture_cost_follow_asset_relations(self):
        AssetMortgage.objects.create(
            asset=self.asset, loan_amount=Decimal("30000.00"), remaining_balance=Decimal("20000.00"),
            monthly_installment=Decimal("500.00"),
        )
        AssetFurniture.objects.create(
            asset=self.asset, name="Desk", category="Furniture", amount_base=Decimal("300.00"),
        )
        rental = AssetRental.objects.create(
            asset=self.asset, monthly_rent=Decimal("500.00"), occupancy_rate=Decimal("80.00")
        )
        RentReceipt.objects.create(
            owner=self.user, rental=rental, period_start=datetime.date(2025, 1, 1),
            received_date=datetime.date(2025, 1, 5), currency=self.currency, amount=Decimal("200.00"),
        )

        training = self._cases(assets, "train", self.user)
        equity = self._assert_four_languages(training, f"asset_equity:{self.asset.pk}")
        self.assertEqual(equity.expected["values"], ["30000.00"])
        self.assertEqual(equity.meta["category"], "cross")
        self.assertFalse(any(case.key.startswith("eval:") for case in training))

        evaluation = self._cases(assets, "evaluate", self.user)
        furniture = self._assert_four_languages(evaluation, f"eval:furniture_cost:{self.asset.pk}")
        receipts = self._assert_four_languages(evaluation, f"eval:rent_receipts_year:{self.asset.pk}:2025")
        self.assertEqual(furniture.expected["values"], ["300.00"])
        self.assertEqual(receipts.expected["values"], ["200.00"])
        self.assertTrue(all(case.key.startswith("eval:") for case in evaluation))

    def test_month_questions_include_a_numeric_month_reference(self):
        self.assertIn("(month 9)", phrasing.month("en", 2025, 9))
        self.assertIn("(mois 9)", phrasing.month("fr", 2025, 9))
        self.assertIn("(Monat 9)", phrasing.month("de", 2025, 9))
        self.assertIn("(الشهر 9)", phrasing.month("ar", 2025, 9))
