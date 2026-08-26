from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AssetSale,
    BalanceEntry,
    Currency,
    FixedAsset,
)

User = get_user_model()


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
