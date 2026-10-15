"""Agent mode through the real chat endpoint with a scripted model: skips instant answers, owns the tool loop, real Sources,
Stop, member vs sysadmin tools, the global off switch."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from core.models import AIConversation, AppSettings
from core.services.ai.agent import control, set_chat_mode
from core.tests.ai.investigation.support import make_user, seed_tenant, tool_call
from core.tests.billing.test_support import grant_ai_workspace_access

VIEW = "core.views.ai_chat.ai_chat_core_views"
GP = f"{VIEW}.generation_pipeline.build_context"
QUESTION = "show my expenses for September 2026"
CTX = ([{"role": "system", "content": "SYS\nBalance: 1 EGP."}, {"role": "user", "content": QUESTION}], ["balance"])


class AgentChatBase(TestCase):
    user_kwargs: dict = {}

    def setUp(self):
        self.user = make_user("agent_chat_user", **self.user_kwargs)
        seed_tenant(self.user, "Q", expenses=2, amount="50.00")
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_direct_answers", "true")      # instant answers ON: Agent mode must still skip them
        set_chat_mode(self.user, "agent")

    def ask(self, script, text=QUESTION, side_effect=None, **body):
        prov = MagicMock()
        prov.supports_tools, prov.model = True, "scripted"
        items = [{"content": s, "tool_calls": [], "error": None} if isinstance(s, str) else {"content": "", "tool_calls": [], "error": None, **s}
                 for s in script]
        calls = {"n": 0}

        def gen(messages, **kwargs):
            calls["n"] += 1
            if side_effect:
                side_effect(calls["n"])
            return items.pop(0) if items else {"content": "(script exhausted)", "tool_calls": [], "error": None}

        prov.generate.side_effect = gen
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=CTX), \
                self.assertLogs("core.ai.pipeline", level="WARNING") as logs:
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": text, **body}), content_type="application/json")
        return res.json(), prov, "\n".join(logs.output)


class AgentModeChatTest(AgentChatBase):
    def test_agent_skips_the_instant_answer_and_answers_from_tool_results(self):
        data, prov, log = self.ask([tool_call("app_computed_figures", question=QUESTION), "Your September 2026 expenses total 100.00 EGP."])
        self.assertEqual(data["message"]["content"], "Your September 2026 expenses total 100.00 EGP.")
        self.assertEqual(prov.generate.call_count, 2)                      # Ask mode would have used 0 model calls (instant answer)
        self.assertEqual([c["tool"] for c in data["message"]["tool_calls"]], ["app_computed_figures"])
        self.assertNotIn("direct_answer", json.dumps(data["message"]["tool_calls"]))
        self.assertIn("stage=investigate status=ok", log)
        self.assertIn("stage=route status=skipped", log)

    def test_sources_are_built_from_the_calls_that_really_ran(self):
        data, _, _ = self.ask([tool_call("app_data_models"), tool_call("app_data_query", model="Expense", aggregate={"count": "*"}),
                               tool_call("app_knowledge_search", query="expenses"), "You have 2 expenses."])
        self.assertTrue({"investigation_data", "investigation_docs", "agent:data:Expense", "agent:data:tables", "agent:docs:expenses"} <= set(data["sources"]))
        self.assertNotIn("investigation_code", data["sources"])

    def test_the_computed_rows_reach_the_model_only_as_an_unverified_hint(self):
        _, prov, _ = self.ask([tool_call("app_data_models"), "ok"])
        # the loop keeps appending to the same list, so pick the user turn rather than the last element
        last_user = next(m["content"] for m in prov.generate.call_args_list[0].args[0] if m["role"] == "user")
        self.assertIn(QUESTION, last_user)
        self.assertIn("[HINT, not verified by you", last_user)
        self.assertIn("100.00 EGP", last_user)

    def test_the_request_can_choose_ask_even_when_agent_is_saved(self):
        data, prov, _ = self.ask(["unused"], chat_mode="ask")
        self.assertEqual(prov.generate.call_count, 0)                      # instant answer path
        self.assertIn("100.00", data["message"]["content"])

    def test_a_user_in_ask_mode_is_unchanged(self):
        set_chat_mode(self.user, "ask")
        data, prov, _ = self.ask(["unused"])
        self.assertEqual(prov.generate.call_count, 0)
        self.assertNotIn("agent:", json.dumps(data["sources"]))

    def test_the_global_switch_off_sends_everyone_down_the_normal_path(self):
        AppSettings.set("ai_agent_enabled", "false")
        data, prov, _ = self.ask(["unused"])
        self.assertEqual(prov.generate.call_count, 0)
        self.assertIn("100.00", data["message"]["content"])

    def test_the_editable_instructions_are_what_the_model_is_told(self):
        AppSettings.set("ai_agent_instructions", "COMPANY RULE: cite the table name.")
        _, prov, _ = self.ask([tool_call("app_data_models"), "ok"])
        self.assertIn("COMPANY RULE: cite the table name.", prov.generate.call_args_list[0].args[0][0]["content"])

    def test_limits_from_settings_are_applied(self):
        AppSettings.set("ai_agent_max_steps", "2")
        _, prov, log = self.ask([tool_call("app_data_models", model="Expense"), tool_call("app_data_models", model="Bank"),
                                 tool_call("app_data_models", model="Company"), "Final from evidence."])
        self.assertIn("reason", log)
        self.assertLessEqual(prov.generate.call_count, 4)

    def test_stop_returns_a_localized_note_plus_what_was_found(self):
        conv = AIConversation.objects.create(user=self.user, title="stop me")
        data, prov, _ = self.ask(
            [tool_call("app_data_models"), tool_call("app_data_query", model="Expense", aggregate={"count": "*"}), "never reached"],
            side_effect=lambda n: control.request_stop(self.user, conv.id) if n == 2 else None, conversation_id=conv.id)
        content = data["message"]["content"]
        self.assertTrue(data["ok"])
        self.assertTrue(content.startswith("Stopped at your request."))
        self.assertIn("I investigated the app", content)
        self.assertEqual(prov.generate.call_count, 2)
        self.assertFalse(control.is_stopped(self.user, conv.id))           # the flag is cleared so the next question runs normally

    def test_stop_note_follows_the_language_of_the_question(self):
        conv = AIConversation.objects.create(user=self.user, title="arabic")
        data, _, _ = self.ask([tool_call("app_data_models"), tool_call("app_data_models", model="Expense"), "x"], text="كم أنفقت هذا الشهر؟",
                              side_effect=lambda n: control.request_stop(self.user, conv.id) if n == 2 else None, conversation_id=conv.id)
        self.assertTrue(data["message"]["content"].startswith("تم الإيقاف"))

    def test_a_model_that_never_uses_tools_gets_a_clear_note(self):
        prov = MagicMock()
        prov.supports_tools, prov.model = False, "plain"
        prov.generate.return_value = {"content": "Probably about 100.", "tool_calls": [], "error": None}
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=CTX), self.assertLogs("core.ai.pipeline", level="WARNING"):
            data = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": "how are my finances going overall?"}),
                                    content_type="application/json").json()
        self.assertIn("did not use any tools", data["message"]["content"])

    def test_a_provider_error_is_reported_like_everywhere_else(self):
        data, _, _ = self.ask([{"error": "model down"}, {"error": "model down"}])
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_key"], "ai_error_provider_unavailable")

    def test_the_export_request_still_attaches_the_file_link(self):
        data, _, _ = self.ask([tool_call("app_data_models"), "Here are your expenses."], text="list my expenses for September 2026 and export it to excel")
        self.assertIn("/api/financial-advisor/ai/messages/", data["message"]["content"])


class AgentModeMemberVsSysadminTest(AgentChatBase):
    def test_a_member_is_never_offered_code_tools_and_cannot_use_them(self):
        data, prov, _ = self.ask([tool_call("app_grep", pattern="SECRET_KEY"), tool_call("app_grep", pattern="SECRET_KEY"),
                                  tool_call("app_grep", pattern="SECRET_KEY"), "I cannot search the code."], text="which file defines ExpenseService?")
        offered = {t["function"]["name"] for t in prov.generate.call_args_list[0].kwargs["tools"]}
        self.assertNotIn("app_grep", offered)
        self.assertNotIn("investigation_code", data["sources"])
        self.assertNotIn("source code", prov.generate.call_args_list[0].args[0][0]["content"])


class AgentModeSysadminTest(AgentChatBase):
    user_kwargs = {"sysadmin": True}

    def test_a_sysadmin_gets_code_tools_and_real_file_line_sources(self):
        data, prov, _ = self.ask([tool_call("app_find_definition", symbol="code_access_allowed"),
                                  tool_call("app_read_file", path="core/services/ai/investigation/code_tools.py", start_line=25, end_line=40),
                                  "It is defined in code_tools.py (see lines 25-40)."], text="how does the AI decide who can read the source code?")
        offered = {t["function"]["name"] for t in prov.generate.call_args_list[0].kwargs["tools"]}
        self.assertTrue({"app_grep", "app_callers", "app_git_history", "app_trace_feature"} <= offered)
        self.assertIn("investigation_code", data["sources"])
        self.assertIn("agent:code:core/services/ai/investigation/code_tools.py:25-40", data["sources"])

    def test_the_code_switch_off_hides_code_tools_from_the_sysadmin_too(self):
        AppSettings.set("ai_code_access", "false")
        _, prov, _ = self.ask([tool_call("app_data_models"), "ok"])
        offered = {t["function"]["name"] for t in prov.generate.call_args_list[0].kwargs["tools"]}
        self.assertNotIn("app_read_file", offered)
        self.assertIn("app_routes", offered)
