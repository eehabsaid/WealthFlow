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

    def test_gold_already_included_in_total_not_addable_again(self):
        """Regression: the AI chat previously added gold_value_in_home_currency to
        total_liquid_in_home_currency a second time, overstating the grand total."""
        summary = BalanceDataProvider().get_data(self.user)["summary"]
        # total = non-gold + gold, i.e. gold is already inside the total exactly once.
        self.assertAlmostEqual(
            summary["non_gold_liquid_in_home_currency"] + summary["gold_value_in_home_currency"],
            summary["total_liquid_in_home_currency"], places=2,
        )
        self.assertAlmostEqual(summary["non_gold_liquid_in_home_currency"], 1000.0, places=2)
        # The wrong, double-counted figure a model previously produced must not equal the total.
        wrong_total = summary["total_liquid_in_home_currency"] + summary["gold_value_in_home_currency"]
        self.assertNotAlmostEqual(wrong_total, summary["total_liquid_in_home_currency"], places=2)
        self.assertIn("double-count", summary["total_liquid_in_home_currency_note"])
        self.assertIn("ALREADY INCLUDED", summary["gold_valuation_note"])
