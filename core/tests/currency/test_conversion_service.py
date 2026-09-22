from decimal import Decimal

from django.test import TestCase

from core.models import ExchangeRate
from core.services.shared.currency_conversion_service import (
    RATE_PIVOT,
    CurrencyConversionService,
)


class LatestBuyRateTests(TestCase):
    def test_pivot_currency_is_always_one(self):
        self.assertEqual(CurrencyConversionService.get_latest_buy_rate(RATE_PIVOT), Decimal("1.000000"))

    def test_unknown_currency_falls_back_to_one(self):
        self.assertEqual(CurrencyConversionService.get_latest_buy_rate("XYZ"), Decimal("1.000000"))

    def test_uses_most_recent_stored_rate(self):
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13.10"), sell_rate=Decimal("13.20"), mid_rate=Decimal("13.15"))
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13.50"), sell_rate=Decimal("13.60"), mid_rate=Decimal("13.55"))
        self.assertEqual(CurrencyConversionService.get_latest_buy_rate("SAR"), Decimal("13.50"))

    def test_target_date_filters_to_rates_fetched_on_or_before_it(self):
        import datetime

        from django.utils import timezone

        old = ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13.00"), sell_rate=Decimal("13.00"), mid_rate=Decimal("13.00"))
        old.fetched_at = timezone.make_aware(datetime.datetime(2026, 1, 1))
        old.save(update_fields=["fetched_at"])
        new = ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("14.00"), sell_rate=Decimal("14.00"), mid_rate=Decimal("14.00"))
        new.fetched_at = timezone.make_aware(datetime.datetime(2026, 6, 1))
        new.save(update_fields=["fetched_at"])
        self.assertEqual(
            CurrencyConversionService.get_latest_buy_rate("SAR", target_date=datetime.date(2026, 3, 1)),
            Decimal("13.00"),
        )


class RatesToBaseTests(TestCase):
    def setUp(self):
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13.00"), sell_rate=Decimal("13.00"), mid_rate=Decimal("13.00"))
        ExchangeRate.objects.create(currency_code="USD", buy_rate=Decimal("49.00"), sell_rate=Decimal("49.00"), mid_rate=Decimal("49.00"))

    def test_base_is_always_one(self):
        rates = CurrencyConversionService.get_rates_to_base("SAR")
        self.assertEqual(rates["SAR"], Decimal("1.000000"))

    def test_other_currencies_expressed_relative_to_base(self):
        # 1 USD = 49 EGP, 1 SAR = 13 EGP -> 1 USD = 49/13 SAR
        rates = CurrencyConversionService.get_rates_to_base("SAR")
        self.assertEqual(rates["USD"], (Decimal("49.00") / Decimal("13.00")).quantize(Decimal("0.000001")))

    def test_pivot_is_included_when_base_is_not_the_pivot(self):
        rates = CurrencyConversionService.get_rates_to_base("SAR")
        self.assertIn(RATE_PIVOT, rates)

    def test_base_without_a_stored_rate_returns_itself_only(self):
        rates = CurrencyConversionService.get_rates_to_base("XYZ")
        self.assertEqual(rates, {"XYZ": Decimal("1.000000")})


class StrictRateTests(TestCase):
    def test_same_currency_is_always_one_even_without_a_rate(self):
        self.assertEqual(CurrencyConversionService.strict_rate("SAR", "SAR"), Decimal("1.000000"))

    def test_missing_rate_raises(self):
        with self.assertRaises(ValueError):
            CurrencyConversionService.strict_rate("SAR", RATE_PIVOT)

    def test_pivot_never_needs_a_stored_rate(self):
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13.00"), sell_rate=Decimal("13.00"), mid_rate=Decimal("13.00"))
        expected = CurrencyConversionService.calculate_exchange_rate(RATE_PIVOT, "SAR")
        self.assertEqual(CurrencyConversionService.strict_rate(RATE_PIVOT, "SAR"), expected)


class ConvertAmountTests(TestCase):
    def setUp(self):
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13.00"), sell_rate=Decimal("13.00"), mid_rate=Decimal("13.00"))

    def test_converts_using_the_system_rate(self):
        rate, converted = CurrencyConversionService.convert_amount(Decimal("100"), RATE_PIVOT, "SAR")
        self.assertEqual(converted, Decimal("7.69"))  # 100 / 13, rounded to cents

    def test_custom_rate_overrides_the_system_rate(self):
        rate, converted = CurrencyConversionService.convert_amount(Decimal("100"), RATE_PIVOT, "SAR", custom_rate=Decimal("10"))
        self.assertEqual(rate, Decimal("10.000000"))
        self.assertEqual(converted, Decimal("1000.00"))

    def test_zero_or_none_amount_converts_to_zero(self):
        _, converted = CurrencyConversionService.convert_amount(None, RATE_PIVOT, "SAR")
        self.assertEqual(converted, Decimal("0.00"))
