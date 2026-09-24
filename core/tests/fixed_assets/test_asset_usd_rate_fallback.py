from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Currency, ExchangeRate
from core.views.fixed_assets.fixed_asset_helpers import _resolve_asset_usd_rate_and_price


class ResolveAssetUsdRateAndPriceTests(TestCase):
    """_resolve_asset_usd_rate_and_price() is the backend fallback used when
    the frontend doesn't already supply purchase_usd_rate/purchase_price_usd
    (e.g. a direct API create). It must use the same "units of currency per
    1 USD" convention as UsdRateService, or a fallback-computed rate would
    silently disagree with what the "Now" button and UI display."""

    def setUp(self):
        self.user = User.objects.create_user(username="fallback_tester", password="x")
        sar, _ = Currency.objects.get_or_create(owner=self.user, code="SAR", defaults={"name": "SAR", "symbol": "SAR"})
        self.sar_id = sar.id
        ExchangeRate.objects.create(currency_code="USD", currency_name="US Dollar", buy_rate=Decimal("48.30"), sell_rate=Decimal("48.60"), mid_rate=Decimal("48.45"))
        ExchangeRate.objects.create(currency_code="SAR", currency_name="Saudi Riyal", buy_rate=Decimal("12.90"), sell_rate=Decimal("12.96"), mid_rate=Decimal("12.93"))

    def test_sar_fallback_rate_is_units_per_usd_and_price_is_correct(self):
        data = {"purchase_price": "375", "purchase_currency_id": self.sar_id}
        usd_rate, price_usd = _resolve_asset_usd_rate_and_price(data, owner=self.user)
        self.assertAlmostEqual(float(usd_rate), 48.30 / 12.90, places=4)
        self.assertAlmostEqual(float(price_usd), 100.0, delta=0.5)

    def test_egp_fallback_uses_pivot_rate_directly(self):
        data = {"purchase_price": "4830"}  # no purchase_currency_id -> falls back to base code
        usd_rate, price_usd = _resolve_asset_usd_rate_and_price(data, owner=self.user)
        # base currency defaults to EGP (no preferred_currency set)
        self.assertAlmostEqual(float(usd_rate), 48.30, places=2)
        self.assertAlmostEqual(float(price_usd), 100.0, places=1)
