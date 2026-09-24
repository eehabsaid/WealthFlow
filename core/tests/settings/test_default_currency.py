import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from decimal import Decimal

from core.models import AppSettings, Currency, ExchangeRate, UserProfile
from core.services.onboarding import OnboardingService
from core.services.shared.base_currency import (
    PLATFORM_FALLBACK_CURRENCY,
    get_user_base_code,
    get_user_base_info,
)

User = get_user_model()


def _catalog(user, *codes):
    for order, code in enumerate(codes):
        Currency.objects.get_or_create(
            owner=user, code=code, defaults={"symbol": code, "name": code, "order": order}
        )


class DefaultCurrencyResolutionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cur_user", password="pw12345")

    def test_falls_back_to_platform_default(self):
        UserProfile.objects.filter(user=self.user).update(preferred_currency="")  # un-pin
        self.assertEqual(get_user_base_code(self.user), PLATFORM_FALLBACK_CURRENCY)

    def test_platform_setting_is_used_before_the_constant(self):
        UserProfile.objects.filter(user=self.user).update(preferred_currency="")  # un-pin
        AppSettings.set("home_currency", "SAR")
        self.assertEqual(get_user_base_code(self.user), "SAR")

    def test_user_choice_wins(self):
        AppSettings.set("home_currency", "SAR")
        profile = self.user.profile
        profile.preferred_currency = "aed"
        profile.save()
        self.assertEqual(get_user_base_code(self.user), "AED")

    def test_info_uses_the_users_own_catalog(self):
        _catalog(self.user, "EGP")
        Currency.objects.filter(owner=self.user, code="EGP").update(symbol="ج.م")
        info = get_user_base_info(self.user)
        self.assertEqual((info["code"], info["symbol"]), ("EGP", "ج.م"))


class DefaultCurrencyApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cur_api", password="pw12345")
        self.other = User.objects.create_user(username="cur_other", password="pw12345")
        _catalog(self.user, "EGP", "SAR")
        _catalog(self.other, "EGP", "JPY")
        ExchangeRate.objects.create(currency_code="SAR", buy_rate=Decimal("13"), sell_rate=Decimal("13"), mid_rate=Decimal("13"))
        self.client = Client()
        self.client.force_login(self.user)

    def _set(self, code):
        return self.client.post("/api/base-currency/", data=json.dumps({"code": code}), content_type="application/json")

    @override_settings(MULTI_CURRENCY_ENABLED=False)
    def test_get_returns_default(self):
        body = self.client.get("/api/base-currency/").json()
        self.assertEqual(body["code"], "EGP")
        self.assertFalse(body["multi_currency_enabled"])

    @override_settings(MULTI_CURRENCY_ENABLED=False)
    def test_other_currency_is_locked_until_enabled(self):
        response = self._set("SAR")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_key"], "currency_default_unavailable")
        self.assertEqual(get_user_base_code(self.user), "EGP")
        self.assertEqual(self._set("EGP").status_code, 200)

    @override_settings(MULTI_CURRENCY_ENABLED=True)
    def test_change_when_enabled_and_persists(self):
        self.assertEqual(self._set("sar").status_code, 200)
        self.assertEqual(get_user_base_code(self.user), "SAR")
        self.assertEqual(self.client.get("/api/base-currency/").json()["code"], "SAR")
        rows = self.client.get("/api/currencies/").json()
        defaults = [r["code"] for r in rows["currencies"] if r["is_default"]]
        self.assertEqual(defaults, ["SAR"])
        self.assertEqual(rows["default_code"], "SAR")

    @override_settings(MULTI_CURRENCY_ENABLED=True)
    def test_cannot_use_another_users_currency_or_unknown_code(self):
        self.assertEqual(self._set("JPY").status_code, 400)
        self.assertEqual(self._set("").status_code, 400)
        self.assertEqual(get_user_base_code(self.user), "EGP")

    @override_settings(MULTI_CURRENCY_ENABLED=True)
    def test_gold_pseudo_currency_is_never_a_default(self):
        _catalog(self.user, "Gold")
        self.assertEqual(self._set("Gold").status_code, 400)
        rows = {r["code"]: r["can_be_default"] for r in self.client.get("/api/currencies/").json()["currencies"]}
        self.assertFalse(rows["Gold"])
        self.assertTrue(rows["SAR"])

    @override_settings(MULTI_CURRENCY_ENABLED=True)
    def test_currency_without_a_market_rate_is_refused(self):
        _catalog(self.user, "AED")
        response = self._set("AED")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_key"], "currency_default_no_rate")

    def test_new_users_are_pinned_to_the_platform_default(self):
        AppSettings.set("home_currency", "SAR")
        fresh = User.objects.create_user(username="cur_fresh", password="pw12345")
        AppSettings.set("home_currency", "USD")
        self.assertEqual(UserProfile.objects.get(user=fresh).preferred_currency, "SAR")
        self.assertEqual(get_user_base_code(fresh), "SAR")

    def test_default_currency_cannot_be_deleted_or_renamed(self):
        egp = Currency.objects.get(owner=self.user, code="EGP")
        sar = Currency.objects.get(owner=self.user, code="SAR")
        self.assertEqual(self.client.delete(f"/api/currencies/{egp.id}/").status_code, 409)
        renamed = self.client.put(
            f"/api/currencies/{egp.id}/", data=json.dumps({"code": "XXX"}), content_type="application/json"
        )
        self.assertEqual(renamed.status_code, 409)
        self.assertEqual(self.client.delete(f"/api/currencies/{sar.id}/").status_code, 200)

    @override_settings(MULTI_CURRENCY_ENABLED=True)
    def test_wizard_sets_default_currency(self):
        status = OnboardingService.status(self.user)
        self.assertEqual(status["default_currency"], "EGP")
        self.assertTrue(status["multi_currency_enabled"])
        OnboardingService.complete(self.user, {"default_currency": "SAR", "categories": []})
        self.assertEqual(get_user_base_code(self.user), "SAR")

    @override_settings(MULTI_CURRENCY_ENABLED=False)
    def test_wizard_cannot_pick_locked_currency(self):
        with self.assertRaises(ValueError):
            OnboardingService.complete(self.user, {"default_currency": "SAR", "categories": []})
