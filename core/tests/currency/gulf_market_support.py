"""Shared fixtures for the Gulf market tests."""


from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import ExchangeRate, GoldPrice


User = get_user_model()

RATES = {"USD": "52.30", "EUR": "59.05", "GBP": "69.12", "SAR": "13.94", "AED": "14.23", "EGP": "1"}


def _codes(response):
    return {row["code"].upper() for row in response.json()["currencies"]}


class GulfMarketBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gulf_user", password="pw-12345-x")
        self.client.force_login(self.user)
        for code, value in RATES.items():
            if code == "EGP":
                continue
            ExchangeRate.objects.create(
                currency_code=code, currency_name=code, buy_rate=Decimal(value),
                sell_rate=Decimal(value), mid_rate=Decimal(value),
            )
        self.gold = GoldPrice.objects.create(
            carat_24k=7000, carat_22k=6400, carat_21k=6125, carat_18k=5250,
            carat_24k_buy=6900, carat_22k_buy=6300, carat_21k_buy=6025, carat_18k_buy=5150,
            usd_gram_24k=Decimal("134.000000"), usd_per_oz=Decimal("4168.0000"),
            usd_to_egp=Decimal("52.300000"),
        )

    def switch(self, code):
        return self.client.post("/api/base-currency/", data={"code": code}, content_type="application/json")
