"""Phase 1: pipeline settings (validate mode / debug), answer-from-context path, embedding skip + breaker."""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from core.models import AppSettings
from core.services.ai.providers.registry.scoring_semantic import apply_semantic_bonus
from core.services.ai.retrieval import embeddings
from core.tests.billing.test_support import grant_ai_workspace_access
from core.views.ai_chat.chat_pipeline.reason import answer_from_context
from core.views.ai_chat.chat_pipeline.retrieve import Retrieval
from core.views.ai_chat.chat_pipeline.validate import get_mode

User = get_user_model()
GP = "core.views.ai_chat.ai_chat_core_views.generation_pipeline.build_context"
VIEW = "core.views.ai_chat.ai_chat_core_views"
CTX = "=== FINANCIAL CONTEXT DATA ===\nBalance: 12,345.67 EGP"


class PipelineSettingsApiTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="adm", password="pw12345!", is_staff=True)
        from core.authentication.services import AuthWorkflowService
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        self.client.force_login(self.admin)

    def post(self, **body):
        return self.client.post("/api/settings/ai/", json.dumps(body), content_type="application/json")

    def test_get_defaults(self):
        data = self.client.get("/api/settings/ai/").json()
        self.assertEqual(data["ai_validate_mode"], "flag")
        self.assertIs(data["ai_pipeline_debug"], False)

    def test_save_roundtrip_and_pipeline_reads_it(self):
        self.assertEqual(self.post(ai_validate_mode="regenerate", ai_pipeline_debug=True).status_code, 200)
        data = self.client.get("/api/settings/ai/").json()
        self.assertEqual(data["ai_validate_mode"], "regenerate")
        self.assertIs(data["ai_pipeline_debug"], True)
        self.assertEqual(get_mode(self.admin), "regenerate")
        self.post(ai_validate_mode="off", ai_pipeline_debug=False)
        self.assertEqual(get_mode(self.admin), "off")

    def test_invalid_mode_rejected_and_nothing_saved(self):
        self.assertEqual(self.post(ai_validate_mode="bogus").status_code, 400)
        self.assertEqual(self.client.get("/api/settings/ai/").json()["ai_validate_mode"], "flag")

    def test_omitted_keys_keep_current_values(self):
        self.post(ai_validate_mode="off", ai_pipeline_debug=True)
        self.post(ai_temperature=0.5)
        data = self.client.get("/api/settings/ai/").json()
        self.assertEqual(data["ai_validate_mode"], "off")
        self.assertIs(data["ai_pipeline_debug"], True)


class AnswerFromContextTest(SimpleTestCase):
    def r(self, sources, ctx="data"):
        return Retrieval(messages=[], sources=sources, context_text=ctx)

    def u(self, intent="data_lookup", periods=()):
        return SimpleNamespace(intent=intent, entities={"periods": list(periods)})

    def test_topical_provider_match_answers_from_context(self):
        self.assertEqual(answer_from_context(self.r(["balance"]), "business_data_analysis", self.u()), (True, "topical_data_provider_match"))

    def test_keeps_tools_when_retrieval_did_not_cover(self):
        d = "business_data_analysis"
        self.assertFalse(answer_from_context(self.r([]), d, self.u())[0])
        self.assertFalse(answer_from_context(self.r(["balance"], ""), d, self.u())[0])
        self.assertFalse(answer_from_context(self.r(["overview", "cash_flow", "goal_planning", "risk_analysis"]), d, self.u())[0])
        self.assertFalse(answer_from_context(self.r(["balance"]), "app_features_architecture", self.u())[0])
        self.assertFalse(answer_from_context(self.r(["balance"]), d, self.u("forecast"))[0])
        self.assertFalse(answer_from_context(self.r(["balance"]), d, self.u("action_request"))[0])
        self.assertFalse(answer_from_context(self.r(["expenses"]), d, self.u(periods=["2026-01"]))[0])
        self.assertFalse(answer_from_context(None, d)[0])


class ContextPathViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ctx_user", password="Password123!")
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_direct_answers", "false")

    def ask(self, text, answers, sources):
        prov = MagicMock()
        prov.supports_tools = True
        prov.generate.side_effect = [{"content": a, "tool_calls": None, "error": None} for a in answers]
        ctx = ([{"role": "system", "content": "SYS\n" + CTX}, {"role": "user", "content": text}], sources)
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=ctx), \
                self.assertLogs("core.ai.pipeline", level="WARNING") as logs:
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": text}),
                                   content_type="application/json")
        return res, prov, "\n".join(logs.output)

    def test_grounded_question_sends_no_tools_and_one_call(self):
        res, prov, log = self.ask("what is my balance?", ["You have 12,345.67 EGP."], ["balance"])
        self.assertEqual(prov.generate.call_count, 1)
        self.assertIsNone(prov.generate.call_args[1]["tools"])
        self.assertIn("stage=tool status=skipped", log)
        self.assertEqual(res.json()["message"]["content"], "You have 12,345.67 EGP.")

    def test_uncovered_question_still_offers_tools(self):
        _, prov, _ = self.ask("what is my balance?", ["You have 12,345.67 EGP."], ["overview", "cash_flow", "goal_planning", "risk_analysis"])
        self.assertTrue(prov.generate.call_args[1]["tools"])

    def test_empty_context_answer_escalates_to_tools(self):
        res, prov, log = self.ask("what is my balance?", ["", "", "You have 12,345.67 EGP."], ["balance"])
        self.assertEqual(prov.generate.call_count, 3)
        self.assertTrue(prov.generate.call_args[1]["tools"])
        self.assertIn('"escalated_to_tools": true', log)
        self.assertEqual(res.json()["message"]["content"], "You have 12,345.67 EGP.")


class EmbeddingSkipAndBreakerTest(TestCase):
    def test_lexically_decisive_skips_semantic(self):
        scores = {"a": 3.5, "b": 0.0}
        before = embeddings.stats["skipped_lexical"]
        with patch("core.services.ai.retrieval.semantic_scores") as sem:
            apply_semantic_bonus(scores, {"a": 1, "b": 2}, "gold", lambda p: "x")
        sem.assert_not_called()
        self.assertEqual(embeddings.stats["skipped_lexical"], before + 1)
        self.assertEqual(scores, {"a": 3.5, "b": 0.0})

    def test_weak_lexical_still_uses_semantic(self):
        scores = {"a": 1.0, "b": 0.0}
        with patch("core.services.ai.retrieval.semantic_scores", return_value={"a": 0.1, "b": 0.8}) as sem:
            apply_semantic_bonus(scores, {"a": 1, "b": 2}, "how much do I owe", lambda p: "x")
        sem.assert_called_once()
        self.assertAlmostEqual(scores["b"], 2.4)
        self.assertEqual(scores["a"], 1.0)

    def test_failure_opens_breaker_and_skips_following_calls(self):
        embeddings._failed_until = 0.0
        try:
            with patch.object(embeddings, "make_json_http_request", return_value=(None, 0, "boom")) as call:
                self.assertIsNone(embeddings._embed("one"))
                self.assertIsNone(embeddings._embed("two"))
                self.assertIsNone(embeddings._embed("three"))
            self.assertEqual(call.call_count, 1)
            embeddings._failed_until = time.monotonic() - 1
            with patch.object(embeddings, "make_json_http_request", return_value=({"embedding": [1.0]}, 200, None)) as call:
                self.assertEqual(embeddings._embed("again"), [1.0])
            self.assertEqual(call.call_count, 1)
        finally:
            embeddings._failed_until = 0.0
