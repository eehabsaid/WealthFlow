from datetime import date
import json
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from core.models import BalanceEntry, Currency, FixedAsset

User = get_user_model()


class BalanceRecommendationTranslationsTest(SimpleTestCase):
    def test_recommendation_translation_keys_exist(self):
        locale_path = Path(__file__).resolve().parent.parent.parent.parent / "static" / "i18n" / "en.json"

        with locale_path.open(encoding="utf-8") as fh:
            translations = json.load(fh)

        required_keys = [
            "recommend_gold_downtrend",
            "recommend_gold_uptrend",
            "recommend_gold_strong_uptrend",
            "recommend_gold_strong_downtrend",
            "recommend_gold_neutral",
            "recommend_maturity_soon",
            "recommend_maturity_very_soon",
            "recommend_large_maturity_90",
            "recommend_idle_cash",
            "recommend_certificate_concentration",
            "recommend_low_liquidity",
            "recommend_high_cash_position",
            "recommend_high_foreign_currency_exposure",
            "recommend_low_emergency_fund",
            "recommend_excess_cash",
            "recommend_low_certificate_allocation",
            "recommend_asset_allocation_balanced",
            "action_renew_certificate",
            "action_gold_certificate_cash",
            "action_gold_cash",
            "action_gold_certificate",
        ]

        missing = [key for key in required_keys if not translations.get(key)]
        self.assertEqual([], missing, f"Missing translation keys: {missing}")


class NetWorthIntegrationTest(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="EGP", symbol="L", name="Egyptian Pound")
        BalanceEntry.objects.create(
            title="Cash",
            balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.currency,
            amount=1000,
        )

    def test_balance_grand_total_includes_fixed_assets_current_market_value(self):
        FixedAsset.objects.create(
            name="Apartment",
            asset_type="Real Estate",
            status="Owned",
            purchase_date=date(2024, 1, 1),
            purchase_price=500000,
            current_market_value=800000,
        )

        response = self.client.get("/api/balance/")
        self.assertEqual(response.status_code, 200)
        summary = response.json().get("summary", {})

        self.assertEqual(summary.get("fixed_assets_total"), 800000.0)
        self.assertEqual(summary.get("grand_total"), 1000.0)
        self.assertEqual(summary.get("net_worth"), 801000.0)
        expected_formula_total = (
            float((summary.get("totals_by_currency") or {}).get("EGP") or 0)
            + float(summary.get("usd_value") or 0)
            + float(summary.get("eur_value") or 0)
            + float(summary.get("sar_value") or 0)
            + float(summary.get("gold_value") or 0)
        )
        self.assertEqual(summary.get("grand_total"), expected_formula_total)
