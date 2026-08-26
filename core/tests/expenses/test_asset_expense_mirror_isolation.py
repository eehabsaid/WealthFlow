import json
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AssetFurniture,
    AssetRenovation,
    BalanceEntry,
    Currency,
    Expense,
    ExpenseCategory,
    FixedAsset,
)

User = get_user_model()


class AssetExpenseMirrorIsolationTest(TestCase):
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

    def test_mirror_via_acquisition_cost_endpoint_with_string_date(self):
        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=100000,
        )
        response = self.client.post(
            "/api/asset-acquisition-costs/",
            data=json.dumps({
                "asset_id": self.asset.id,
                "date": "2025-01-02",
                "category": "Lawyer Fees",
                "amount_egp": 25000,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        cost_id = response.json()["id"]
        mirror = Expense.objects.get(source_type="asset_acquisition_cost", source_id=cost_id)
        self.assertEqual(mirror.date, date(2025, 1, 2))
        self.assertEqual(mirror.amount_egp, Decimal("25000"))

    def test_mirror_via_renovation_endpoint_with_string_date(self):
        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=self.currency_egp,
            amount=100000,
        )
        response = self.client.post(
            "/api/asset-renovations/",
            data=json.dumps({
                "asset_id": self.asset.id,
                "date": "2025-02-15",
                "category": "Painting",
                "amount_egp": 4000,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        renovation_id = response.json()["id"]
        mirror = Expense.objects.get(source_type="asset_renovation", source_id=renovation_id)
        self.assertEqual(mirror.date, date(2025, 2, 15))

    def test_mirrors_accumulate_across_months_like_manual_expenses(self):
        AssetRenovation.objects.create(
            asset=self.asset, date=date(2025, 1, 15), category="Painting", amount_egp=5000
        )
        AssetRenovation.objects.create(
            asset=self.asset, date=date(2025, 2, 10), category="Flooring", amount_egp=9000
        )
        AssetFurniture.objects.create(
            asset=self.asset, name="Sofa", purchase_date=date(2025, 2, 20), amount_egp=8000
        )

        category = self._fixed_assets_category()
        jan_total = sum(
            float(e.amount_egp)
            for e in Expense.objects.filter(category=category, year=2025, month=1)
        )
        feb_total = sum(
            float(e.amount_egp)
            for e in Expense.objects.filter(category=category, year=2025, month=2)
        )
        self.assertEqual(jan_total, 5000)
        self.assertEqual(feb_total, 17000)

    def test_mirrored_expense_cannot_be_edited_or_deleted_via_expense_service(self):
        from core.services import ExpenseService

        renovation = AssetRenovation.objects.create(
            asset=self.asset, date=date(2025, 3, 10), category="Painting", amount_egp=5000
        )
        mirror = Expense.objects.get(source_type="asset_renovation", source_id=renovation.id)

        with self.assertRaises(ValueError) as ctx:
            ExpenseService.update_expense(mirror.id, {"amount": 9999})
        self.assertEqual(str(ctx.exception), "readonly_mirrored_expense")

        with self.assertRaises(ValueError) as ctx:
            ExpenseService.delete_expense(mirror.id)
        self.assertEqual(str(ctx.exception), "readonly_mirrored_expense")

        # Untouched
        mirror.refresh_from_db()
        self.assertEqual(mirror.amount_egp, Decimal("5000"))

    def test_mirrored_expense_endpoints_reject_edit_and_delete(self):
        renovation = AssetRenovation.objects.create(
            asset=self.asset, date=date(2025, 3, 10), category="Painting", amount_egp=5000
        )
        mirror = Expense.objects.get(source_type="asset_renovation", source_id=renovation.id)

        put_response = self.client.put(
            f"/api/expenses/{mirror.id}/",
            data=json.dumps({"amount": 9999}),
            content_type="application/json",
        )
        self.assertEqual(put_response.status_code, 400)
        self.assertEqual(put_response.json().get("error_key"), "readonly_mirrored_expense")

        delete_response = self.client.delete(f"/api/expenses/{mirror.id}/")
        self.assertEqual(delete_response.status_code, 400)
        self.assertEqual(delete_response.json().get("error_key"), "readonly_mirrored_expense")
