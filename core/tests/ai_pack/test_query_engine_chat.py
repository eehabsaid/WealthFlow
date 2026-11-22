"""Chat-level proof: supported questions are answered with ZERO LLM calls (OllamaProvider.generate raises),
scoped to the asking user, correct, fast at realistic volume, and traced."""


from ai.models import AISetting
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from ai.integrations.ai_provider import OllamaProvider

from core.tests.billing.test_support import grant_ai_workspace_access

import core.tests.ai_pack.qe_fixtures as fx
from .query_engine_chat_support import CASES, NO_LLM


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
        from ai.views.ai_chat.ai_chat_core_views.response_finalizer import json_safe

        out = json_safe([{"a": Decimal("1.50"), "d": date(2026, 1, 2), "s": {1, 2}}])
        self.assertEqual(out[0]["a"], "1.50")
        self.assertEqual(out[0]["d"], "2026-01-02")

    def test_kill_switch_sends_question_to_llm(self):
        AISetting.set("ai_direct_answers", "false", user=self.user)
        with patch.object(OllamaProvider, "generate", return_value={"content": "LLM answer", "error": None}) as gen:
            data = fx.ask(self, "what is the gold price today for 24k?")
        self.assertEqual(data["message"]["content"], "LLM answer")
        self.assertTrue(gen.called)

    def test_route_is_traced_with_capability_slots_and_llm_calls(self):
        with NO_LLM, self.assertLogs("ai.pipeline", level="WARNING") as logs:
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
        from ai.services.query_engine.llm_slots import request_from_json

        self.assertIsNone(request_from_json({"capability": "expenses", "periods": ["June"]}, "en"))
        self.assertIsNone(request_from_json({"capability": "nope"}, "en"))
        self.assertIsNone(request_from_json({"capability": "gold_price", "periods": ["2026-06"]}, "en"))
        self.assertIsNone(request_from_json([], "en"))

    def test_slot_call_skipped_when_over_wall_clock_budget(self):
        AISetting.set("ai_query_llm_budget_s", "5")
        AISetting.set("ai_prompt_tps", "36.9")   # a slow machine: the estimate (~32 s) is over the 5 s budget
        AISetting.set("ai_decode_tps", "1.67")
        with patch.object(OllamaProvider, "generate", return_value={"content": "LLM answer", "error": None}) as gen:
            fx.ask(self, "gold today")
        self.assertEqual(gen.call_count, 1)  # the normal pipeline's call only, not a slot call on top
