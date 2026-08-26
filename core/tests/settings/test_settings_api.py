import json
from django.test import TestCase
from core.models import AppSettings


class SettingsAPITestCase(TestCase):
    def test_single_setting_save(self):
        payload = {"key": "test_single_key", "value": "test_single_val"}
        res = self.client.post(
            "/api/settings/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["key"], "test_single_key")
        self.assertEqual(data["value"], "test_single_val")
        self.assertEqual(AppSettings.get("test_single_key"), "test_single_val")

    def test_batch_dict_setting_save(self):
        payload = {
            "settings": {
                "property_valuation_rate_map": '{"Cairo": 100}',
                "property_valuation_provider_order": "configured_market_rate",
                "property_valuation_external_enabled": "true",
            }
        }
        res = self.client.post(
            "/api/settings/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(
            AppSettings.get("property_valuation_rate_map"), '{"Cairo": 100}'
        )
        self.assertEqual(
            AppSettings.get("property_valuation_provider_order"),
            "configured_market_rate",
        )
        self.assertEqual(
            AppSettings.get("property_valuation_external_enabled"), "true"
        )

    def test_batch_list_setting_save(self):
        payload = [
            {"key": "batch_k1", "value": "batch_v1"},
            {"key": "batch_k2", "value": "batch_v2"},
        ]
        res = self.client.post(
            "/api/settings/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(AppSettings.get("batch_k1"), "batch_v1")
        self.assertEqual(AppSettings.get("batch_k2"), "batch_v2")

    def test_empty_settings_payload(self):
        res = self.client.post(
            "/api/settings/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_arabic_english_location_valuation_matching(self):
        from datetime import date
        from core.models import FixedAsset, RealEstateDetails
        from core.services.fixed_assets.property_valuation_service import (
            PropertyValuationService,
        )

        asset = FixedAsset.objects.create(
            name="شقة القاهرة",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=500000,
        )
        RealEstateDetails.objects.create(
            asset=asset,
            city="القاهرة",
            governorate="القاهرة",
            area_m2=100,
        )

        # Rate Map has English keys
        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({"by_city": {"Cairo": 25000}}),
        )

        updated, provider = PropertyValuationService().refresh_asset(asset)
        asset.refresh_from_db()
        self.assertTrue(updated)
        self.assertEqual(provider, "configured_market_rate")
        self.assertEqual(float(asset.current_market_value), 2500000.0)

    def test_arabic_city_valuation_matching(self):
        from datetime import date
        from core.models import FixedAsset, RealEstateDetails
        from core.services.fixed_assets.property_valuation_service import (
            PropertyValuationService,
        )

        asset = FixedAsset.objects.create(
            name="شقة المعادي",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2026, 1, 1),
            purchase_price=500000,
            current_market_value=500000,
        )
        RealEstateDetails.objects.create(
            asset=asset,
            city="المعادي",
            governorate="القاهرة",
            area_m2=100,
        )

        AppSettings.set(
            "property_valuation_rate_map",
            json.dumps({
                "by_city": {
                    "Maadi": 26950,
                    "Fifth Settlement": 61550,
                    "Wadi Hoff": 18000
                },
                "default": 33000
            }),
        )

        updated, provider = PropertyValuationService().refresh_asset(asset)
        asset.refresh_from_db()
        self.assertTrue(updated)
        self.assertEqual(provider, "configured_market_rate")
        self.assertEqual(float(asset.current_market_value), 2695000.0)
