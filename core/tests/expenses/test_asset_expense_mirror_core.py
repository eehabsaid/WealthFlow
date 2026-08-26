from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AssetFurniture,
    AssetRenovation,
    Bank,
    Currency,
    Expense,
    ExpenseCategory,
    ExpenseSubcategory,
    FixedAsset,
)

User = get_user_model()


class AssetExpenseMirrorCoreTest(TestCase):
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

    def test_category_and_subcategories_created_on_first_mirror(self):
        self.assertIsNone(self._fixed_assets_category())

        renovation = AssetRenovation.objects.create(
            asset=self.asset,
            date=date(2025, 3, 10),
            category="Painting",
            amount_egp=5000,
        )

        category = self._fixed_assets_category()
        self.assertIsNotNone(category)
        subcat = category.subcategories.get(name="Renovation")
        mirror = Expense.objects.get(source_type="asset_renovation", source_id=renovation.id)
        self.assertEqual(mirror.category_id, category.id)
        self.assertEqual(mirror.subcategory_id, subcat.id)

    def test_existing_manually_created_category_is_reused(self):
        existing = ExpenseCategory.objects.create(name="Fixed Assets", icon="🧱", color_hex="#123456")
        existing_sub = ExpenseSubcategory.objects.create(category=existing, name="Furniture")

        furniture = AssetFurniture.objects.create(
            asset=self.asset,
            name="Sofa",
            purchase_date=date(2025, 4, 1),
            amount_egp=8000,
        )

        mirror = Expense.objects.get(source_type="asset_furniture", source_id=furniture.id)
        self.assertEqual(mirror.category_id, existing.id)
        self.assertEqual(mirror.subcategory_id, existing_sub.id)
        self.assertEqual(ExpenseCategory.objects.filter(name="Fixed Assets").count(), 1)

    def test_renovation_create_update_delete_mirrors(self):
        renovation = AssetRenovation.objects.create(
            asset=self.asset,
            date=date(2025, 3, 10),
            category="Painting",
            description="Living room paint job",
            amount_egp=5000,
            payment_method="Cash",
        )
        mirror = Expense.objects.get(source_type="asset_renovation", source_id=renovation.id)
        self.assertEqual(mirror.amount_egp, Decimal("5000"))
        self.assertEqual(mirror.description, "Renovation: Painting — Living room paint job")
        self.assertTrue(mirror.is_readonly_mirror)
        self.assertEqual(mirror.year, 2025)
        self.assertEqual(mirror.month, 3)

        renovation.amount_egp = 7500
        renovation.description = "Living room + hallway paint job"
        renovation.save()
        mirror.refresh_from_db()
        self.assertEqual(mirror.amount_egp, Decimal("7500"))
        self.assertEqual(mirror.description, "Renovation: Painting — Living room + hallway paint job")
        # still exactly one mirror row for this renovation
        self.assertEqual(
            Expense.objects.filter(source_type="asset_renovation", source_id=renovation.id).count(), 1
        )

        renovation_id = renovation.id
        renovation.delete()
        self.assertFalse(
            Expense.objects.filter(source_type="asset_renovation", source_id=renovation_id).exists()
        )

    def test_renovation_bank_payment_method_normalized(self):
        bank = Bank.objects.create(name="Test Bank")
        renovation = AssetRenovation.objects.create(
            asset=self.asset,
            date=date(2025, 3, 10),
            category="Plumbing",
            amount_egp=3000,
            payment_method="Bank",
            bank=bank,
        )
        mirror = Expense.objects.get(source_type="asset_renovation", source_id=renovation.id)
        self.assertEqual(mirror.payment_method, "Bank Transfer")
        self.assertEqual(mirror.bank_id, bank.id)

    def test_zero_amount_renovation_is_not_mirrored(self):
        renovation = AssetRenovation.objects.create(
            asset=self.asset,
            date=date(2025, 3, 10),
            category="Painting",
            amount_egp=0,
        )
        self.assertFalse(
            Expense.objects.filter(source_type="asset_renovation", source_id=renovation.id).exists()
        )

    def test_renovation_mirror_removed_when_amount_cleared_to_zero(self):
        renovation = AssetRenovation.objects.create(
            asset=self.asset,
            date=date(2025, 3, 10),
            category="Painting",
            amount_egp=5000,
        )
        self.assertTrue(
            Expense.objects.filter(source_type="asset_renovation", source_id=renovation.id).exists()
        )

        renovation.amount_egp = 0
        renovation.save()
        self.assertFalse(
            Expense.objects.filter(source_type="asset_renovation", source_id=renovation.id).exists()
        )
