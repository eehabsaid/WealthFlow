from decimal import Decimal

from django.test import TestCase

from core.models import ExchangeRate
from core.services.shared.currency_conversion_service import CurrencyConversionService as Conv


class RatesToBaseTests(TestCase):
    def setUp(self):
        # Stored rates are quoted per unit in the pivot currency: 1 USD = 50, 1 SAR = 13.
        ExchangeRate.objects.create(currency_code="USD", buy_rate=Decimal("50"), sell_rate=Decimal("50"), mid_rate=Decimal("50"))
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13"), sell_rate=Decimal("13"), mid_rate=Decimal("13"))

    def test_pivot_base_is_unchanged(self):
        rates = Conv.get_rates_to_base("EGP")
        self.assertEqual(rates["EGP"], Decimal("1"))
        self.assertEqual(rates["USD"], Decimal("50"))

    def test_other_base_uses_cross_rates(self):
        rates = Conv.get_rates_to_base("sar")
        self.assertEqual(rates["SAR"], Decimal("1"))
        self.assertAlmostEqual(float(rates["USD"]), 50 / 13, places=5)
        self.assertAlmostEqual(float(rates["EGP"]), 1 / 13, places=5)

    def test_base_without_a_rate_is_not_silently_treated_as_one(self):
        self.assertEqual(Conv.get_rates_to_base("JPY"), {"JPY": Decimal("1.000000")})
