"""AI providers and instant answers must follow the user's market: a SAR/AED-base user
gets spot gold in their own currency and no EGP rate; an Egyptian user is unchanged."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import ExchangeRate, FixedAsset, GoldDetails, GoldPrice
from core.services.ai.providers.assets_provider import FixedAssetsDataProvider
from core.services.ai.providers.market_provider import MarketDataProvider
from core.services.ai.query_engine.executors.market import run_gold
from core.services.ai.query_engine.spec import QueryRequest
from core.services.shared.base_currency import set_user_base_currency
from core.services.shared.market_profile import ensure_base_catalog, prune_egp_for_gulf_user

User = get_user_model()
RATES = {"USD": "52.30", "SAR": "13.94", "AED": "14.23", "EGP": "0.019"}


class AiGulfMarketTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ai_gulf", password="pw-12345-x")
        for code, value in RATES.items():
            ExchangeRate.objects.create(currency_code=code, currency_name=code, buy_rate=Decimal(value),
                                        sell_rate=Decimal(value), mid_rate=Decimal(value))
        GoldPrice.objects.create(
            carat_24k=7000, carat_22k=6400, carat_21k=6125, carat_18k=5250,
            carat_24k_buy=6900, carat_22k_buy=6300, carat_21k_buy=6025, carat_18k_buy=5150,
            usd_gram_24k=Decimal("134.000000"), usd_per_oz=Decimal("4168.0000"), usd_to_egp=Decimal("52.300000"),
        )

    def _go_gulf(self, code="SAR"):
        ensure_base_catalog(self.user, code)
        set_user_base_currency(self.user, code)
        prune_egp_for_gulf_user(self.user)

    def test_market_provider_hides_egp_and_gives_spot_gold_for_gulf_user(self):
        self._go_gulf("SAR")
        data = MarketDataProvider().get_data(self.user)
        self.assertNotIn("EGP", {r["currency_code"] for r in data["exchange_rates"]})
        gold = data["latest_gold_price"]
        self.assertEqual(gold["market"], "spot")
        self.assertEqual(gold["currency"], "SAR")
        self.assertAlmostEqual(gold["carat_24k"], 134 * 52.30 / 13.94, places=1)

    def test_market_provider_unchanged_for_egyptian_user(self):
        data = MarketDataProvider().get_data(self.user)
        self.assertIn("EGP", {r["currency_code"] for r in data["exchange_rates"]})
        self.assertEqual(data["latest_gold_price"]["carat_24k"], 7000)
        self.assertNotIn("market", data["latest_gold_price"])

    def test_instant_gold_answer_is_in_base_currency_for_gulf_user(self):
        self._go_gulf("AED")
        result = run_gold(self.user, QueryRequest(capability="gold", filters={"karat": "24"}))
        self.assertIn("AED", result.intro)
        self.assertNotIn("EGP", result.intro)
        self.assertAlmostEqual(result.facts["sell"], 134 * 52.30 / 14.23, delta=0.01)
        self.assertEqual(result.facts["sell"], result.facts["buy"])

    def test_instant_gold_answer_unchanged_for_egyptian_user(self):
        result = run_gold(self.user, QueryRequest(capability="gold", filters={"karat": "24"}))
        self.assertIn("EGP", result.intro)
        self.assertEqual(result.facts["sell"], 7000.0)
        self.assertEqual(result.facts["buy"], 6900.0)

    def test_assets_provider_values_gold_at_spot_in_base_currency(self):
        self._go_gulf("SAR")
        asset = FixedAsset.objects.create(owner=self.user, name="Ring", asset_type="Gold", status="Owned",
                                          purchase_date=date(2024, 1, 1), purchase_price=Decimal("3000"),
                                          current_market_value=Decimal("3000"))
        GoldDetails.objects.create(asset=asset, purity="24k", weight=Decimal("10"))
        data = FixedAssetsDataProvider().get_data(self.user)
        item = next(i for i in data["items"] if i["name"] == "Ring")
        self.assertAlmostEqual(item["current_market_value"], 10 * 134 * 52.30 / 13.94, delta=0.2)


class AiPromptCurrencyExampleTests(TestCase):
    """The system prompt's worked example must use the viewer's own currency (no EGP for a SAR user)."""

    def test_prompt_example_uses_home_currency(self):
        import inspect

        from core.services.ai.context_builder_service import prompt as prompt_module

        source = inspect.getsource(prompt_module)
        self.assertNotIn("50.9 EGP/USD", source)
        self.assertIn("{home_currency}/USD", source)
