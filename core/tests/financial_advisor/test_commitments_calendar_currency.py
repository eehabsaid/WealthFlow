"""Commitments calendar: concentration never adds amounts of different currencies."""

from datetime import date

from django.test import SimpleTestCase

from core.services.financial_advisor.commitments_calendar_service.event_shape import _make
from core.services.financial_advisor.commitments_calendar_service.liquidity import build_analysis
from core.tests.financial_advisor.test_commitments_calendar_logic import StubSeries

BASE = "EGP"


def bill(day, source_id, amount, amount_base, currency):
    return _make(day, "expense", "recurring", "expected", "commitments_event_recurring", amount=amount,
                 amount_base=amount_base, currency_code=currency, source="RecurringTransaction", source_id=source_id)


def analyse(events):
    return build_analysis(events, 30, StubSeries(), BASE)


class ConcentrationCurrencyTest(SimpleTestCase):
    def test_mixed_currencies_with_one_missing_base_amount_is_excluded_and_flagged(self):
        events = [bill(date(2027, 1, 5), 1, 100, 100, "EGP"),
                  bill(date(2027, 1, 10), 2, 200, 400, "USD"),
                  bill(date(2027, 1, 15), 3, 500, None, "EUR")]
        a = analyse(events)
        top = a["concentration_windows"][0]
        self.assertEqual((top["outflow"], top["events"]), (500.0, 2))  # the 500 EUR is NOT added
        self.assertTrue(a["concentration_incomplete"])
        self.assertEqual(a["unconverted_count"], 1)
        self.assertEqual(a["unconverted_currencies"], ["EUR"])

    def test_all_convertible_is_unchanged(self):
        events = [bill(date(2027, 1, 5), 1, 100, 100, "EGP"), bill(date(2027, 1, 10), 2, 200, 400, "USD")]
        a = analyse(events)
        self.assertEqual(a["concentration_windows"][0]["outflow"], 500.0)
        self.assertFalse(a["concentration_incomplete"])
        self.assertEqual(a["unconverted_count"], 0)
        self.assertTrue(any(r["key"] == "commitments_risk_concentration" for r in a["risk_reasons"]))

    def test_all_unconvertible_gives_no_alert_and_incomplete_flag(self):
        events = [bill(date(2027, 1, 5), 1, 100, None, "USD"), bill(date(2027, 1, 10), 2, 300, None, "EUR")]
        a = analyse(events)
        self.assertEqual(a["concentration_windows"], [])
        self.assertFalse(any(r["key"] == "commitments_risk_concentration" for r in a["risk_reasons"]))
        self.assertTrue(a["concentration_incomplete"])
        self.assertEqual(a["unconverted_currencies"], ["EUR", "USD"])

    def test_base_currency_amount_without_amount_base_is_still_counted(self):
        events = [bill(date(2027, 1, 5), 1, 100, None, "egp"), bill(date(2027, 1, 10), 2, 250, 250, "EGP")]
        a = analyse(events)
        self.assertEqual(a["concentration_windows"][0]["outflow"], 350.0)
        self.assertFalse(a["concentration_incomplete"])
