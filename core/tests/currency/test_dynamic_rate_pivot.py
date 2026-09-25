from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.models import AppSettings, Currency, ExchangeRate, UserProfile
from core.services.shared.base_currency import get_user_base_info
from core.services.shared.currency_conversion_service import get_rate_pivot_code
from core.services.shared.exchange_rate_service import ExchangeRateService

User = get_user_model()


class DynamicRatePivotTests(TestCase):
    """A6 batch 4: core_exchangerate pivots on whoever's own default
    currency triggered the refresh (open.er-api.com/v6/latest/{base_code}),
    never a fixed EGP or USD pivot."""

    def test_refresh_defaults_to_the_platform_currency_when_no_pivot_given(self):
        with patch(
            "core.integrations.fetch_latest_exchange_rates",
            return_value={"USD": 0.02},
        ) as mocked:
            ExchangeRateService().refresh_latest_rates()
        mocked.assert_called_once_with("EGP")
        self.assertEqual(get_rate_pivot_code(), "EGP")

    def test_refresh_with_explicit_pivot_fetches_and_stores_against_it(self):
        # 1 SAR = 0.2667 USD, 1 SAR = 0.0714 EUR (i.e. quoted with SAR as base)
        with patch(
            "core.integrations.fetch_latest_exchange_rates",
            return_value={"USD": 0.2667, "EUR": 0.0714, "EGP": 3.65},
        ) as mocked:
            ExchangeRateService().refresh_latest_rates("SAR")
        mocked.assert_called_once_with("SAR")
        self.assertEqual(get_rate_pivot_code(), "SAR")
        # SAR itself never gets a row (it's the implicit 1.0 pivot)
        self.assertFalse(ExchangeRate.objects.filter(currency_code="SAR").exists())
        # EGP is no longer the pivot, so it now gets a normal stored row
        egp_row = ExchangeRate.objects.get(currency_code="EGP")
        self.assertAlmostEqual(float(egp_row.mid_rate), 1 / 3.65, places=4)

    def test_get_rate_pivot_code_persists_across_calls_via_appsettings(self):
        with patch("core.integrations.fetch_latest_exchange_rates", return_value={"USD": 0.2667}):
            ExchangeRateService().refresh_latest_rates("SAR")
        self.assertEqual(AppSettings.get("exchange_rate_pivot_code"), "SAR")
        self.assertEqual(get_rate_pivot_code(), "SAR")

    @override_settings(MULTI_CURRENCY_ENABLED=True)
    def test_refresh_view_uses_the_requesting_users_own_base_currency(self):
        user = User.objects.create_user(username="sar_user", password="pw12345")
        Currency.objects.get_or_create(owner=user, code="EGP", defaults={"symbol": "EGP", "name": "EGP", "order": 0})
        Currency.objects.get_or_create(owner=user, code="SAR", defaults={"symbol": "SAR", "name": "SAR", "order": 1})
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13"), sell_rate=Decimal("13"), mid_rate=Decimal("13"))
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.preferred_currency = "SAR"
        profile.save(update_fields=["preferred_currency"])

        self.client.force_login(user)
        with patch(
            "core.integrations.fetch_latest_exchange_rates",
            return_value={"USD": 0.2667},
        ) as mocked:
            response = self.client.post("/api/rates/refresh/")

        self.assertEqual(response.status_code, 200)
        mocked.assert_called_once_with("SAR")
        self.assertEqual(get_rate_pivot_code(), "SAR")

    def test_base_currency_info_reports_the_live_pivot(self):
        with patch("core.integrations.fetch_latest_exchange_rates", return_value={"USD": 0.2667}):
            ExchangeRateService().refresh_latest_rates("SAR")
        self.assertEqual(get_user_base_info(None)["pivot_currency"], "SAR")
