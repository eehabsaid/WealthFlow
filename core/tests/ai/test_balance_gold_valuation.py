"""AI balance provider values GOLD entries like the Balance page (sell price + cashback per gram)."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import BalanceEntry, Currency, GoldPrice, GoldPuritySetting
from core.services.ai.providers.balance_provider import BalanceDataProvider

User = get_user_model()


class BalanceGoldValuationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gold_ai", password="pw12345")
        self.egp = Currency.objects.get_or_create(code="EGP", owner=self.user, defaults={"name": "Egyptian Pound", "symbol": "EGP"})[0]
        self.gold = Currency.objects.get_or_create(code="GOLD", owner=self.user, defaults={"name": "Gold", "symbol": "g"})[0]
        GoldPrice.objects.create(carat_24k=Decimal("6000"), carat_21k=Decimal("5250"))
        GoldPuritySetting.objects.update_or_create(
            owner=self.user, key="24k", defaults={"label": "24K", "cashback_per_gram": Decimal("50"), "is_active": True}
        )
        BalanceEntry.objects.create(owner=self.user, currency=self.egp, title="Cash", amount=Decimal("1000"))
        BalanceEntry.objects.create(
            owner=self.user, currency=self.gold, title="Gold 24K", purity="24K",
            balance_type="gold", amount=Decimal("10"),
        )

    def test_gold_valued_per_gram_with_cashback(self):
        data = BalanceDataProvider().get_data(self.user)
        item = next(i for i in data["items"] if i["currency"] == "GOLD")
        self.assertEqual(item["gold_grams"], 10.0)
        self.assertAlmostEqual(item["amount_in_home_currency"], 10 * (6000 + 50), places=2)
        self.assertAlmostEqual(data["summary"]["gold_value_in_home_currency"], 60500.0, places=2)
        self.assertAlmostEqual(data["summary"]["total_liquid_in_home_currency"], 61500.0, places=2)
