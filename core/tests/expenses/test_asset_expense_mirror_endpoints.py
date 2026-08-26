from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AssetAcquisitionCost,
    AssetFurniture,
    AssetRenovation,
    Currency,
    Expense,
    ExpenseCategory,
    FixedAsset,
)

User = get_user_model()


class AssetExpenseMirrorEndpointsTest(TestCase):
    def setUp(self):
        self.asset = FixedAsset.objects.create(
            name="Nile View Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2025, 1, 1),
            purchase_price=1000000,
            current_market_value=1200000,
        )
        self.currency_egp, _ = Currency.objects.get_or_create(
            code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"}
        )

    def _fixed_assets_category(self):
        return ExpenseCategory.objects.filter(name="Fixed Assets").first()

    def test_renovation_description_falls_back_to_category_when_blank(self):
        renovation = AssetRenovation.objects.create(
            asset=self.asset,
            date=date(2025, 3, 10),
            category="Plumbing",
            amount_egp=1000,
        )
        mirror = Expense.objects.get(source_type="asset_renovation", source_id=renovation.id)
        self.assertEqual(mirror.description, "Renovation: Plumbing")

    def test_acquisition_cost_mirrors_and_defaults_to_today_when_date_missing(self):
        cost = AssetAcquisitionCost.objects.create(
            asset=self.asset,
            date=date(2025, 1, 5),
            category="Lawyer Fees",
            amount_egp=25000,
        )
        mirror = Expense.objects.get(source_type="asset_acquisition_cost", source_id=cost.id)
        self.assertEqual(mirror.amount_egp, Decimal("25000"))

        cost.date = None
        cost.save()
        mirror.refresh_from_db()
        # Missing date defaults to today rather than dropping the mirror,
        # so the spend is never silently missing from Expenses/dashboards.
        self.assertEqual(mirror.date, date.today())
        self.assertEqual(mirror.amount_egp, Decimal("25000"))

    def test_furniture_without_purchase_date_mirrors_with_todays_date(self):
        furniture = AssetFurniture.objects.create(
            asset=self.asset,
            name="Dining Table",
            amount_egp=12000,
        )
        mirror = Expense.objects.get(source_type="asset_furniture", source_id=furniture.id)
        self.assertEqual(mirror.date, date.today())
        self.assertEqual(mirror.amount_egp, Decimal("12000"))

        furniture.purchase_date = date(2025, 5, 20)
        furniture.save()
        mirror.refresh_from_db()
        self.assertEqual(mirror.date, date(2025, 5, 20))
        self.assertEqual(mirror.month, 5)

    def test_furniture_description_combines_category_and_name(self):
        furniture = AssetFurniture.objects.create(
            asset=self.asset,
            name="Sofa",
            category="Living Room",
            purchase_date=date(2025, 4, 1),
            amount_egp=8000,
        )
        mirror = Expense.objects.get(source_type="asset_furniture", source_id=furniture.id)
        self.assertEqual(mirror.description, "Furniture: Living Room — Sofa")

    def test_zero_amount_furniture_is_not_mirrored(self):
        furniture = AssetFurniture.objects.create(
            asset=self.asset,
            name="Free sample chair",
            purchase_date=date(2025, 4, 1),
            amount_egp=0,
        )
        self.assertFalse(
            Expense.objects.filter(source_type="asset_furniture", source_id=furniture.id).exists()
        )

    def test_furniture_stable_id_updates_mirror_in_place(self):
        furniture = AssetFurniture.objects.create(
            asset=self.asset,
            name="Chair",
            purchase_date=date(2025, 6, 1),
            amount_egp=1500,
        )
        mirror_id = Expense.objects.get(source_type="asset_furniture", source_id=furniture.id).id

        furniture.amount_egp = 1800
        furniture.save()

        self.assertEqual(Expense.objects.filter(source_type="asset_furniture").count(), 1)
        updated_mirror = Expense.objects.get(source_type="asset_furniture", source_id=furniture.id)
        self.assertEqual(updated_mirror.id, mirror_id)
        self.assertEqual(updated_mirror.amount_egp, Decimal("1800"))
