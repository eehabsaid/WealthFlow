"""Commitments calendar: currency, API/settings behaviour, asset sales, first day of the week."""

import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AssetSale, BalanceEntry, Bank, BankCertificate, Currency, ExchangeRate, FixedAsset
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.commitments_calendar_service import CommitmentsCalendarService, resolve_week_start_day, resolve_window_days

User = get_user_model()
TODAY = date(2026, 11, 22)
SETTING = "commitments_concentration_window_days"
API = "/api/financial-advisor/commitments-calendar/"


class CurrencyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_fx", password="x12345678")
        self.bank = Bank.objects.create(owner=self.user, name="FX Bank")
        self.usd = Currency.objects.create(code="USD", symbol="$", name="US Dollar")

    def calendar_for_usd_certificate(self, with_rate=True):
        if with_rate:
            ExchangeRate.objects.create(currency_code="USD", buy_rate=50, sell_rate=50, mid_rate=50)
        BalanceEntry.objects.create(
            owner=self.user, title="USD cash", balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.usd, amount=100000, bank=self.bank,
        )
        BankCertificate.objects.create(
            owner=self.user, bank=self.bank, currency=self.usd, amount=1000, interest_value=10,
            issue_date=date(2026, 1, 15), expiry_date=date(2027, 1, 15), frequency="monthly", status="active",
        )
        return CommitmentsCalendarService(self.user, today=TODAY).payload(date(2026, 12, 1), date(2026, 12, 31))["events"]

    def test_foreign_certificate_amounts_are_converted_to_base(self):
        interest = [e for e in self.calendar_for_usd_certificate() if e["event_type"] == "certificate_interest"]
        self.assertTrue(interest)
        self.assertEqual((interest[0]["amount"], interest[0]["currency_code"], interest[0]["amount_base"]),
                         (10.0, "USD", 500.0))

    def test_certificate_without_a_stored_rate_is_omitted_like_the_forecast(self):
        events = self.calendar_for_usd_certificate(with_rate=False)
        self.assertEqual([e for e in events if e["event_type"].startswith("certificate_")], [])
        forecast = CashFlowForecastService(self.user, today=TODAY).payload()
        self.assertFalse(any(ev["type"].startswith("certificate_") for m in forecast["timeline"] for ev in m["events"]))


class ApiAndSettingsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_set", password="x12345678")
        self.other = User.objects.create_user(username="cc_set2", password="x12345678")
        self.client.login(username="cc_set", password="x12345678")
        self.own_bank = Bank.objects.create(owner=self.user, name="Own")
        self.foreign_bank = Bank.objects.create(owner=self.other, name="Foreign")

    def get(self, **extra):
        return self.client.get(API, {"start_date": "2026-11-01", "end_date": "2026-12-31", **extra})

    def save_setting(self, value):
        return self.client.post("/api/settings/", data=json.dumps({"key": SETTING, "value": value}),
                                content_type="application/json")

    def test_own_bank_filter_is_accepted(self):
        self.assertEqual(self.get(bank=self.own_bank.id).status_code, 200)

    def test_other_users_bank_is_rejected(self):
        self.assertEqual(self.get(bank=self.foreign_bank.id).status_code, 400)

    def test_non_numeric_bank_is_rejected(self):
        self.assertEqual(self.get(bank="abc").status_code, 400)

    def test_range_longer_than_a_year_is_rejected(self):
        r = self.client.get(API, {"start_date": "2026-01-01", "end_date": "2027-01-03"})
        self.assertEqual(r.status_code, 400)

    def test_window_setting_rejects_invalid_values(self):
        for bad in ("0", "91", "-5", "abc", ""):
            self.assertEqual(self.save_setting(bad).status_code, 400, bad)
        self.assertEqual(resolve_window_days(self.user), 30)  # nothing invalid was stored

    def test_window_setting_is_saved_and_used_per_user(self):
        self.assertEqual(self.save_setting("45").status_code, 200)
        self.assertEqual(self.get().json()["settings"]["concentration_window_days"], 45)
        self.client.logout()
        self.client.login(username="cc_set2", password="x12345678")
        self.assertEqual(self.get().json()["settings"]["concentration_window_days"], 30)


class AssetSaleEventsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_sale", password="x12345678")
        self.other = User.objects.create_user(username="cc_sale2", password="x12345678")

    def sale(self, owner, name, day, net):
        asset = FixedAsset.objects.create(owner=owner, name=name, asset_type="Other Assets",
                                          purchase_date=date(2025, 1, 1))
        return AssetSale.objects.create(asset=asset, sale_date=day, sale_price=net, selling_expenses=0,
                                        net_sale_amount=net)

    def events(self, start, end):
        payload = CommitmentsCalendarService(self.user, today=TODAY).payload(start, end)
        return [e for e in payload["events"] if e["event_type"] == "asset_sale"]

    def test_sale_in_range_is_actual_income_with_net_amount(self):
        sale = self.sale(self.user, "Car", date(2026, 12, 10), 250000)
        rows = self.events(date(2026, 11, 1), date(2026, 12, 31))
        self.assertEqual([(e["date"], e["category"], e["kind"], e["amount"], e["source_id"]) for e in rows],
                         [("2026-12-10", "income", "actual", 250000.0, sale.id)])

    def test_sale_outside_range_zero_net_and_other_user_are_excluded(self):
        self.sale(self.user, "Late", date(2027, 6, 1), 1000)
        self.sale(self.user, "Free", date(2026, 12, 12), 0)
        self.sale(self.other, "Foreign", date(2026, 12, 15), 5000)
        self.assertEqual(self.events(date(2026, 11, 1), date(2026, 12, 31)), [])


class WeekStartSettingTest(TestCase):
    KEY = "commitments_week_start_day"

    def setUp(self):
        self.user = User.objects.create_user(username="cc_ws", password="x12345678")
        self.other = User.objects.create_user(username="cc_ws2", password="x12345678")
        self.client.login(username="cc_ws", password="x12345678")

    def save(self, value):
        return self.client.post("/api/settings/", data=json.dumps({"key": self.KEY, "value": value}),
                                content_type="application/json")

    def test_default_is_sunday(self):
        self.assertEqual(resolve_week_start_day(self.user), 0)
        r = self.client.get(API, {"start_date": "2026-11-01", "end_date": "2026-12-31"})
        self.assertEqual(r.json()["settings"]["week_start_day"], 0)

    def test_valid_values_are_saved_and_returned(self):
        for day in ("0", "1", "6"):
            self.assertEqual(self.save(day).status_code, 200, day)
            r = self.client.get(API, {"start_date": "2026-11-01", "end_date": "2026-12-31"})
            self.assertEqual(r.json()["settings"]["week_start_day"], int(day))

    def test_invalid_values_are_rejected(self):
        for bad in ("7", "-1", "abc", ""):
            self.assertEqual(self.save(bad).status_code, 400, bad)
        self.assertEqual(resolve_week_start_day(self.user), 0)

    def test_setting_is_per_user(self):
        self.save("6")
        self.assertEqual(resolve_week_start_day(self.user), 6)
        self.assertEqual(resolve_week_start_day(self.other), 0)
