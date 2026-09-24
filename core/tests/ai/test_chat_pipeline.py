"""Staged chat pipeline: Understand / Validate logic, tracing, and view integration."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from core.models import AppSettings
from core.tests.billing.test_support import grant_ai_workspace_access
from core.views.ai_chat.chat_pipeline import STAGES, PipelineTrace, understand
from core.views.ai_chat.chat_pipeline.grounding import ground_answer

User = get_user_model()
EVIDENCE = "Balance: 12,345.67 EGP. Salary 30000. Food 10000. Rent 5000. Share 0.337. Total 1,234,567"
CTX = "=== FINANCIAL CONTEXT DATA ===\n" + EVIDENCE
GP = "core.views.ai_chat.ai_chat_core_views.generation_pipeline.build_context"
VIEW = "core.views.ai_chat.ai_chat_core_views"


class GroundingTest(SimpleTestCase):
    def check(self, answer, question="how much"):
        return ground_answer(answer, question, EVIDENCE)

    def test_exact_rounded_and_suffix(self):
        for a in ("You have EGP 12,345.67", "about 12,346", "roughly 1.2M in total"):
            self.assertTrue(self.check(a).ok, a)

    def test_percent_and_derived(self):
        self.assertTrue(self.check("That is 33.7% of it").ok)
        self.assertTrue(self.check("Salary plus food is 40,000").ok)
        self.assertTrue(self.check("Food is 33% of salary").ok)

    def test_ungrounded_detected(self):
        r = self.check("You have 99,999 EGP")
        self.assertEqual(r.ungrounded, ("99,999",))

    def test_ignored_noise(self):
        self.assertEqual(self.check("In 2026 you had 25 items").checked, 0)
        self.assertEqual(self.check("1. first\n2. second").checked, 0)
        self.assertEqual(ground_answer("You asked about 4,321", "what is 4,321?", EVIDENCE).checked, 0)

    def test_arabic_indic_digits(self):
        self.assertTrue(self.check("الرصيد ١٢٬٣٤٥٫٦٧").ok)


class UnderstandTest(SimpleTestCase):
    def test_intents_and_entities(self):
        u = understand("Compare my expenses in Jan 2026 and Feb 2026 in EGP")
        self.assertEqual(u.intent, "comparison")
        self.assertIn("expenses", u.topics)
        self.assertEqual(u.entities["periods"], ["2026-01", "2026-02"])
        self.assertEqual(u.entities["currencies"], ["EGP"])
        self.assertEqual(u.question_domain, "business_data_analysis")

    def test_domain_matches_previous_inference(self):
        self.assertEqual(understand("which pages exist in the app?").question_domain, "app_features_architecture")
        self.assertEqual(understand("x", "custom").question_domain, "custom")

    def test_smalltalk_and_language(self):
        self.assertEqual(understand("hello!").intent, "smalltalk")
        self.assertEqual(understand("كم رصيدي؟").scope["language"], "ar")


class TraceTest(SimpleTestCase):
    def test_logs_each_stage_and_summary(self):
        t = PipelineTrace(1, 2)
        with self.assertLogs("core.ai.pipeline", level="WARNING") as cm:
            with t.stage("understand") as rec:
                rec.detail["x"] = 1
            t.skip_remaining("test")
            t.log_summary()
        self.assertEqual(len([m for m in cm.output if "stage=" in m]), 6)
        self.assertIn("summary", cm.output[-1])
        self.assertEqual([s["stage"] for s in t.to_dict()["stages"]], list(STAGES))


class PipelineViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pipe_user", password="Password123!")
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_direct_answers", "false")

    def ask(self, text, answers, **body):
        prov = MagicMock()
        prov.supports_tools = False
        prov.generate.side_effect = [{"content": a, "tool_calls": None, "error": None} for a in answers]
        ctx = ([{"role": "system", "content": "SYS\n" + CTX}, {"role": "user", "content": text}], ["balance"])
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=ctx), \
                self.assertLogs("core.ai.pipeline", level="WARNING") as logs:
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": text, **body}),
                                   content_type="application/json")
        return res, prov, "\n".join(logs.output)

    def test_grounded_answer_costs_no_extra_llm_call(self):
        res, prov, log = self.ask("what is my balance?", ["You have 12,345.67 EGP."])
        self.assertEqual(prov.generate.call_count, 1)
        self.assertEqual(res.json()["message"]["content"], "You have 12,345.67 EGP.")
        for stage in STAGES:
            self.assertIn(f"stage={stage} ", log)
        self.assertIn("verdict", log)

    def test_default_mode_flags_without_llm_call(self):
        res, prov, _ = self.ask("what is my balance?", ["You have 99,999 EGP."])
        self.assertEqual(prov.generate.call_count, 1)
        self.assertIn("couldn't match these figures", res.json()["message"]["content"])

    def test_regenerate_mode_makes_one_extra_call(self):
        AppSettings.set("ai_validate_mode", "regenerate")
        res, prov, _ = self.ask("what is my balance?", ["You have 99,999 EGP.", "You have 12,345.67 EGP."])
        self.assertEqual(prov.generate.call_count, 2)
        self.assertIsNone(prov.generate.call_args[1]["tools"])
        self.assertEqual(res.json()["message"]["content"], "You have 12,345.67 EGP.")

    def test_regenerate_still_bad_is_flagged_and_capped_at_one(self):
        AppSettings.set("ai_validate_mode", "regenerate")
        res, prov, _ = self.ask("what is my balance?", ["99,999 EGP", "88,888 EGP"])
        self.assertEqual(prov.generate.call_count, 2)
        self.assertIn("couldn't match", res.json()["message"]["content"])

    def test_off_mode_and_no_figures_skip(self):
        AppSettings.set("ai_validate_mode", "off")
        res, _, log = self.ask("what is my balance?", ["You have 99,999 EGP."])
        self.assertNotIn("couldn't match", res.json()["message"]["content"])
        self.assertIn("mode_off", log)

    def test_debug_flag_returns_trace(self):
        AppSettings.set("ai_pipeline_debug", "true")
        res, _, _ = self.ask("what is my balance?", ["You have 12,345.67 EGP."])
        self.assertEqual(len(res.json()["pipeline"]["stages"]), 5)  # respond still in progress

    def test_direct_answer_path_skips_stages(self):
        prov = MagicMock()
        direct = {"content": "Paid: 100", "tool_calls": [], "sources": ["salary"]}
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), \
                patch(f"{VIEW}.try_direct_answer", return_value=direct), \
                self.assertLogs("core.ai.pipeline", level="WARNING") as logs:
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": "salary sep 2026"}),
                                   content_type="application/json")
        self.assertEqual(res.json()["message"]["content"], "Paid: 100")
        self.assertIn("direct_answer", "\n".join(logs.output))
        prov.generate.assert_not_called()
