from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Currency, ExchangeRate, UserProfile
from core.services.fixed_assets.usd_rate_service import UsdRateError, UsdRateService


class UsdRateServiceTests(TestCase):
    """Regression coverage for get_rate_for_currency().

    The rate is always "units of the purchase currency per 1 USD" —
    uniform across every currency, including whichever currency the
    exchange-rate table currently happens to be pivoted on (dynamic since
    A6 batch 4 — see currency_conversion_service.get_rate_pivot_code() /
    ExchangeRateService.CURRENCY_NAMES; the pivot currency never has its
    own row). In these tests that's still EGP by default (no AppSettings
    override), so the historical examples below are unaffected.
    Two real bugs this guards against:
      1. EGP used to be compared against the user's own base currency
         instead of the fixed pivot, which crashed for any user whose
         base currency isn't EGP (e.g. USD) with a 502.
      2. Every currency other than EGP/USD used to return the *inverse*
         convention ("1 unit of currency is worth this many USD"), which
         is fine for the General tab's own division-only-for-EGP
         handling, but Acquisition Cost / Furniture / Renovation rows
         always divide by this rate uniformly — so any purchase currency
         other than EGP or USD produced wildly wrong USD totals there.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="rate_tester", password="x")
        # create_user auto-seeds EGP/USD/Gold for a new account; add the rest.
        for code in ("SAR", "EUR"):
            Currency.objects.get_or_create(owner=self.user, code=code, defaults={"name": code, "symbol": code})
        ExchangeRate.objects.create(currency_code="USD", currency_name="US Dollar", buy_rate=Decimal("48.30"), sell_rate=Decimal("48.60"), mid_rate=Decimal("48.45"))
        ExchangeRate.objects.create(currency_code="SAR", currency_name="Saudi Riyal", buy_rate=Decimal("12.90"), sell_rate=Decimal("12.96"), mid_rate=Decimal("12.93"))
        ExchangeRate.objects.create(currency_code="EUR", currency_name="Euro", buy_rate=Decimal("52.30"), sell_rate=Decimal("52.60"), mid_rate=Decimal("52.45"))

    def _currency_id(self, code):
        return Currency.objects.get(owner=self.user, code=code).id

    def test_egp_returns_implicit_rate_when_base_currency_is_egp(self):
        UserProfile.objects.update_or_create(user=self.user, defaults={"preferred_currency": "EGP"})
        rate = UsdRateService().get_rate_for_currency(self._currency_id("EGP"))
        self.assertEqual(rate.rate, 48.3)

    def test_egp_returns_implicit_rate_when_base_currency_is_not_egp(self):
        # The 502 regression: base currency USD must not affect EGP's
        # rate, since EGP is the table's structural pivot regardless of
        # any given user's own base currency.
        UserProfile.objects.update_or_create(user=self.user, defaults={"preferred_currency": "USD"})
        rate = UsdRateService().get_rate_for_currency(self._currency_id("EGP"))
        self.assertEqual(rate.rate, 48.3)

    def test_sar_is_units_of_sar_per_usd_not_the_inverse(self):
        # The convention regression: this must be ~3.75 (SAR per USD),
        # not ~0.267 (USD per SAR) — dividing an amount by 0.267 rather
        # than 3.75 is exactly what silently inflated Acquisition/
        # Furniture/Renovation USD totals for any non-EGP currency.
        rate = UsdRateService().get_rate_for_currency(self._currency_id("SAR"))
        self.assertAlmostEqual(rate.rate, 48.30 / 12.90, places=5)
        self.assertGreater(rate.rate, 1)

    def test_eur_ratio_unaffected_by_base_currency(self):
        UserProfile.objects.update_or_create(user=self.user, defaults={"preferred_currency": "USD"})
        rate = UsdRateService().get_rate_for_currency(self._currency_id("EUR"))
        self.assertAlmostEqual(rate.rate, 48.30 / 52.30, places=5)

    def test_usd_is_always_one(self):
        rate = UsdRateService().get_rate_for_currency(self._currency_id("USD"))
        self.assertEqual(rate.rate, 1.0)

    def test_missing_usd_rate_raises(self):
        ExchangeRate.objects.all().delete()
        with self.assertRaises(UsdRateError):
            UsdRateService().get_rate_for_currency(self._currency_id("EGP"))

    def test_amount_divided_by_rate_gives_correct_usd_for_every_currency(self):
        # End-to-end sanity check matching how every consumer (General tab,
        # Acquisition Cost, Furniture, Renovation) uses this rate.
        egp_rate = UsdRateService().get_rate_for_currency(self._currency_id("EGP")).rate
        sar_rate = UsdRateService().get_rate_for_currency(self._currency_id("SAR")).rate
        self.assertAlmostEqual(4830 / egp_rate, 100.0, places=2)
        self.assertAlmostEqual(375 / sar_rate, 100.0, delta=0.5)
