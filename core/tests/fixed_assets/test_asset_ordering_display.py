from core.models import AssetFurniture
from core.models import AssetInsurance
from core.models import AssetMaintenance
from core.models import AssetPhoto
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AssetAcquisitionCost,
    FixedAsset,
)

User = get_user_model()


class FixedAssetListOrderingTest(TestCase):
    """Every list-bearing tab on an asset (Furniture, Acquisition Costs,
    Maintenance, Insurance, Photos, plus the already-fixed Renovation /
    Valuation History / Documents) should show newest-first, matching the
    ordering already applied to renovations."""

    def setUp(self):
        self.re_asset = FixedAsset.objects.create(
            name="Nile View Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2025, 1, 1),
            purchase_price=1000000,
            current_market_value=1200000,
        )
        self.vehicle_asset = FixedAsset.objects.create(
            name="Family Car",
            asset_type="Vehicles",
            status="Owned",
            purchase_date=date(2025, 1, 1),
            purchase_price=500000,
            current_market_value=450000,
        )

    def test_furniture_ordered_newest_first(self):
        older = AssetFurniture.objects.create(
            asset=self.re_asset, name="Sofa", purchase_date=date(2025, 1, 5), amount_egp=1000
        )
        newer = AssetFurniture.objects.create(
            asset=self.re_asset, name="Chair", purchase_date=date(2025, 6, 1), amount_egp=500
        )
        ordered = list(AssetFurniture.objects.filter(asset=self.re_asset))
        self.assertEqual([f.id for f in ordered], [newer.id, older.id])

    def test_acquisition_costs_ordered_newest_first(self):
        older = AssetAcquisitionCost.objects.create(
            asset=self.re_asset, date=date(2025, 1, 5), category="Lawyer Fees", amount_egp=1000
        )
        newer = AssetAcquisitionCost.objects.create(
            asset=self.re_asset, date=date(2025, 6, 1), category="Registration", amount_egp=500
        )
        ordered = list(AssetAcquisitionCost.objects.filter(asset=self.re_asset))
        self.assertEqual([c.id for c in ordered], [newer.id, older.id])

    def test_maintenance_ordered_newest_first(self):
        older = AssetMaintenance.objects.create(
            asset=self.vehicle_asset, date=date(2025, 1, 5), maintenance_type="Oil Change", cost=300
        )
        newer = AssetMaintenance.objects.create(
            asset=self.vehicle_asset, date=date(2025, 6, 1), maintenance_type="Tires", cost=1200
        )
        ordered = list(AssetMaintenance.objects.filter(asset=self.vehicle_asset))
        self.assertEqual([m.id for m in ordered], [newer.id, older.id])

    def test_insurance_ordered_newest_first(self):
        older = AssetInsurance.objects.create(
            asset=self.vehicle_asset, company="Insurer A", expiry_date=date(2025, 6, 1), premium=1000
        )
        newer = AssetInsurance.objects.create(
            asset=self.vehicle_asset, company="Insurer B", expiry_date=date(2026, 1, 1), premium=1200
        )
        ordered = list(AssetInsurance.objects.filter(asset=self.vehicle_asset))
        self.assertEqual([i.id for i in ordered], [newer.id, older.id])

    def test_photos_ordered_newest_first(self):
        older = AssetPhoto.objects.create(asset=self.re_asset, filename="a.jpg", title="A")
        newer = AssetPhoto.objects.create(asset=self.re_asset, filename="b.jpg", title="B")
        ordered = list(AssetPhoto.objects.filter(asset=self.re_asset))
        self.assertEqual([p.id for p in ordered], [newer.id, older.id])

    def test_maintenance_endpoint_returns_newest_first(self):
        older = AssetMaintenance.objects.create(
            asset=self.vehicle_asset, date=date(2025, 1, 5), maintenance_type="Oil Change", cost=300
        )
        newer = AssetMaintenance.objects.create(
            asset=self.vehicle_asset, date=date(2025, 6, 1), maintenance_type="Tires", cost=1200
        )
        response = self.client.get(f"/api/asset-maintenance/?asset={self.vehicle_asset.id}")
        self.assertEqual(response.status_code, 200)
        ids = [m["id"] for m in response.json()["maintenance"]]
        self.assertEqual(ids, [newer.id, older.id])

    def test_insurance_endpoint_returns_newest_first(self):
        older = AssetInsurance.objects.create(
            asset=self.vehicle_asset, company="Insurer A", expiry_date=date(2025, 6, 1), premium=1000
        )
        newer = AssetInsurance.objects.create(
            asset=self.vehicle_asset, company="Insurer B", expiry_date=date(2026, 1, 1), premium=1200
        )
        response = self.client.get(f"/api/asset-insurance/?asset={self.vehicle_asset.id}")
        self.assertEqual(response.status_code, 200)
        ids = [i["id"] for i in response.json()["insurance"]]
        self.assertEqual(ids, [newer.id, older.id])

    def test_furniture_endpoint_returns_newest_first(self):
        older = AssetFurniture.objects.create(
            asset=self.re_asset, name="Sofa", purchase_date=date(2025, 1, 5), amount_egp=1000
        )
        newer = AssetFurniture.objects.create(
            asset=self.re_asset, name="Chair", purchase_date=date(2025, 6, 1), amount_egp=500
        )
        response = self.client.get(f"/api/asset-furniture/?asset={self.re_asset.id}")
        self.assertEqual(response.status_code, 200)
        ids = [f["id"] for f in response.json()["furniture"]]
        self.assertEqual(ids, [newer.id, older.id])

    def test_acquisition_costs_endpoint_returns_newest_first(self):
        older = AssetAcquisitionCost.objects.create(
            asset=self.re_asset, date=date(2025, 1, 5), category="Lawyer Fees", amount_egp=1000
        )
        newer = AssetAcquisitionCost.objects.create(
            asset=self.re_asset, date=date(2025, 6, 1), category="Registration", amount_egp=500
        )
        response = self.client.get(f"/api/asset-acquisition-costs/?asset={self.re_asset.id}")
        self.assertEqual(response.status_code, 200)
        ids = [c["id"] for c in response.json()["acquisition_costs"]]
        self.assertEqual(ids, [newer.id, older.id])

    def test_maintenance_and_insurance_readable_via_asset_to_dict(self):
        """Confirms the whole-asset payload (used to populate the detail
        page tabs) also carries the fixed ordering, not just the standalone
        list endpoints."""
        older = AssetMaintenance.objects.create(
            asset=self.vehicle_asset, date=date(2025, 1, 5), maintenance_type="Oil Change", cost=300
        )
        newer = AssetMaintenance.objects.create(
            asset=self.vehicle_asset, date=date(2025, 6, 1), maintenance_type="Tires", cost=1200
        )
        payload = self.vehicle_asset.to_dict()
        ids = [m["id"] for m in payload["maintenance"]]
        self.assertEqual(ids, [newer.id, older.id])
