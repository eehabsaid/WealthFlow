"""Regression: AI providers must convert using buy_rate (the app-wide convention), not
mid_rate/sell_rate. Ehab reported the AI chat's EGP total didn't match the Balance page
because it used the wrong side of the rate."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Currency, ExchangeRate
from core.services.ai.providers.balance_provider import BalanceDataProvider
from core.services.shared.currency_conversion_service import CurrencyConversionService

User = get_user_model()


class ProviderUsesBuyRateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyrate_ai", password="pw12345")
        self.egp = Currency.objects.get_or_create(code="EGP", owner=self.user, defaults={"name": "Egyptian Pound", "symbol": "EGP"})[0]
        self.usd = Currency.objects.get_or_create(code="USD", owner=self.user, defaults={"name": "US Dollar", "symbol": "$"})[0]
        # Deliberately distinct buy/mid/sell so a wrong-rate bug is visible in the total.
        ExchangeRate.objects.create(
            currency_code="USD", currency_name="US Dollar",
            buy_rate=Decimal("48.00"), mid_rate=Decimal("49.00"), sell_rate=Decimal("50.00"),
        )
        BalanceEntry.objects.create(owner=self.user, currency=self.usd, title="USD account", amount=Decimal("100"))

    def test_balance_provider_converts_with_buy_rate_not_mid_or_sell(self):
        data = BalanceDataProvider().get_data(self.user)
        item = next(i for i in data["items"] if i["currency"] == "USD")
        self.assertAlmostEqual(item["amount_in_home_currency"], 100 * 48.00, places=2)
        self.assertAlmostEqual(data["summary"]["total_liquid_in_home_currency"], 4800.0, places=2)

    def test_matches_canonical_conversion_service(self):
        # Same figure the Balance page itself would compute — this is the actual regression:
        # the AI's total must agree with the rest of the app, not compute its own rate.
        expected = float(CurrencyConversionService.calculate_exchange_rate("USD", "EGP")) * 100
        item = next(i for i in BalanceDataProvider().get_data(self.user)["items"] if i["currency"] == "USD")
        self.assertAlmostEqual(item["amount_in_home_currency"], expected, places=2)
