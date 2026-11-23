"""Calendar payload replayed against a REAL ForecastSeries / CashFlowForecastService payload (no stubs)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import (
    AssetMortgage, AssetRental, AssetSale, BalanceEntry, Bank, BankCertificate, Company, Currency,
    ExchangeRate, FixedAsset, RecurringTransaction,
)
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.commitments_calendar_service import CommitmentsCalendarService

from .commitments_calendar_helpers import END, START, TODAY, calendar_view, forecast_view

User = get_user_model()
# calendar event_type -> (forecast type, sign of the forecast amount)
MAPPED = {"salary": ("salary", 1), "rental_income": ("rental_income", 1),
          "mortgage": ("mortgage_payment", -1), "asset_sale": ("asset_sale", 1)}


class ForecastReplayTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc_replay", password="x12345678")
        self.egp = Currency.objects.create(code="EGP", symbol="E", name="Egyptian Pound")
        self.usd = Currency.objects.create(code="USD", symbol="$", name="US Dollar")
        ExchangeRate.objects.create(currency_code="USD", buy_rate=50, sell_rate=50, mid_rate=50)
        self.bank = Bank.objects.create(owner=self.user, name="Replay Bank")
        for cur, amount in ((self.egp, 5000000), (self.usd, 100000)):
            BalanceEntry.objects.create(owner=self.user, title=f"{cur.code} cash", balance_type=BalanceEntry.BalanceType.CASH,
                                        currency=cur, amount=amount, bank=self.bank)
        Company.objects.create(owner=self.user, name="Acme", display_name="Acme", is_active=True,
                               current_salary_amount=20000, current_salary_currency=self.egp)
        home = FixedAsset.objects.create(owner=self.user, name="Flat", asset_type="Real Estate", status="Owned",
                                         purchase_date=date(2025, 1, 1), purchase_price=500000, current_market_value=600000)
        AssetRental.objects.create(asset=home, monthly_rent=3000, occupancy_rate=100, contract_start=date(2026, 1, 1), contract_end=date(2028, 1, 1))
        AssetMortgage.objects.create(asset=home, loan_amount=300000, remaining_balance=240000, monthly_installment=5000,
                                     interest_rate=8.5, start_date=date(2026, 1, 1))
        car = FixedAsset.objects.create(owner=self.user, name="Car", asset_type="Other Assets", purchase_date=date(2025, 1, 1))
        AssetSale.objects.create(asset=car, sale_date=date(2027, 1, 20), sale_price=60000, selling_expenses=10000, net_sale_amount=50000)
        BankCertificate.objects.create(owner=self.user, bank=self.bank, currency=self.egp, amount=100000, interest_value=1000,
                                       issue_date=date(2026, 6, 10), expiry_date=date(2027, 2, 10), frequency="monthly", status="active")
        BankCertificate.objects.create(owner=self.user, bank=self.bank, currency=self.usd, amount=2000, interest_value=20,
                                       issue_date=date(2026, 3, 5), expiry_date=date(2027, 9, 5), frequency="quarterly", status="active")
        RecurringTransaction.objects.create(owner=self.user, name="Internet", amount=500, currency=self.egp, frequency="monthly",
                                            interval=1, start_date=date(2026, 11, 5), next_run_date=date(2026, 12, 5))
        RecurringTransaction.objects.create(owner=self.user, name="Cloud", amount=10, currency=self.usd, frequency="monthly",
                                            interval=1, start_date=date(2026, 11, 8), next_run_date=date(2026, 12, 8))
        self.calendar = CommitmentsCalendarService(self.user, today=TODAY).payload(START, END)
        self.forecast = CashFlowForecastService(self.user, today=TODAY).payload()
        self.forecast_events = [(ev["date"], ev["type"], ev["amount"]) for m in self.forecast["timeline"] for ev in m["events"]]

    def by_type(self, event_type):
        return [e for e in self.calendar["events"] if e["event_type"] == event_type]

    def test_forecast_derived_events_equal_the_forecast(self):
        for cal_type, (fc_type, sign) in MAPPED.items():
            calendar = sorted((e["date"], round(e["amount_base"] * sign, 2)) for e in self.by_type(cal_type))
            forecast = sorted((d, a) for d, t, a in self.forecast_events if t == fc_type and START.isoformat() <= d <= END.isoformat())
            self.assertTrue(calendar, cal_type)
            self.assertEqual(calendar, forecast, cal_type)

    def test_certificate_events_equal_the_forecast_including_a_foreign_currency_one(self):
        events = [e for e in self.calendar["events"] if e["event_type"].startswith("certificate_")]
        self.assertTrue({"EGP", "USD"} <= {e["currency_code"] for e in events})
        self.assertEqual(calendar_view(events), forecast_view(self.user))

    def test_foreign_amounts_keep_their_currency_and_convert_like_the_forecast(self):
        usd_interest = [e for e in self.by_type("certificate_interest") if e["currency_code"] == "USD"]
        self.assertTrue(usd_interest)
        self.assertEqual({(e["amount"], e["amount_base"]) for e in usd_interest}, {(20.0, 1000.0)})
        usd_maturity = [e for e in self.by_type("certificate_maturity") if e["currency_code"] == "USD"]
        self.assertEqual([(e["amount"], e["amount_base"]) for e in usd_maturity], [(2020.0, 101000.0)])
        cloud = [e for e in self.by_type("recurring") if e["currency_code"] == "USD"]
        self.assertEqual({(e["amount"], e["amount_base"]) for e in cloud}, {(10.0, 500.0)})

    def test_projected_balances_equal_the_forecast_running_cash(self):
        start_cash = self.forecast["checkpoints"]["current"]
        self.assertAlmostEqual(self.calendar["analysis"]["series_start_cash"], start_cash, places=2)
        checked = 0
        for e in self.calendar["events"]:
            expected = start_cash + sum(a for d, _t, a in self.forecast_events if d <= e["date"])
            self.assertAlmostEqual(e["projected_balance"], expected, places=2, msg=f'{e["date"]} {e["event_type"]}')
            checked += 1
        self.assertGreater(checked, 10)

    def test_recurring_bills_are_expected_and_do_not_move_the_forecast_balance(self):
        recurring = self.by_type("recurring")
        self.assertTrue(recurring)
        self.assertFalse(any(e["included_in_forecast"] for e in recurring))
        self.assertNotIn("recurring", {t for _d, t, _a in self.forecast_events})
