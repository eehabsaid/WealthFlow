"""Zip 2 B: how/where/should questions take the reasoning path (knowledge chunks, no data snapshot, one bounded
LLM call), and every step leaves [AI-PIPELINE] lines."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase

from core.models import AppSettings
from core.tests.ai import qe_fixtures as fx
from core.views.ai_chat.chat_pipeline import STAGES

LAPTOP = "if i bought a laptop where should i record its price? in assets, or in expenses?"
PROVIDER = "core.views.ai_chat.ai_chat_core_views.get_active_ai_provider"


def stub_provider(reply="Record it as an asset.", error=None):
    prov = MagicMock()
    prov.supports_tools = True
    prov.calls = []

    def generate(messages, tools=None, **kw):
        prov.calls.append({"messages": messages, "tools": tools, **kw})
        return {"content": "" if error else reply, "tool_calls": [], "error": error, "prompt_tokens": 1, "completion_tokens": 1}

    prov.generate.side_effect = generate
    return prov


class WorkflowChatTests(TestCase):
    def setUp(self):
        fx.build(self)

    def chat(self, text, prov):
        with patch(PROVIDER, return_value=prov), self.assertLogs("core.ai.pipeline", level="WARNING") as logs:
            data = fx.ask(self, text)
        return data, "\n".join(logs.output)

    def test_laptop_question_uses_knowledge_not_data_snapshot(self):
        prov = stub_provider()
        data, log = self.chat(LAPTOP, prov)
        self.assertEqual(len(prov.calls), 1)
        call = prov.calls[0]
        system = call["messages"][0]["content"]
        self.assertIsNone(call["tools"])
        self.assertNotIn("=== FINANCIAL CONTEXT DATA ===", system)
        self.assertIn("APP KNOWLEDGE", system)
        self.assertIn("NOT written as an Expense row", system)                 # generated data-flows chunk
        self.assertLess(sum(len(m["content"]) for m in call["messages"]), 6000)  # was ~13.6K chars
        self.assertEqual(call["max_tokens"], 320)
        self.assertEqual(data["message"]["content"], "Record it as an asset.")
        self.assertEqual(data["message"]["sources"], ["app_knowledge"])

    def test_every_stage_is_logged_including_knowledge(self):
        _, log = self.chat(LAPTOP, stub_provider())
        self.assertIn("request received", log)
        for stage in ("understand", "route", "knowledge", "reason", "respond"):
            self.assertIn(f"stage={stage} ", log)
        self.assertIn("summary total=", log)
        self.assertIn("knowledge", STAGES)

    def test_prompt_asks_to_weigh_options_and_state_uncertainty(self):
        prov = stub_provider()
        self.chat(LAPTOP, prov)
        system = prov.calls[0]["messages"][0]["content"]
        for phrase in ("Think it through", "what is uncertain", "Do not invent"):
            self.assertIn(phrase, system)

    def test_prompt_carries_only_the_owners_setup(self):
        prov = stub_provider()
        self.chat(LAPTOP, prov)
        system = prov.calls[0]["messages"][0]["content"]
        self.assertIn("Real Estate x1", system)
        self.assertNotIn("SECRET", system)
        self.assertNotIn("9999999", system)

    def test_provider_error_is_a_clean_error_with_logged_summary(self):
        data, log = self.chat(LAPTOP, stub_provider(error="timed out"))
        self.assertFalse(data["ok"])
        self.assertIn("summary total=", log)
        self.assertIn("provider_error", log)

    def test_empty_model_reply_gets_the_fallback_text(self):
        data, _ = self.chat(LAPTOP, stub_provider(reply=" "))
        self.assertTrue(data["message"]["content"].strip())

    def test_kill_switch_restores_the_data_pipeline(self):
        AppSettings.set("ai_workflow_reasoning", "false", user=self.user)
        prov = stub_provider()
        self.chat(LAPTOP, prov)
        system = prov.calls[0]["messages"][0]["content"]
        self.assertIn("=== FINANCIAL CONTEXT DATA ===", system)

    def test_data_lookups_do_not_take_the_workflow_path(self):
        prov = stub_provider()
        data, log = self.chat("how much did I spend in June 2026 and compare it with August", prov)
        self.assertIn("stage=knowledge status=skipped", log)
        self.assertIn("data_question", log)
        self.assertIn("=== FINANCIAL CONTEXT DATA ===", prov.calls[0]["messages"][0]["content"])
