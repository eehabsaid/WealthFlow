import json
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AssetAcquisitionCost,
    BalanceEntry,
    Currency,
    FixedAsset,
)

User = get_user_model()


class FixedAssetAcquisitionCostsTest(TestCase):
    def setUp(self):
        self.asset = FixedAsset.objects.create(
            name="Test Property",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2025, 1, 1),
            purchase_price=1000000,
            current_market_value=1200000,
        )
        # Acquisition costs now debit a matching Cash balance entry (money-movement
        # sync, same pattern as core/services/expenses/expense_service.py). A Cash
        # entry must exist or the create/update endpoints return 400
        # matching_balance_entry_not_found.
        currency_egp, _ = Currency.objects.get_or_create(
            code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"}
        )
        self.cash_entry = BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            bank=None,
            currency=currency_egp,
            amount=1000000,
        )

    def test_acquisition_cost_categories_endpoint(self):
        response = self.client.get("/api/asset-acquisition-costs/categories/")
        self.assertEqual(response.status_code, 200)
        categories = response.json().get("categories")
        self.assertIn("Lawyer Fees", categories)
        self.assertIn("Brokerage Fees", categories)

    def test_crud_endpoints(self):
        # Create
        response = self.client.post(
            "/api/asset-acquisition-costs/",
            data=json.dumps({
                "asset_id": self.asset.id,
                "date": "2025-01-02",
                "category": "Lawyer Fees",
                "description": "Fee for legal consultation",
                "amount_egp": 25000,
                "usd_rate": 50.0,
                "amount_usd": 500,
                "notes": "Some notes",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        cost_id = response.json()["id"]

        # List
        response = self.client.get(f"/api/asset-acquisition-costs/?asset={self.asset.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["acquisition_costs"]), 1)

        # Update
        response = self.client.put(
            f"/api/asset-acquisition-costs/{cost_id}/",
            data=json.dumps({
                "category": "Government Fees",
                "amount_egp": 30000,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["category"], "Government Fees")
        self.assertEqual(response.json()["amount_egp"], 30000.0)

        # Delete
        response = self.client.delete(f"/api/asset-acquisition-costs/{cost_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssetAcquisitionCost.objects.count(), 0)

    def test_backend_calculations(self):
        AssetAcquisitionCost.objects.create(
            asset=self.asset,
            date=date(2025, 1, 2),
            category="Lawyer Fees",
            amount_egp=50000,
        )
        AssetAcquisitionCost.objects.create(
            asset=self.asset,
            date=date(2025, 1, 3),
            category="Registration Fees",
            amount_egp=30000,
        )

        self.assertEqual(self.asset.get_total_acquisition_costs(), Decimal("80000"))
        self.assertEqual(self.asset.get_total_investment(), Decimal("1080000"))
        self.assertEqual(self.asset.get_gain_loss(), Decimal("120000")) # 1.2M market - 1.08M inv
        self.assertAlmostEqual(float(self.asset.get_roi()), 120000 / 1080000 * 100)
