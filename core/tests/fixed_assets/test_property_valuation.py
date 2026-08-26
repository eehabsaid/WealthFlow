from core.models import AssetValuationHistory
from unittest.mock import MagicMock
import json
from datetime import date
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import (
    AppSettings,
    FixedAsset,
    RealEstateDetails,
)
from core.services.fixed_assets.property_valuation_service import PropertyValuationService

User = get_user_model()


class PropertyValuationServiceTest(TestCase):
    def setUp(self):
        self.asset = FixedAsset.objects.create(
            name="Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=600000,
        )
        self.details = RealEstateDetails.objects.create(
            asset=self.asset,
            city="Cairo",
            governorate="Cairo",
            area_m2=100,
        )

    def test_refresh_asset_updates_from_configured_provider(self):
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_city": {"Cairo": 42000}}),
        )

        updated, provider_name = PropertyValuationService().refresh_asset(self.asset, today=date(2026, 7, 4))

        self.asset.refresh_from_db()
        self.details.refresh_from_db()

        self.assertTrue(updated)
        self.assertEqual(provider_name, "configured_market_rate")
        self.assertEqual(float(self.asset.current_market_value), 4200000.0)
        self.assertEqual(float(self.details.last_estimated_market_price), 4200000.0)
        self.assertEqual(self.details.valuation_provider, "configured_market_rate")

    def test_refresh_asset_preserves_manual_value_when_unavailable(self):
        updated, provider_name = PropertyValuationService().refresh_asset(self.asset, today=date(2026, 7, 4))

        self.asset.refresh_from_db()
        self.details.refresh_from_db()

        self.assertFalse(updated)
        self.assertIsNone(provider_name)
        self.assertEqual(float(self.asset.current_market_value), 600000.0)
        self.assertEqual(self.details.valuation_provider, "")

    def test_manual_refresh_endpoint_updates_asset(self):
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_governorate": {"Cairo": 40000}}),
        )

        response = self.client.post(f"/api/fixed-assets/{self.asset.id}/valuation/refresh/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["updated"])
        self.assertEqual(payload["provider"], "configured_market_rate")

    def test_refresh_asset_records_valuation_history_row(self):
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_city": {"Cairo": 42000}}),
        )

        self.assertEqual(self.asset.valuation_history.count(), 0)

        updated, provider_name = PropertyValuationService().refresh_asset(self.asset, today=date(2026, 7, 4))
        self.assertTrue(updated)

        history_rows = list(self.asset.valuation_history.all())
        self.assertEqual(len(history_rows), 1)
        row = history_rows[0]
        self.assertEqual(float(row.market_value), 4200000.0)
        self.assertEqual(row.valuation_source, "Automatic")
        self.assertEqual(row.valuation_date, date(2026, 7, 4))
        self.assertIn(provider_name, row.notes)

    def test_refresh_asset_appends_new_history_row_each_time_instead_of_overwriting(self):
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_city": {"Cairo": 42000}}),
        )

        PropertyValuationService().refresh_asset(self.asset, today=date(2026, 7, 4))
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_city": {"Cairo": 43000}}),
        )
        PropertyValuationService().refresh_asset(self.asset, today=date(2026, 7, 5))

        self.assertEqual(self.asset.valuation_history.count(), 2)
        values = sorted(float(v) for v in self.asset.valuation_history.values_list("market_value", flat=True))
        self.assertEqual(values, [4200000.0, 4300000.0])

    def test_manual_refresh_endpoint_response_includes_new_history_row(self):
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_governorate": {"Cairo": 40000}}),
        )

        response = self.client.post(f"/api/fixed-assets/{self.asset.id}/valuation/refresh/")
        payload = response.json()
        history = payload["asset"]["valuation_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["valuation_source"], "Automatic")
        self.assertEqual(float(history[0]["market_value"]), 4000000.0)

    def test_manual_valuation_history_rows_are_untouched_by_refresh(self):
        AssetValuationHistory.objects.create(
            asset=self.asset,
            valuation_date=date(2026, 1, 1),
            market_value=550000,
            valuation_source="Manual",
            notes="Initial manual entry",
        )
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_city": {"Cairo": 42000}}),
        )

        PropertyValuationService().refresh_asset(self.asset, today=date(2026, 7, 4))

        self.assertEqual(self.asset.valuation_history.count(), 2)
        manual_row = self.asset.valuation_history.get(valuation_source="Manual")
        self.assertEqual(float(manual_row.market_value), 550000.0)
        self.assertEqual(manual_row.notes, "Initial manual entry")

    @patch("core.integrations.property_valuation_api.request.urlopen")
    def test_refresh_asset_uses_external_provider_when_enabled(self, mock_urlopen):
        AppSettings.set("property_valuation_external_enabled", "true")
        AppSettings.set(
            "property_valuation_external_url",
            "https://example.com/valuation?city={city}&area={area_m2}",
        )
        AppSettings.set("property_valuation_external_result_path", "estimated_price")

        response = MagicMock()
        response.read.return_value = b'{"estimated_price": 5100000}'
        mock_urlopen.return_value.__enter__.return_value = response

        updated, provider_name = PropertyValuationService().refresh_asset(
            self.asset,
            today=date(2026, 7, 4),
        )

        self.asset.refresh_from_db()
        self.details.refresh_from_db()

        self.assertTrue(updated)
        self.assertEqual(provider_name, "external_api")
        self.assertEqual(float(self.asset.current_market_value), 5100000.0)
        self.assertEqual(self.details.valuation_provider, "external_api")
