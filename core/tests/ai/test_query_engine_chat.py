"""Chat-level proof: supported questions are answered with ZERO LLM calls (OllamaProvider.generate raises),
scoped to the asking user, correct, fast at realistic volume, and traced."""

import time
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from core.integrations.ai_provider import OllamaProvider
from core.models import AppSettings, Expense, ExpenseCategory

from core.tests.billing.test_support import grant_ai_workspace_access

from . import qe_fixtures as fx

NO_LLM = patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))

# question -> substrings that must be in the answer. Every one runs with the LLM forbidden.
CASES = [
    ("what is the gold price today for 24k?", ["5,000.00 EGP", "4,950.00 EGP"]),
    ("gold 21k buy price", ["21K", "buy", "4,300.00 EGP"]),
    ("gold prices by karat", ["| 24K | 5,000.00 | 4,950.00 |", "| 18K |"]),
    ("سعر جرام الذهب عيار 21", ["عيار 21", "4,375.00 EGP"]),
    ("what is the USD exchange rate", ["1 USD = 50.2500 EGP", "buy 50.0000", "sell 50.5000"]),
    ("سعر الدولار اليوم", ["1 USD = 50.2500 EGP"]),
    ("total expenses for Sept 2026", ["1,000.00 EGP across 1 transactions"]),
    ("total expenses from Jun to Sept 2026", ["**Grand Total**", "1,170.50 EGP"]),
    ("expenses by category for Jun 2026", ["Food", "150.50 EGP", "100.0%"]),
    ("مصروفات شهر يونيو 2026", ["150.50 EGP"]),
    ("my last expense", ["Rent", "1,000.00 EGP"]),
    ("What was my paid salary for January 2026?", ["87,643.86 EGP"]),
    ("ما هو راتبي في يناير 2026", ["87,643.86 EGP", "الراتب المدفوع"]),
    ("last salary", ["Latest paid salary", "87,643.86"]),
    ("how much money do I have", ["Total balance: 1,000.00 EGP"]),
    ("كم رصيدي", ["إجمالي الرصيد: 1,000.00 EGP"]),
    ("balances per currency", ["| EGP |", "**Grand Total**"]),
    ("my certificates", ["1 active certificate(s)", "100,000.00 EGP"]),
    ("next certificate interest date", ["Next interest posting"]),
    ("what are my fixed assets", ["5,000,000.00 EGP", "1 asset(s)"]),
    ("assets by type", ["Real Estate", "100.0%"]),
]


class NoLlmAnswerTests(TestCase):
    def setUp(self):
        fx.build(self)

    def test_supported_questions_answer_without_llm_and_without_leaks(self):
        for q, needles in CASES:
            with self.subTest(q=q), NO_LLM as gen:
                data = fx.ask(self, q)
                text = data["message"]["content"]
                for n in needles:
                    self.assertIn(n, text)
                for secret in ("SECRET", "777,777", "111.00", "999,999", "9,999,999"):
                    self.assertNotIn(secret, text)
                call = data["message"]["tool_calls"][0]
                self.assertTrue(call["direct_answer"])
                self.assertEqual(call["llm_calls"], 0)
                gen.assert_not_called()

    def test_tenant_isolation_other_user_sees_only_own_data(self):
        grant_ai_workspace_access(self.other)
        self.client.force_login(self.other)
        with NO_LLM:
            text = fx.ask(self, "how much money do I have")["message"]["content"]
            self.assertIn("777,777.00", text)
            self.assertNotIn("1,000.00 EGP", text)
            self.assertIn("111.00", fx.ask(self, "salary for January 2026")["message"]["content"])
            self.assertIn("9,999,999.00", fx.ask(self, "total fixed assets")["message"]["content"])

    def test_tool_calls_are_json_safe_with_decimals(self):
        from core.views.ai_chat.ai_chat_core_views.response_finalizer import json_safe

        out = json_safe([{"a": Decimal("1.50"), "d": date(2026, 1, 2), "s": {1, 2}}])
        self.assertEqual(out[0]["a"], "1.50")
        self.assertEqual(out[0]["d"], "2026-01-02")

    def test_kill_switch_sends_question_to_llm(self):
        AppSettings.set("ai_direct_answers", "false", user=self.user)
        with patch.object(OllamaProvider, "generate", return_value={"content": "LLM answer", "error": None}) as gen:
            data = fx.ask(self, "what is the gold price today for 24k?")
        self.assertEqual(data["message"]["content"], "LLM answer")
        self.assertTrue(gen.called)

    def test_route_is_traced_with_capability_slots_and_llm_calls(self):
        with NO_LLM, self.assertLogs("core.ai.pipeline", level="WARNING") as logs:
            fx.ask(self, "gold 21k buy price")
        line = next(m for m in logs.output if "stage=route" in m)
        for needle in ("gold_price", "confidence", '"karat": "21"', "llm_calls=0", '"path": "engine"'):
            self.assertIn(needle, line)


class AnalyticAndLlmSlotTests(TestCase):
    def setUp(self):
        fx.build(self)

    def test_analytic_question_reaches_llm_and_gets_computed_facts(self):
        seen = {}

        def fake(messages, tools=None, **kw):
            seen["text"] = "\n".join(str(m.get("content")) for m in messages)
            return {"content": "Because rent.", "tool_calls": None, "error": None}

        with patch.object(OllamaProvider, "generate", side_effect=fake):
            data = fx.ask(self, "why did my expenses grow in Sept 2026")
        self.assertEqual(data["message"]["content"].startswith("Because rent."), True)
        self.assertIn("COMPUTED FACTS", seen["text"])
        self.assertIn("1,000.00", seen["text"])

    def test_unclear_question_uses_exactly_one_slot_call(self):
        reply = 'Sure: {"capability": "gold_price", "metric": "price", "filters": {"karat": "21", "side": "sell"}}'
        with patch.object(OllamaProvider, "generate", return_value={"content": reply, "error": None}) as gen:
            data = fx.ask(self, "gold today")  # only the bare word "gold": router confidence too low, one slot call
        self.assertEqual(gen.call_count, 1)
        self.assertIn("4,375.00 EGP", data["message"]["content"])
        self.assertEqual(data["message"]["tool_calls"][0]["llm_calls"], 1)

    def test_bad_slot_json_falls_through_to_pipeline(self):
        from core.services.ai.query_engine.llm_slots import request_from_json

        self.assertIsNone(request_from_json({"capability": "expenses", "periods": ["June"]}, "en"))
        self.assertIsNone(request_from_json({"capability": "nope"}, "en"))
        self.assertIsNone(request_from_json({"capability": "gold_price", "periods": ["2026-06"]}, "en"))
        self.assertIsNone(request_from_json([], "en"))

    def test_slot_call_skipped_when_over_wall_clock_budget(self):
        AppSettings.set("ai_query_llm_budget_s", "5")
        with patch.object(OllamaProvider, "generate", return_value={"content": "LLM answer", "error": None}) as gen:
            fx.ask(self, "gold today")
        self.assertEqual(gen.call_count, 1)  # the normal pipeline's call only, not a slot call on top


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
    """The real log: "what is the gold price today for 24k?" then "and how much i hold?" took 9m56s on the LLM path."""

    def setUp(self):
        from core.models import BalanceEntry, Currency, FixedAsset
        from core.models.fixed_assets_gold import GoldDetails

        fx.build(self)
        for owner, grams, asset_g in ((self.user, "10.00", "5.0000"), (self.other, "999.00", "888.0000")):
            gold = Currency.objects.get_or_create(owner=owner, code="GOLD", defaults={"name": "Gold"})[0]
            BalanceEntry.objects.create(owner=owner, title="Gold bars", balance_type="gold", currency=gold, amount=Decimal(grams), purity="21k")
            asset = FixedAsset.objects.create(owner=owner, name="Gold set", asset_type="Gold", purchase_date=date(2024, 1, 1),
                                              purchase_price=Decimal("1000"), current_market_value=Decimal("1000"))
            GoldDetails.objects.create(asset=asset, purity="21k", weight=Decimal(asset_g))

    def test_follow_up_after_gold_price_is_answered_without_llm(self):
        with NO_LLM as gen:
            first = fx.ask(self, "what is the gold price today for 24k?")["message"]["content"]
            self.assertIn("Gold 24K price per gram", first)
            data = fx.ask(self, "and how much i hold?")
            text = data["message"]["content"]
            gen.assert_not_called()
        self.assertIn("Gold holdings: 15.00 g in total", text)  # 10 g in Balance + 5 g fixed asset
        self.assertIn("Balance: Gold bars", text)
        self.assertIn("Fixed asset: Gold set", text)
        self.assertNotIn("999", text)
        self.assertNotIn("888", text)
        self.assertEqual(data["message"]["tool_calls"][0]["tool"], "direct_answer_gold_holdings")

    def test_follow_up_is_traced_and_standalone_question_works(self):
        with NO_LLM, self.assertLogs("core.ai.pipeline", level="WARNING") as logs:
            fx.ask(self, "gold price today")
            fx.ask(self, "and how much i hold?")
            text = fx.ask(self, "how much gold do I own")["message"]["content"]
        self.assertIn("15.00 g", text)
        self.assertTrue(any("follow_up_of:gold_price" in m for m in logs.output))

    def test_follow_up_without_a_previous_question_still_goes_to_the_llm(self):
        with patch.object(OllamaProvider, "generate", return_value={"content": "LLM answer", "error": None}) as gen:
            data = fx.ask(self, "and how much i hold?")
        self.assertEqual(data["message"]["content"], "LLM answer")
        self.assertTrue(gen.called)
