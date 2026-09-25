from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Currency, ExchangeRate, FixedAsset, GoldDetails, GoldPrice, UserProfile
from core.services.fixed_assets.gold_sync_service.sync import _refresh_gold_asset_pricing


class GoldAssetCurrencyNeutralityTests(TestCase):
    """Gold prices are always sourced in EGP (GOLD_PRICE_CURRENCY). A gold
    asset's current_market_value must be expressed in its owner's own base
    currency like every other asset type, not silently left in EGP."""

    def setUp(self):
        self.gold_price = GoldPrice.objects.create(
            carat_24k=Decimal("4000.00"),
            carat_22k=Decimal("3700.00"),
            carat_21k=Decimal("3500.00"),
            carat_18k=Decimal("3000.00"),
            usd_to_egp=Decimal("48.500000"),
        )

    def _make_gold_asset(self, owner):
        asset = FixedAsset.objects.create(
            owner=owner,
            name="Gold bar",
            asset_type="Gold",
            purchase_date="2024-01-01",
            purchase_price=Decimal("1000"),
        )
        details = GoldDetails.objects.create(asset=asset, purity="21k", weight=Decimal("10"), unit="gram")
        return asset, details

    def test_egp_base_owner_value_unchanged(self):
        """No preferred_currency set -> base defaults to EGP (platform
        fallback). Behavior must be byte-identical to before this fix."""
        user = User.objects.create_user(username="egp_owner", password="x")
        asset, details = self._make_gold_asset(user)

        _refresh_gold_asset_pricing(asset, details, self.gold_price)

        self.assertEqual(asset.current_market_value, Decimal("35000.00"))  # 10g * 3500 EGP/g

    def test_non_egp_base_owner_value_converted(self):
        user = User.objects.create_user(username="usd_owner", password="x")
        usd, _ = Currency.objects.get_or_create(owner=user, code="USD", defaults={"name": "USD", "symbol": "$"})
        UserProfile.objects.update_or_create(user=user, defaults={"preferred_currency": "USD"})
        ExchangeRate.objects.create(currency_code="USD", currency_name="US Dollar", buy_rate=Decimal("48.500000"), sell_rate=Decimal("48.60"), mid_rate=Decimal("48.55"))

        asset, details = self._make_gold_asset(user)
        _refresh_gold_asset_pricing(asset, details, self.gold_price)

        from core.services.shared.currency_conversion_service import CurrencyConversionService

        _, expected = CurrencyConversionService.convert_amount(Decimal("35000.00"), "EGP", "USD")
        self.assertEqual(asset.current_market_value, expected)
