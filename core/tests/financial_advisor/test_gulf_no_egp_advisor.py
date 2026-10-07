"""A SAR/AED-base user must see no EGP on any Financial Advisor tab, and the
Performance gold history must be spot prices in their own base currency."""
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Currency, ExchangeRate, GoldPrice, GoldPriceHistory

User = get_user_model()
EGP_RE = re.compile(r"EGP|ج\.م")
ADVISOR_TABS = [
    "overview", "cash-flow-forecast", "wealth-growth-forecast", "portfolio-optimizer", "risk-analysis",
    "spending-intelligence", "opportunity-detection", "performance", "what-if-simulator", "goal-planning",
]
USD_GRAM = Decimal("134")


class GulfAdvisorNoEgpTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gulf_advisor", password="pw-12345-x")
        self.client.force_login(self.user)
        for code, value in (("USD", "52.3"), ("EUR", "59"), ("SAR", "13.94"), ("AED", "14.23")):
            ExchangeRate.objects.create(
                currency_code=code, currency_name=code, buy_rate=Decimal(value),
                sell_rate=Decimal(value), mid_rate=Decimal(value),
            )
        GoldPrice.objects.create(carat_24k=7000, usd_gram_24k=USD_GRAM, usd_per_oz=Decimal("4168"), usd_to_egp=Decimal("52.3"))
        for i in range(10):
            GoldPriceHistory.objects.create(
                carat_24k=7000 + i, carat_21k=6125 + i, carat_18k=5250 + i,
                usd_gram_24k=USD_GRAM + i, usd_per_oz=Decimal("4168"), usd_to_egp=Decimal("52.3"),
            )

    def _go_gulf(self, code):
        self.client.post("/api/base-currency/", data={"code": code}, content_type="application/json")
        usd = Currency.objects.get(owner=self.user, code="USD")
        BalanceEntry.objects.create(owner=self.user, title="Home Balance", currency=usd, amount=100)

    def _sweep(self, code):
        self._go_gulf(code)
        offenders = []
        for tab in ADVISOR_TABS:
            response = self.client.get(f"/api/financial-advisor/{tab}/")
            self.assertLess(response.status_code, 500, tab)
            match = EGP_RE.search(response.content.decode())
            if match:
                body = response.content.decode()
                offenders.append((tab, body[max(0, match.start() - 60):match.end() + 40]))
        self.assertEqual(offenders, [])

    def test_sar_user_every_advisor_tab(self):
        self._sweep("SAR")

    def test_aed_user_every_advisor_tab(self):
        self._sweep("AED")

    def test_performance_gold_is_spot_in_base_currency(self):
        self._go_gulf("SAR")
        gold = self.client.get("/api/financial-advisor/performance/").json()["gold"]
        self.assertEqual(gold["currency"], "SAR")
        self.assertEqual(gold["market"], "spot")
        sar_per_usd = Decimal("52.3") / Decimal("13.94")
        # The loop in setUp can stamp several rows with the same coarse clock
        # tick (Windows); the service orders ties by id, so the last row is newest.
        newest = gold["timeseries"][-1]
        self.assertAlmostEqual(newest["carat_24k"], float((USD_GRAM + 9) * sar_per_usd), delta=0.05)
        self.assertAlmostEqual(gold["current_price_24k"], newest["carat_24k"], delta=0.05)

    def test_performance_gold_stays_egp_for_non_gulf_user(self):
        gold = self.client.get("/api/financial-advisor/performance/").json()["gold"]
        self.assertEqual(gold["currency"], "EGP")
        self.assertEqual(gold["market"], "dealer")
        self.assertEqual(gold["current_price_24k"], 7009.0)

    def test_gold_history_rows_with_identical_timestamps_keep_insertion_order(self):
        from django.utils import timezone

        GoldPriceHistory.objects.update(timestamp=timezone.now())
        self._go_gulf("SAR")
        series = self.client.get("/api/financial-advisor/performance/").json()["gold"]["timeseries"]
        prices = [row["carat_24k"] for row in series]
        self.assertEqual(prices, sorted(prices))
        self.assertEqual(series[-1]["carat_24k"], max(prices))
