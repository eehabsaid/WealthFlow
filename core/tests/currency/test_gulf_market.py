"""Gulf market (SAR/AED base): no EGP anywhere, spot gold, safe catalog switch."""



from django.test import TestCase

from core.models import BalanceEntry, Currency, ExchangeRate
from core.reports.excel_sheets_builder.build_balance_sheet.context import resolve_slot_codes
from core.services.shared.market_profile import is_gulf_user
from .gulf_market_support import GulfMarketBase, User, _codes


class CatalogSwitchTests(GulfMarketBase):
    def test_new_user_can_pick_aed_in_the_wizard(self):
        self.assertIn("AED", _codes(self.client.get("/api/currencies/")))
        self.assertEqual(self.client.post("/api/onboarding/complete/", data={"default_currency": "AED"},
                                          content_type="application/json").status_code, 200)
        self.assertEqual(self.client.get("/api/base-currency/").json()["code"], "AED")
        self.assertNotIn("EGP", _codes(self.client.get("/api/currencies/")))

    def test_spot_gold_is_rounded_to_two_decimals(self):
        self.switch("SAR")
        gold = self.client.get("/api/gold/").json()["gold"]
        self.assertEqual(gold["carat_24k"], round(gold["carat_24k"], 2))

    def test_new_user_starts_with_egp(self):
        self.assertIn("EGP", _codes(self.client.get("/api/currencies/")))

    def test_switch_to_aed_builds_gulf_catalog_without_egp(self):
        self.assertEqual(self.switch("AED").status_code, 200)
        codes = _codes(self.client.get("/api/currencies/"))
        self.assertEqual(codes, {"SAR", "AED", "USD", "EUR", "GOLD"})
        self.assertTrue(is_gulf_user(self.user))

    def test_switch_to_sar_has_no_egp(self):
        self.assertEqual(self.switch("SAR").status_code, 200)
        self.assertNotIn("EGP", _codes(self.client.get("/api/currencies/")))

    def test_switch_back_to_egp_restores_the_row(self):
        self.switch("SAR")
        self.assertEqual(self.switch("EGP").status_code, 200)
        self.assertIn("EGP", _codes(self.client.get("/api/currencies/")))
        self.assertFalse(is_gulf_user(self.user))

    def test_used_egp_is_kept_and_its_data_survives(self):
        egp = Currency.objects.get(owner=self.user, code="EGP")
        entry = BalanceEntry.objects.create(owner=self.user, title="Cairo", currency=egp, amount=500)
        self.assertEqual(self.switch("SAR").status_code, 200)
        self.assertTrue(Currency.objects.filter(owner=self.user, code="EGP").exists())
        self.assertTrue(BalanceEntry.objects.filter(pk=entry.pk).exists())

    def test_failed_switch_does_not_touch_the_catalog(self):
        ExchangeRate.objects.filter(currency_code="AED").delete()
        self.assertEqual(self.switch("AED").status_code, 400)
        self.assertIn("EGP", _codes(self.client.get("/api/currencies/")))

    def test_other_users_catalog_is_untouched(self):
        other = User.objects.create_user(username="egy_user", password="pw-12345-x")
        self.switch("AED")
        self.assertTrue(Currency.objects.filter(owner=other, code="EGP").exists())


class BalanceSheetSlotTests(TestCase):
    def test_egp_base_layout_is_unchanged(self):
        self.assertEqual(resolve_slot_codes("EGP"), ("USD", "EUR", "SAR"))

    def test_sar_base_replaces_the_duplicate_sar_column(self):
        self.assertEqual(resolve_slot_codes("SAR", gulf=True), ("USD", "EUR", "AED"))

    def test_usd_base_replaces_the_duplicate_usd_column(self):
        slots = resolve_slot_codes("USD")
        self.assertNotIn("USD", slots)
        self.assertEqual(len(set(slots)), 3)

    def test_eur_base_and_aed_base(self):
        self.assertNotIn("EUR", resolve_slot_codes("EUR"))
        self.assertEqual(resolve_slot_codes("AED", gulf=True), ("USD", "EUR", "SAR"))
