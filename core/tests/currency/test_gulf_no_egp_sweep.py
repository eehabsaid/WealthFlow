"""A SAR/AED-base user must see no EGP in any JSON their screens read."""
import re

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Currency, ExchangeRate, GoldPrice

User = get_user_model()

# Screens' read endpoints. Not listed: /api/translations/ (static UI text that
# contains the word "EGP" in the Egyptian gold label) and /api/base-currency/.
# 'pivot_currency' (also returned by /api/rates/) is the internal rate-table
# pivot, never displayed, so it is removed before scanning.
ENDPOINTS = [
    "/api/currencies/", "/api/rates/", "/api/gold/", "/api/balance/", "/api/dashboard/summary/",
    "/api/expenses/", "/api/budgets/", "/api/goals/", "/api/banks/", "/api/fixed-assets/",
    "/api/billing/plans/", "/api/billing/status/", "/api/onboarding/status/",
    "/api/per-diems/currencies/",
]
EGP_RE = re.compile(r"EGP|ج\.م")
PIVOT_RE = re.compile(r'"pivot_currency":\s*"[A-Z]*"')


class GulfNoEgpSweepTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gulf_sweep", password="pw-12345-x")
        self.client.force_login(self.user)
        for code, value in (("USD", "52.3"), ("EUR", "59"), ("SAR", "13.94"), ("AED", "14.23")):
            ExchangeRate.objects.create(
                currency_code=code, currency_name=code, buy_rate=Decimal(value),
                sell_rate=Decimal(value), mid_rate=Decimal(value),
            )
        GoldPrice.objects.create(carat_24k=7000, usd_gram_24k=Decimal("134"), usd_per_oz=Decimal("4168"), usd_to_egp=Decimal("52.3"))

    def _sweep(self, code):
        self.client.post("/api/base-currency/", data={"code": code}, content_type="application/json")
        usd = Currency.objects.get(owner=self.user, code="USD")
        BalanceEntry.objects.create(owner=self.user, title="Home Balance", currency=usd, amount=100)
        offenders = []
        for url in ENDPOINTS:
            response = self.client.get(url)
            self.assertLess(response.status_code, 500, url)
            if "json" in response.get("Content-Type", "") and EGP_RE.search(PIVOT_RE.sub("", response.content.decode())):
                offenders.append(url)
        self.assertEqual(offenders, [])

    def test_sar_user(self):
        self._sweep("SAR")

    def test_aed_user(self):
        self._sweep("AED")
