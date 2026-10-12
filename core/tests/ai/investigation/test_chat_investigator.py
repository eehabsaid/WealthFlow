"""AIChatView + investigator: escalation when a normal path gives up, modes, code-question routing, settings, trace."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from core.models import AppSettings
from core.tests.billing.test_support import grant_ai_workspace_access
from core.views.ai_chat.chat_pipeline import STAGES

from .support import make_user, seed_tenant, tool_call

VIEW = "core.views.ai_chat.ai_chat_core_views"
GP = "core.views.ai_chat.ai_chat_core_views.generation_pipeline.build_context"
CTX = "=== FINANCIAL CONTEXT DATA ===\nBalance: 12,345.67 EGP."
REFUSAL = "I don't have access to your data, so I can't tell."


class InvestigatorChatBase(TestCase):
    user_kwargs: dict = {}

    def setUp(self):
        self.user = make_user("chat_inv_user", **self.user_kwargs)
        seed_tenant(self.user, "Q", expenses=2, amount="50.00")
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_direct_answers", "false")

    def ask(self, text, script, **body):
        prov = MagicMock()
        prov.supports_tools = True
        prov.model = "scripted"
        items = [{"content": s, "tool_calls": [], "error": None} if isinstance(s, str) else {"content": "", "tool_calls": [], "error": None, **s}
                 for s in script]
        prov.generate.side_effect = items
        ctx = ([{"role": "system", "content": "SYS\n" + CTX}, {"role": "user", "content": text}], ["balance"])
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=ctx), \
                self.assertLogs("core.ai.pipeline", level="WARNING") as logs:
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": text, **body}),
                                   content_type="application/json")
        return res, prov, "\n".join(logs.output)


class EscalationTest(InvestigatorChatBase):
    def test_a_give_up_answer_is_replaced_by_an_investigation(self):
        res, prov, log = self.ask("what is my balance?", [REFUSAL, tool_call("app_data_models"), "You have 2 expenses (Expense rows: 2)."])
        data = res.json()
        self.assertEqual(data["message"]["content"], "You have 2 expenses (Expense rows: 2).")
        self.assertEqual(prov.generate.call_count, 3)
        self.assertIn("investigation_data", data["sources"])
        self.assertEqual([c["tool"] for c in data["message"]["tool_calls"]], ["app_data_models"])
        self.assertIn("stage=investigate status=ok", log)
        self.assertNotIn(REFUSAL, json.dumps(data))

    def test_a_good_answer_is_left_alone_and_costs_no_extra_call(self):
        res, prov, log = self.ask("what is my balance?", ["You have 12,345.67 EGP."])
        self.assertEqual(prov.generate.call_count, 1)
        self.assertEqual(res.json()["message"]["content"], "You have 12,345.67 EGP.")
        self.assertIn("stage=investigate status=skipped", log)

    def test_a_provider_error_in_the_normal_path_escalates_too(self):
        res, prov, _ = self.ask("what is my balance?", [{"error": "model busy"}, tool_call("app_data_models"), "Expense has 2 rows."])
        self.assertEqual(res.json()["message"]["content"], "Expense has 2 rows.")
        self.assertEqual(prov.generate.call_count, 3)

    def test_if_the_investigator_cannot_answer_either_the_provider_error_is_reported(self):
        res, prov, _ = self.ask("what is my balance?", [{"error": "down"}, {"error": "down"}])
        data = res.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_key"], "ai_error_provider_unavailable")    # the app's existing provider-error contract
        self.assertEqual(data["error"], "down")
        self.assertEqual(prov.generate.call_count, 2)

    def test_how_do_i_questions_escalate_from_the_workflow_path(self):
        res, prov, _ = self.ask("how do I record a laptop purchase?", [REFUSAL, tool_call("app_knowledge_search", query="laptop purchase"),
                                                                       "Record it under Fixed Assets > Acquisition Costs."])
        self.assertIn("Fixed Assets", res.json()["message"]["content"])
        self.assertIn("investigation_docs", res.json()["sources"])

    def test_mode_off_keeps_the_original_behaviour(self):
        AppSettings.set("ai_investigator_mode", "off")
        res, prov, _ = self.ask("what is my balance?", [REFUSAL])
        self.assertEqual(prov.generate.call_count, 1)
        self.assertIn("I don't have access", res.json()["message"]["content"])

    def test_mode_always_skips_the_normal_path(self):
        AppSettings.set("ai_investigator_mode", "always")
        res, prov, _ = self.ask("what is my balance?", [tool_call("app_data_models"), "Expense has 2 rows."])
        self.assertEqual(prov.generate.call_count, 2)
        self.assertEqual(res.json()["message"]["content"], "Expense has 2 rows.")

    def test_trace_lists_every_stage_and_marks_the_investigation(self):
        AppSettings.set("ai_pipeline_debug", "true")
        res, _, _ = self.ask("what is my balance?", [REFUSAL, tool_call("app_data_models"), "Expense has 2 rows."])
        stages = {s["stage"]: s for s in res.json()["pipeline"]["stages"]}
        self.assertEqual(set(stages), set(STAGES) - {"respond"})
        self.assertEqual(stages["investigate"]["detail"]["why"], "refusal")
        self.assertEqual(stages["investigate"]["detail"]["tools"], ["app_data_models"])

    def test_customer_code_question_stays_on_the_normal_path(self):
        res, prov, _ = self.ask("which file defines ExpenseService?", ["It is part of the expenses module."])
        self.assertEqual(prov.generate.call_count, 1)
        self.assertEqual(res.json()["message"]["content"], "It is part of the expenses module.")


class SysadminCodeQuestionTest(InvestigatorChatBase):
    user_kwargs = {"sysadmin": True}

    def test_code_question_goes_straight_to_the_investigator_and_must_use_evidence(self):
        res, prov, log = self.ask("which file defines ExpenseService?", [
            "It is in utils.py.", tool_call("app_find_definition", symbol="ExpenseService"),
            "ExpenseService is defined at core/services/expenses/expense_service.py:12."])
        data = res.json()
        self.assertIn("expense_service.py:12", data["message"]["content"])
        self.assertEqual([c["tool"] for c in data["message"]["tool_calls"]], ["app_find_definition"])
        self.assertIn("investigation_code", data["sources"])
        self.assertIn("why", log)
        self.assertEqual(prov.generate.call_count, 3)          # the imagined answer was rejected, then evidence, then answer

    def test_code_switch_off_sends_the_question_down_the_normal_path(self):
        AppSettings.set("ai_code_access", "false")
        res, prov, _ = self.ask("which file defines ExpenseService?", ["Probably the expenses service."])
        self.assertEqual(prov.generate.call_count, 1)


class InvestigatorSettingsTest(TestCase):
    URL = "/api/settings/ai/"

    def setUp(self):
        self.admin = make_user("inv_settings_admin", sysadmin=True)
        self.client.force_login(self.admin)

    def post(self, **body):
        return self.client.post(self.URL, json.dumps(body), content_type="application/json")

    def test_defaults_round_trip_and_validation(self):
        got = self.client.get(self.URL).json()
        self.assertEqual((got["ai_investigator_mode"], got["ai_code_access"]), ("auto", True))
        self.assertEqual(self.post(ai_investigator_mode="always", ai_code_access=False).status_code, 200)
        got = self.client.get(self.URL).json()
        self.assertEqual((got["ai_investigator_mode"], got["ai_code_access"]), ("always", False))
        self.assertEqual(AppSettings.get("ai_code_access"), "false")
        self.assertEqual(self.post(ai_investigator_mode="sometimes").status_code, 400)
        self.assertEqual(self.client.get(self.URL).json()["ai_investigator_mode"], "always")   # rejected value not stored
        self.post(ai_validate_mode="flag")                                                     # omitted keys keep stored values
        self.assertEqual(self.client.get(self.URL).json()["ai_investigator_mode"], "always")
        self.assertEqual(self.post(ai_code_access="true", ai_investigator_mode="auto").status_code, 200)
        self.assertTrue(self.client.get(self.URL).json()["ai_code_access"])

    def test_a_users_own_settings_row_cannot_enable_code_access(self):
        AppSettings.set("ai_code_access", "false")
        AppSettings.set("ai_code_access", "true", user=self.admin)       # per-user row must not override the global switch
        from core.services.ai.investigation.code_tools import code_access_allowed

        self.assertFalse(code_access_allowed(self.admin))
