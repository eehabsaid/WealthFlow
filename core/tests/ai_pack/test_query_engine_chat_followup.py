"""Query engine chat tests: realistic volume and gold holdings follow-ups."""


import time
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from ai.integrations.ai_provider import OllamaProvider
from core.models import Expense, ExpenseCategory


import core.tests.ai_pack.qe_fixtures as fx
from .query_engine_chat_support import NO_LLM


class RealisticVolumeTests(TestCase):
    N = 4000

    def setUp(self):
        fx.build(self)
        cats = [ExpenseCategory.objects.create(owner=self.user, name=f"Cat{i}") for i in range(15)]
        rows = [Expense(owner=self.user, category=cats[i % 15], date=date(2026, 1 + i % 9, 1 + i % 27), year=2026, month=1 + i % 9,
                        amount=Decimal("10.25"), amount_base=Decimal("10.25"), description=f"item {i}") for i in range(self.N)]
        Expense.objects.bulk_create(rows, batch_size=500)

    def test_thousands_of_expenses_answered_fast_and_exact(self):
        exact = Decimal("10.25") * sum(1 for i in range(self.N) if i % 9 == 8)  # month 9 only (plus the fixture's Rent)
        with NO_LLM, CaptureQueriesContext(connection) as q:
            t0 = time.monotonic()
            text = fx.ask(self, "total expenses for Sept 2026")["message"]["content"]
            elapsed = time.monotonic() - t0
        self.assertIn(f"{exact + Decimal('1000'):,.2f} EGP", text)
        self.assertLess(elapsed, 3.0)
        self.assertLess(len(q), 80)

    def test_big_table_is_capped_but_totals_cover_every_row(self):
        with NO_LLM:
            text = fx.ask(self, "detailed expenses table from Jan to Sept 2026")["message"]["content"]
        self.assertIn("**Grand Total**", text)
        self.assertIn("Showing the first 300 of", text)
        self.assertLess(len(text), 60000)
        total = Decimal("10.25") * self.N + Decimal("1170.50")
        self.assertIn(f"{total:,.2f} EGP", text)


class GoldHoldingsFollowUpTests(TestCase):
    """The real log: "what is the gold price today for 24k?" then "and how much i hold?".
    Regression: the Balance gold entry is a mirror of the Owned gold fixed assets (gold_sync_service), so the
    grams must be counted ONCE (the first version answered 250 g for 125 g of gold)."""

    ASSETS = (("Bars 5-10-20", "35"), ("Bar 20 a", "20"), ("Bar 20 b", "20"), ("Bar 50", "50"))

    def setUp(self):
        from core.models import Currency, FixedAsset
        from core.models.fixed_assets_gold import GoldDetails
        from core.services.fixed_assets.gold_sync_service import _refresh_gold_asset_pricing, _sync_gold_balance_from_assets

        fx.build(self)
        for owner, assets in ((self.user, self.ASSETS), (self.other, (("Other", "888"),))):
            Currency.objects.get_or_create(owner=owner, code="Gold", defaults={"name": "Gold (grams)"})
            for name, grams in assets:
                a = FixedAsset.objects.create(owner=owner, name=name, asset_type="Gold", status="Owned", purchase_date=date(2024, 1, 1),
                                              purchase_price=Decimal("1000"), current_market_value=Decimal("1000"))
                gd = GoldDetails.objects.create(asset=a, purity="24k", weight=Decimal(grams))
                _refresh_gold_asset_pricing(a, gd)
            _sync_gold_balance_from_assets(owner)   # what the app does on every gold asset save

    def test_follow_up_after_gold_price_counts_the_gold_once(self):
        with NO_LLM as gen:
            first = fx.ask(self, "what is the gold price today for 24k?")["message"]["content"]
            self.assertIn("Gold 24K price per gram", first)
            data = fx.ask(self, "and how much i hold?")
            gen.assert_not_called()
        text = data["message"]["content"]
        self.assertIn("Gold holdings: 125.00 g in total, worth 625,000.00 EGP", text)   # 125 g x 5,000 (24k sell in the fixture)
        self.assertNotIn("250.00", text)
        self.assertIn("Includes 4 gold fixed asset(s) (125.00 g)", text)
        self.assertNotIn("888", text)
        self.assertEqual(data["message"]["tool_calls"][0]["tool"], "direct_answer_gold_holdings")

    def test_same_answer_for_the_two_phrasings_and_matches_balance_value(self):
        with NO_LLM:
            a = fx.ask(self, "how much gold i hold and how much it's value in EGP")["message"]["content"]
            b = fx.ask(self, "how much gold do I own")["message"]["content"]
        self.assertIn("125.00 g in total, worth 625,000.00 EGP", a)
        self.assertEqual(a.split("\n")[0], b.split("\n")[0])

    def test_asset_grams_missing_from_balance_are_added_but_sold_assets_are_not(self):
        from core.models import BalanceEntry, FixedAsset
        from core.models.fixed_assets_gold import GoldDetails

        BalanceEntry.objects.filter(owner=self.user, balance_type="gold").delete()   # sync has not run yet
        sold = FixedAsset.objects.create(owner=self.user, name="Sold bar", asset_type="Gold", status="Sold", purchase_date=date(2024, 1, 1),
                                         purchase_price=Decimal("1"), current_market_value=Decimal("1"))
        GoldDetails.objects.create(asset=sold, purity="24k", weight=Decimal("500"))
        with NO_LLM:
            text = fx.ask(self, "how much gold do I hold")["message"]["content"]
        self.assertIn("Gold holdings: 125.00 g in total, worth 625,000.00 EGP", text)   # Owned assets only (the Sold 500 g is ignored), once
        self.assertNotIn("Includes", text)   # nothing is mirrored into Balance in this state

    def test_follow_up_is_traced_and_standalone_question_works(self):
        with NO_LLM, self.assertLogs("ai.pipeline", level="WARNING") as logs:
            fx.ask(self, "gold price today")
            fx.ask(self, "and how much i hold?")
        self.assertTrue(any("follow_up_of:gold_price" in m for m in logs.output))

    def test_follow_up_without_a_previous_question_still_goes_to_the_llm(self):
        with patch.object(OllamaProvider, "generate", return_value={"content": "LLM answer", "error": None}) as gen:
            data = fx.ask(self, "and how much i hold?")
        self.assertEqual(data["message"]["content"], "LLM answer")
        self.assertTrue(gen.called)
