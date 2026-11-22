"""Commitments calendar: analysis rules, forecast-driven events, currency and API/settings behaviour."""

import json
from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AssetSale, BalanceEntry, Bank, BankCertificate, Currency, FixedAsset
from core.services.financial_advisor.commitments_calendar_service import CommitmentsCalendarService, resolve_week_start_day, resolve_window_days
from core.services.financial_advisor.commitments_calendar_service import events as events_module
from core.services.financial_advisor.commitments_calendar_service.event_shape import _make
from core.services.financial_advisor.commitments_calendar_service.liquidity import build_analysis

User = get_user_model()
TODAY = date(2026, 11, 22)
SETTING = "commitments_concentration_window_days"
API = "/api/financial-advisor/commitments-calendar/"


class StubSeries:
    """Minimal stand-in for ForecastSeries so analysis rules are tested in isolation."""

    as_of = "2026-11-22"
    start_cash = 1000.0

    def __init__(self, timeline=None, incomes=()):
        self.timeline = timeline or []
        self._incomes = list(incomes)

    def balance_at(self, d):
        return 1000.0

    def next_income_after(self, d):
        for income in self._incomes:
            if income > d:
                return {"date": income, "amount": 1.0, "type": "salary"}
        return None


def bill(day, amount=100, source_id=1, event_type="recurring"):
    return _make(day, "expense", event_type, "expected", "commitments_event_" + event_type,
                 amount=amount, amount_base=amount, source="RecurringTransaction", source_id=source_id)


class AnalysisRulesTest(TestCase):
    def test_one_monthly_bill_is_not_a_concentration(self):
        # Feb 2 -> Mar 2 is only 28 days apart: the same bill must not raise an alarm.
        events = [bill(date(2027, 1, 2)), bill(date(2027, 2, 2)), bill(date(2027, 3, 2))]
        analysis = build_analysis(events, 30, StubSeries())
        self.assertEqual(analysis["concentration_windows"], [])
        self.assertFalse(any(r["key"] == "commitments_risk_concentration" for r in analysis["risk_reasons"]))

    def test_two_different_commitments_are_a_concentration(self):
        events = [bill(date(2027, 2, 2), 300, 1), bill(date(2027, 2, 10), 200, 2)]
        analysis = build_analysis(events, 30, StubSeries())
        top = analysis["concentration_windows"][0]
        self.assertEqual((top["events"], top["outflow"]), (2, 500.0))

    def test_window_end_is_exclusive(self):
        events = [bill(date(2027, 2, 1), 100, 1), bill(date(2027, 3, 3), 100, 2)]  # 30 days apart
        analysis = build_analysis(events, 30, StubSeries())
        self.assertEqual(analysis["concentration_windows"], [])

    def test_negative_months_and_before_income(self):
        series = StubSeries(timeline=[{"month": "2026-12", "ending_cash": -50}, {"month": "2027-01", "ending_cash": 10}],
                            incomes=[date(2027, 3, 1)])
        analysis = build_analysis([bill(date(2026, 12, 5))], 30, series)
        self.assertEqual(analysis["negative_balance_months"], ["2026-12"])
        keys = [r["key"] for r in analysis["risk_reasons"]]
        self.assertIn("commitments_risk_negative_balance", keys)
        self.assertIn("commitments_risk_before_income", keys)

    def test_projected_balance_and_forecast_flag_on_every_event(self):
        events = [bill(date(2026, 12, 5))]
        build_analysis(events, 30, StubSeries())
        self.assertEqual(events[0]["projected_balance"], 1000.0)
        self.assertFalse(events[0]["included_in_forecast"])  # expected, not an actual forecast event

    def test_highlights_use_renewal_event_types(self):
        renewal = _make(date(2026, 12, 1), "renewal", "vehicle_license_renewal", "informational",
                        "commitments_event_vehicle_license_renewal", amount=10)
        analysis = build_analysis([renewal], 30, StubSeries())
        self.assertEqual(analysis["highlights"][0]["event_type"], "vehicle_license_renewal")


class ForecastDrivenEventsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_fc", password="x12345678")

    def payload(self, series_by_type, start=date(2026, 11, 1), end=date(2027, 1, 31)):
        def fake_series(_self, event_type):
            return series_by_type.get(event_type, [])

        with mock.patch.object(events_module.CommitmentsEventsBuilder, "_series_events", fake_series), \
                mock.patch.object(events_module, "get_current_monthly_salary", return_value=0):
            return CommitmentsCalendarService(self.user, today=TODAY).payload(start, end)

    def test_salary_comes_from_the_forecast_series(self):
        p = self.payload({"salary": [{"date": date(2026, 11, 27), "amount": 10000.0, "type": "salary"}]})
        salary = [e for e in p["events"] if e["event_type"] == "salary"]
        self.assertEqual([(e["date"], e["category"], e["kind"]) for e in salary], [("2026-11-27", "income", "actual")])

    def test_mortgage_fills_every_month_as_an_outflow(self):
        p = self.payload({"mortgage_payment": [{"date": date(2026, 11, 30), "amount": -3000.0, "type": "mortgage_payment"}]})
        rows = [(e["date"], e["amount"]) for e in p["events"] if e["event_type"] == "mortgage"]
        self.assertEqual(rows, [("2026-11-30", 3000.0), ("2026-12-31", 3000.0), ("2027-01-31", 3000.0)])
        self.assertTrue(all(e["category"] == "expense" for e in p["events"] if e["event_type"] == "mortgage"))

    def test_rental_income_is_income(self):
        p = self.payload({"rental_income": [{"date": date(2026, 11, 30), "amount": 5000.0, "type": "rental_income"}]})
        rental = [e for e in p["events"] if e["event_type"] == "rental_income"]
        self.assertEqual(len(rental), 3)
        self.assertTrue(all(e["category"] == "income" and e["amount"] == 5000.0 for e in rental))

    def test_no_series_means_no_forecast_events(self):
        p = self.payload({})
        self.assertFalse([e for e in p["events"] if e["event_type"] in ("salary", "mortgage", "rental_income")])


class CurrencyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_fx", password="x12345678")
        self.bank = Bank.objects.create(owner=self.user, name="FX Bank")
        self.usd = Currency.objects.create(code="USD", symbol="$", name="US Dollar")

    def certificate_events(self):
        BalanceEntry.objects.create(
            owner=self.user, title="USD cash", balance_type=BalanceEntry.BalanceType.CASH,
            currency=self.usd, amount=100000, bank=self.bank,
        )
        BankCertificate.objects.create(
            owner=self.user, bank=self.bank, currency=self.usd, amount=1000, interest_value=10,
            issue_date=date(2026, 1, 15), expiry_date=date(2027, 1, 15), frequency="monthly", status="active",
        )
        with mock.patch("core.services.financial_advisor.commitments_calendar_service.service.get_user_base_code",
                        return_value="EGP"):
            return CommitmentsCalendarService(self.user, today=TODAY)

    def test_foreign_certificate_amounts_are_converted_to_base(self):
        service = self.certificate_events()
        with mock.patch("core.services.financial_advisor.commitments_calendar_service.service.get_user_base_code",
                        return_value="EGP"), \
                mock.patch("core.services.financial_advisor.commitments_calendar_service.service.CurrencyConversionService.strict_rate",
                           return_value=50):
            events = service.payload(date(2026, 12, 1), date(2026, 12, 31))["events"]
        interest = [e for e in events if e["event_type"] == "certificate_interest"]
        self.assertTrue(interest)
        self.assertEqual((interest[0]["amount"], interest[0]["amount_base"]), (10.0, 500.0))

    def test_missing_rate_leaves_base_amount_empty(self):
        service = self.certificate_events()
        with mock.patch("core.services.financial_advisor.commitments_calendar_service.service.get_user_base_code",
                        return_value="EGP"), \
                mock.patch("core.services.financial_advisor.commitments_calendar_service.service.CurrencyConversionService.strict_rate",
                           side_effect=ValueError("no rate")):
            events = service.payload(date(2026, 12, 1), date(2026, 12, 31))["events"]
        interest = [e for e in events if e["event_type"] == "certificate_interest"]
        self.assertIsNone(interest[0]["amount_base"])


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
